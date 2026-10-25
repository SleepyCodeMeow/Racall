from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from collections import deque
from copy import deepcopy

from ...answer_language import question_language
from ...completion_stream import cancellable_completion
from ...provider_settings import embedding_settings
from ...providers import frozen_provider_keys, provider_identity, provider_key
from ...storage import ConflictError, Store, identifier, now, uid
from ..artifacts.repository import Materials
from ..context.service import ContextService
from ..studio.generator import NoEvidence, UnverifiedMaterial, generate_material
from .repository import TERMINAL, JobRepository
from .schemas import GenerationRequest


class GenerationCancelled(Exception):
    cancelled = True


class ProviderChanged(Exception):
    pass


class GenerationService:
    """One daemon worker, portable state, no implicit recovery/retry of inference.

    Closing never joins an in-flight provider request. Its eventual response is
    fenced by checkpoints and cannot publish after interruption/cancellation.
    """

    def __init__(self, store: Store, knowledge):
        self.store = store
        self.knowledge = knowledge
        self.context = ContextService(store)
        self.jobs = JobRepository(store)
        self.materials = Materials(store)
        self._queue = deque()
        self._accepted: dict[str, dict] = {}
        self._protected: set[str] = set()
        self._secret = secrets.token_bytes(32)
        self._condition = threading.Condition(store.lock)
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def _configuration(self, settings: dict) -> dict:
        return {"provider": settings["provider"], "base_url": settings["base_url"],
                "model": settings["model"], "embeddings": deepcopy(settings["embeddings"])}

    def _credentials(self, settings: dict) -> dict:
        configs = [settings]
        embeddings = embedding_settings(settings)
        if embeddings.get("embedding_model"):
            configs.append(embeddings)
        return {provider_identity(config): provider_key(config) for config in configs}

    def _fingerprint(self, settings: dict, credentials: dict) -> bytes:
        data = {"configuration": self._configuration(settings),
                "credentials": [[*identity, key] for identity, key in sorted(credentials.items())]}
        return hmac.digest(self._secret, json.dumps(data, sort_keys=True).encode(), hashlib.sha256)

    def _protect(self, notebook: str, job: str):
        if job not in self._protected:
            self.store.active_operations[notebook] = self.store.active_operations.get(notebook, 0) + 1
            self._protected.add(job)

    def _release(self, notebook: str, job: str):
        if job in self._protected:
            count = self.store.active_operations.get(notebook, 0) - 1
            if count > 0:
                self.store.active_operations[notebook] = count
            else:
                self.store.active_operations.pop(notebook, None)
            self._protected.remove(job)
        self._accepted.pop(job, None)

    def recover(self):
        with self.store.lock:
            for notebook in self.store.notebooks():
                for job in self.jobs.list(notebook["id"]):
                    if job["status"] not in {"queued", "running"} or job["id"] in self._accepted:
                        continue
                    material = self.materials.for_job(notebook["id"], job["id"])
                    if material and material.get("job_id") == job["id"] and material["answer"].get("validated"):
                        job.update(status="completed", stage="completed", error=None,
                                   result={"material_id": material["id"],
                                           **({"research_id": material["research_id"]}
                                              if material.get("research_id") else {})})
                    else:
                        job.update(status="interrupted", stage="interrupted", error="interrupted")
                    job.update(updated_at=now(), finished_at=now())
                    self.jobs.save(notebook["id"], job)

    def start(self):
        with self._condition:
            if self._thread is not None or self._stopping.is_set():
                return
            self.recover()
            self._thread = threading.Thread(target=self._run, name="racall-generation", daemon=True)
            self._thread.start()

    def close(self):
        with self._condition:
            self._stopping.set()
            for notebook in self.store.notebooks():
                for job in self.jobs.list(notebook["id"]):
                    if job["status"] in {"queued", "running"}:
                        job.update(status="interrupted", stage="interrupted", error="interrupted",
                                   updated_at=now(), finished_at=now())
                        self.jobs.save(notebook["id"], job)
                    self._release(notebook["id"], job["id"])
            self._queue.clear()
            self._condition.notify_all()

    def submit(self, notebook: str, request: GenerationRequest | dict, *, retry_of=None) -> dict:
        notebook = identifier(notebook)
        request = GenerationRequest.model_validate(request)
        data = request.model_dump()
        with self._condition:
            if self._stopping.is_set():
                raise ConflictError("Generation service is stopping.")
            for existing in self.jobs.list(notebook):
                if existing["request_id"] == request.request_id:
                    if existing["_request"] != data or existing.get("retry_of") != retry_of:
                        raise ConflictError("This request ID was already used for a different generation.")
                    return self.jobs.public(existing)
            context = self.context.snapshot(notebook, request.context)
            settings = deepcopy(self.store.settings())
            if not settings["model"].strip():
                raise ValueError("Укажите имя модели в настройках AI")
            keys = self._credentials(settings)
            job_id = uid()
            defaults = {
                "en": {"research": "Research", "summary": "Summary", "study_guide": "Study guide",
                       "review_questions": "Review questions"},
                "ru": {"research": "Исследование", "summary": "Краткое содержание",
                       "study_guide": "Учебный конспект", "review_questions": "Контрольные вопросы"},
            }
            title = request.title or (request.question[:160] if request.kind == "research" else "")
            title = title or defaults[request.language][request.kind]
            job = {
                "id": job_id, "request_id": request.request_id, "kind": request.kind,
                "status": "queued", "stage": "queued", "steps": [], "question": request.question,
                "title": title, "language": request.language, "context": context,
                "provider": {key: settings[key] for key in ("provider", "base_url", "model")},
                "created_at": now(), "updated_at": now(), "_request": data,
                **({"retry_of": retry_of} if retry_of else {}),
            }
            self.jobs.save(notebook, job)
            self._accepted[job_id] = {"settings": settings, "keys": keys,
                                      "fingerprint": self._fingerprint(settings, keys)}
            self._protect(notebook, job_id)
            self._queue.append((notebook, job_id))
            self._condition.notify()
            return self.jobs.public(job)

    def list(self, notebook: str) -> list[dict]:
        return [self.jobs.public(item) for item in self.jobs.list(notebook)]

    def get(self, notebook: str, job: str) -> dict:
        return self.jobs.public(self.jobs.get(notebook, job))

    def cancel(self, notebook: str, job_id: str) -> dict:
        with self._condition:
            job = self.jobs.get(notebook, job_id)
            if job["status"] in TERMINAL:
                return self.jobs.public(job)
            queued = job["status"] == "queued"
            job.update(status="cancelled", stage="cancelled", updated_at=now(), finished_at=now())
            self.jobs.save(notebook, job)
            if queued:
                self._release(notebook, job_id)
            self._condition.notify_all()
            return self.jobs.public(job)

    def retry(self, notebook: str, job_id: str, request_id: str) -> dict:
        with self.store.lock:
            previous = self.jobs.get(notebook, job_id)
            if previous["status"] not in {"failed", "cancelled", "interrupted"}:
                raise ConflictError("Only failed, cancelled or interrupted generations can be retried.")
            request = {**previous["_request"], "request_id": request_id}
            return self.submit(notebook, request, retry_of=previous["id"])

    def _checkpoint(self, notebook: str, job_id: str, snapshot: dict):
        with self.store.lock:
            self._cancel_check(notebook, job_id)
            self.context.validate_snapshot(notebook, snapshot)

    def _cancel_check(self, notebook: str, job_id: str):
        with self.store.lock:
            if self._stopping.is_set() or self.jobs.get(notebook, job_id)["status"] != "running":
                raise GenerationCancelled()

    def _progress(self, notebook: str, job_id: str, stage: str, detail=None):
        with self.store.lock:
            job = self.jobs.get(notebook, job_id)
            self._checkpoint(notebook, job_id, job["context"])
            detail = {key: value for key, value in (detail or {}).items()
                      if key in {"count", "accepted", "attempt", "total"} and type(value) in (int, bool)}
            job["steps"].append({"stage": stage, "at": now(), **({"detail": detail} if detail else {})})
            job.update(stage=stage, updated_at=now())
            self.jobs.save(notebook, job)

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._stopping.is_set() or bool(self._queue))
                if self._stopping.is_set():
                    return
                notebook, job_id = self._queue.popleft()
                try:
                    job = self.jobs.get(notebook, job_id)
                except FileNotFoundError:
                    # A queued cancellation releases the notebook deletion guard.
                    self._release(notebook, job_id)
                    continue
                if job["status"] != "queued":
                    self._release(notebook, job_id)
                    continue
                job.update(status="running", stage="context", updated_at=now())
                self.jobs.save(notebook, job)
            try:
                self._execute(notebook, job_id)
            except GenerationCancelled:
                pass
            except ConflictError:
                self._fail(notebook, job_id, "context_changed")
            except ProviderChanged:
                self._fail(notebook, job_id, "provider_changed")
            except NoEvidence:
                self._fail(notebook, job_id, "no_evidence")
            except UnverifiedMaterial:
                self._fail(notebook, job_id, "unverified_output")
            except Exception:
                # Keep raw provider failures, prompts and credentials out of durable metadata.
                self._fail(notebook, job_id, "generation_failed")
            finally:
                with self.store.lock:
                    self._release(notebook, job_id)

    def _fail(self, notebook: str, job_id: str, code: str):
        with self.store.lock:
            job = self.jobs.get(notebook, job_id)
            if job["status"] == "running":
                job.update(status="failed", stage="failed", error=code, updated_at=now(), finished_at=now())
                self.jobs.save(notebook, job)

    def _execute(self, notebook: str, job_id: str):
        job = self.jobs.get(notebook, job_id)
        accepted = self._accepted[job_id]
        current = self.store.settings()
        current_keys = self._credentials(current)
        if not hmac.compare_digest(self._fingerprint(current, current_keys), accepted["fingerprint"]):
            raise ProviderChanged()
        def checkpoint():
            self._checkpoint(notebook, job_id, job["context"])

        def progress(stage, detail=None):
            self._progress(notebook, job_id, stage, detail)
        checkpoint()
        settings = accepted["settings"]
        with frozen_provider_keys(accepted["keys"]), cancellable_completion(
                lambda: self._cancel_check(notebook, job_id)):
            if job["kind"] == "research":
                question = job["question"] or job["title"]
                if question_language(question) != job["language"]:
                    question += "\n" + ("Ответь на русском." if job["language"] == "ru" else "Answer in English.")
                result = self.knowledge.research(notebook, question, context=job["context"], settings=settings,
                                                 progress=progress, cancel=checkpoint)
                if not result.get("answer", {}).get("validated"):
                    raise UnverifiedMaterial()
                generated = {"answer": result["answer"]}
            else:
                progress("retrieval")
                gathered = self.context.gather_snapshot(notebook, job["context"])
                generated = generate_material(job["kind"], job["question"], job["title"], job["language"],
                                              gathered["evidence"], settings, checkpoint, progress)
                generated["context_info"] = gathered["context_info"]
            progress("saving")
            with self.store.lock:
                checkpoint()
                material = {
                    "id": job_id, "job_id": job_id, "kind": job["kind"], "title": job["title"],
                    "created_at": now(), "context": job["context"], "provider": job["provider"], **generated,
                }
                if job["kind"] == "research":
                    note = self.knowledge.save_research(notebook, result["id"])
                    material.update(body=note["body"], research_id=result["id"])
                self.materials.create(notebook, material)
                job = self.jobs.get(notebook, job_id)
                job.update(status="completed", stage="completed", updated_at=now(), finished_at=now(),
                           result={"material_id": material["id"],
                                   **({"research_id": material["research_id"]}
                                      if material.get("research_id") else {})})
                self.jobs.save(notebook, job)
