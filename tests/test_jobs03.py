import json
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from on_knowledge.features.artifacts.repository import Materials
from on_knowledge.features.artifacts.router import create_router as material_router
from on_knowledge.features.jobs.router import create_router as jobs_router
from on_knowledge.features.jobs.service import GenerationService
from on_knowledge.features.notebooks.repository import Notebooks
from on_knowledge.knowledge import Knowledge
from on_knowledge.providers import OpenAICompatible, provider_key
from on_knowledge.storage import ConflictError, Store, now, uid, write_json


class Provider:
    def __init__(self, entered=None, release=None, error=None):
        self.entered, self.release, self.error = entered, release, error
        self.calls = []

    def complete(self, system, data):
        self.calls.append((system, data))
        if "evidence critic" in system:
            return {"supported_claim_ids": [item["claim_id"] for item in data["claims"]]}
        if self.entered:
            self.entered.set()
        if self.release:
            assert self.release.wait(5), "Test did not release blocked fake provider"
        if self.error:
            raise ValueError(self.error)
        return {"items": [{"text": "The project codename is Marigold.", "evidence_ids": ["E1"]}]}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    store = Store(tmp_path)
    settings = store.settings()
    settings["profiles"][settings["provider"]]["model"] = "fixture"
    write_json(store.root / "settings.json", settings)
    notebook = store.create_notebook("Research")["id"]
    source = {"id": uid(), "title": "Project", "status": "ready", "version": "v1", "created_at": now()}
    store.save_source(notebook, source)
    chunk = {
        "id": "source-v1-chunk",
        "text": "The project codename is Marigold.",
        "location": {"page": 2, "element": 0, "offset_start": 0, "offset_end": 33},
    }
    store.replace_chunks(notebook, source["id"], source["version"], [chunk])
    monkeypatch.setattr(
        "on_knowledge.features.jobs.service.provider_key", lambda settings: "test-private-key"
    )
    service = GenerationService(store, object())
    yield store, notebook, source, service
    service.close()


def request(**overrides):
    return {"request_id": uid(), "kind": "summary", "language": "en", **overrides}


def terminal(service, notebook, job_id, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = service.get(notebook, job_id)
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.01)
    pytest.fail("Fake-provider job did not finish")


@pytest.mark.parametrize("kind", ["research", "summary", "study_guide", "review_questions"])
@pytest.mark.parametrize("model", ["", " \t "])
def test_missing_model_rejected_before_credentials_or_durable_job(setup, monkeypatch, kind, model):
    store, notebook, source, service = setup
    settings = store.settings()
    settings["profiles"][settings["provider"]]["model"] = model
    write_json(store.root / "settings.json", settings)
    lookups = []

    def forbidden_credentials(settings):
        lookups.append(settings)
        pytest.fail("An unconfigured generation must not read provider credentials")

    monkeypatch.setattr("on_knowledge.features.jobs.service.provider_key", forbidden_credentials)
    with pytest.raises(ValueError, match="^Укажите имя модели в настройках AI$"):
        service.submit(notebook, request(kind=kind, question="Summarize the selected materials"))
    assert not lookups
    assert service.list(notebook) == []
    assert service.materials.list(notebook) == []
    assert not store.active_operations


def test_existing_submission_remains_idempotent_after_model_is_cleared(setup, monkeypatch):
    store, notebook, source, service = setup
    body = request()
    first = service.submit(notebook, body)
    settings = store.settings()
    settings["profiles"][settings["provider"]]["model"] = ""
    write_json(store.root / "settings.json", settings)
    monkeypatch.setattr(
        "on_knowledge.features.jobs.service.provider_key",
        lambda settings: pytest.fail("Deduplicated request read changed credentials"),
    )
    assert service.submit(notebook, body)["id"] == first["id"]
    assert len(service.list(notebook)) == 1
    assert store.active_operations[notebook] == 1


def test_progress_dedup_portable_material_and_copy(setup, monkeypatch):
    store, notebook, source, service = setup
    provider = Provider()
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    body = request()
    queued = service.submit(notebook, body)
    assert service.submit(notebook, body)["id"] == queued["id"]
    with pytest.raises(ConflictError):
        service.submit(notebook, {**body, "question": "Another question"})
    service.start()
    job = terminal(service, notebook, queued["id"])
    assert job["status"] == "completed", job
    assert [item["stage"] for item in job["steps"]] == ["retrieval", "writer", "critic", "saving"]
    material = service.materials.get(notebook, job["result"]["material_id"])
    assert material["answer"]["citations"][0]["source_id"] == source["id"]
    assert material["answer"]["citations"][0]["quote"] == "The project codename is Marigold."
    copy = service.materials.copy(notebook, material["id"])
    store.save_note(notebook, copy["title"], "My edited note", copy["id"], revision=copy["revision"])
    assert service.materials.get(notebook, material["id"])["body"] == copy["body"]
    assert Materials(Store(store.root)).get(notebook, material["id"])["job_id"] == job["id"]
    persisted = (store.notebook_path(notebook) / "jobs" / (job["id"] + ".json")).read_text("utf-8")
    assert "test-private-key" not in persisted and "fingerprint" not in persisted
    assert all(not key.startswith("_") for key in job)


def test_queued_cancel_never_calls_provider_and_unblocks_delete(setup, monkeypatch):
    store, notebook, source, service = setup
    provider = Provider()
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    job = service.submit(notebook, request())
    with pytest.raises(ConflictError):
        Notebooks(store).delete(notebook)
    assert service.cancel(notebook, job["id"])["status"] == "cancelled"
    Notebooks(store).delete(notebook)
    service.start()  # The stale cancelled queue entry cannot kill the worker or revive a deleted notebook.
    assert provider.calls == [] and notebook not in store.active_operations


def test_running_cancel_fences_late_result(setup, monkeypatch):
    store, notebook, source, service = setup
    entered, release = threading.Event(), threading.Event()
    provider = Provider(entered, release)
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    service.start()
    job = service.submit(notebook, request())
    try:
        assert entered.wait(3)
        cancelled = service.cancel(notebook, job["id"])
        assert cancelled["status"] == "cancelled"
        release.set()
        deadline = time.monotonic() + 3
        while notebook in store.active_operations and time.monotonic() < deadline:
            time.sleep(0.01)
        assert service.get(notebook, job["id"])["status"] == "cancelled"
        assert not service.materials.list(notebook) and len(provider.calls) == 1
        assert notebook not in store.active_operations
    finally:
        release.set()


def test_close_does_not_wait_for_provider_and_restart_does_not_replay(setup, monkeypatch):
    store, notebook, source, service = setup
    entered, release = threading.Event(), threading.Event()
    provider = Provider(entered, release)
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    service.start()
    running = service.submit(notebook, request())
    try:
        assert entered.wait(3)
        queued = service.submit(notebook, request())
        start = time.monotonic()
        service.close()
        assert time.monotonic() - start < 0.5
        for job in (running, queued):
            assert service.get(notebook, job["id"])["status"] == "interrupted"
        restarted = GenerationService(store, object())
        restarted.start()
        try:
            assert all(job["status"] == "interrupted" for job in restarted.list(notebook))
            assert len(provider.calls) == 1
            release.set()
            service._thread.join(timeout=2)
            assert not service.materials.list(notebook)
        finally:
            restarted.close()
    finally:
        release.set()


def test_recover_old_queue_without_inference_and_retry_current_context(setup, monkeypatch):
    store, notebook, source, service = setup
    provider = Provider()
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    old = service.submit(notebook, request())
    # A fresh process has the files but never has the accepted credential snapshot.
    recovered = GenerationService(store, object())
    recovered.recover()
    assert recovered.get(notebook, old["id"])["status"] == "interrupted"
    assert not provider.calls
    note = store.save_note(notebook, "New context", "A later note")
    source["version"] = "v2"
    store.save_source(notebook, source)
    retried = recovered.retry(notebook, old["id"], uid())
    assert retried["id"] != old["id"] and retried["retry_of"] == old["id"]
    assert retried["context"]["sources"][0]["version"] == "v2"
    assert note["id"] not in retried["context"]["selection"]["note_ids"]
    recovered.close()


@pytest.mark.parametrize("change", ["source", "note", "provider", "credentials"])
def test_queue_rejects_changed_context_or_connection_before_inference(setup, monkeypatch, change):
    store, notebook, source, service = setup
    provider = Provider()
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    note = store.save_note(notebook, "Project note", "The project codename is Marigold.")
    job = service.submit(notebook, request(context={"source_ids": [source["id"]], "note_ids": [note["id"]]}))
    if change == "source":
        source["version"] = "v2"
        store.save_source(notebook, source)
    elif change == "note":
        store.save_note(notebook, note["title"], "Changed", note["id"], revision=note["revision"])
    elif change == "provider":
        settings = store.settings()
        settings["profiles"]["openai"]["base_url"] = "https://other.example/v1"
        write_json(store.root / "settings.json", settings)
    else:
        monkeypatch.setattr("on_knowledge.features.jobs.service.provider_key", lambda settings: "rotated-key")
    service.start()
    result = terminal(service, notebook, job["id"])
    assert result["status"] == "failed"
    assert result["error"] == ("context_changed" if change in {"source", "note"} else "provider_changed")
    assert not provider.calls and not service.materials.list(notebook)


def test_context_change_while_model_runs_prevents_publication(setup, monkeypatch):
    store, notebook, source, service = setup
    entered, release = threading.Event(), threading.Event()
    provider = Provider(entered, release)
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    service.start()
    job = service.submit(notebook, request())
    try:
        assert entered.wait(3)
        source["version"] = "v2"
        store.save_source(notebook, source)
        release.set()
        result = terminal(service, notebook, job["id"])
        assert result["error"] == "context_changed" and not service.materials.list(notebook)
        assert len(provider.calls) == 1
    finally:
        release.set()


def test_provider_error_is_stable_and_does_not_persist_secrets(setup, monkeypatch):
    store, notebook, source, service = setup
    provider = Provider(error="Authentication failed: test-private-key RAW-RESPONSE")
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    service.start()
    job = terminal(service, notebook, service.submit(notebook, request())["id"])
    assert job["error"] == "generation_failed"
    persisted = json.dumps(service.jobs.get(notebook, job["id"]))
    assert "test-private-key" not in persisted and "RAW-RESPONSE" not in persisted
    assert len(provider.calls) == 1 and not service.materials.list(notebook)


def test_explicit_empty_selection_does_not_fallback_to_all_sources(setup, monkeypatch):
    store, notebook, source, service = setup
    provider = Provider()
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    service.start()
    job = terminal(
        service, notebook, service.submit(notebook, request(context={"source_ids": [], "note_ids": []}))["id"]
    )
    assert job["error"] == "no_evidence" and not provider.calls


def test_legacy_material_routes_are_nondestructive_and_copy_editable(setup):
    store, notebook, source, service = setup
    original = store.save_note(notebook, "Old report", "# Original\n\nOld content", kind="artifacts")
    path = store.notebook_path(notebook) / "artifacts" / (original["id"] + ".md")
    before = path.read_bytes()
    app = FastAPI()
    app.include_router(material_router(service.materials))
    app.include_router(jobs_router(service))
    with TestClient(app) as client:
        listed = client.get(f"/api/notebooks/{notebook}/materials").json()
        assert listed[0]["legacy"] is True
        material_id = listed[0]["id"]
        assert (
            client.get(f"/api/notebooks/{notebook}/materials/{material_id}").json()["body"]
            == original["body"]
        )
        exported = client.get(f"/api/notebooks/{notebook}/materials/{material_id}/export")
        assert exported.text == original["body"] and "text/markdown" in exported.headers["content-type"]
        copied = client.post(f"/api/notebooks/{notebook}/materials/{material_id}/copy")
        assert copied.status_code == 201 and copied.json()["body"] == original["body"]
        queued = client.post(f"/api/notebooks/{notebook}/jobs", json=request())
        assert queued.status_code == 202
        assert (
            client.post(f"/api/notebooks/{notebook}/jobs/{queued.json()['id']}/cancel").json()["status"]
            == "cancelled"
        )
    assert path.read_bytes() == before
    with pytest.raises(ValueError):
        service.materials.get(notebook, "legacy:../escape")


def test_research_job_reuses_engine_and_publishes_one_inspectable_material(setup, monkeypatch):
    store, notebook, source, service = setup
    knowledge = Knowledge(store)
    service.knowledge = knowledge
    calls = []

    def complete(self, system, data):
        calls.append((system, data))
        if "Plan research" in system:
            return {"queries": ["Marigold"]}
        if "evidence critic" in system:
            return {"supported_claim_ids": [item["claim_id"] for item in data["claims"]]}
        return {"claims": [{"text": "The project codename is Marigold.", "evidence_ids": ["E1"]}]}

    monkeypatch.setattr(OpenAICompatible, "complete", complete)
    try:
        service.start()
        job = terminal(
            service, notebook, service.submit(notebook, request(kind="research", question="Marigold"))["id"]
        )
        assert job["status"] == "completed", job
        assert len(calls) == 3
        material = service.materials.get(notebook, job["result"]["material_id"])
        assert material["research_id"] == job["result"]["research_id"]
        assert material["answer"]["citations"][0]["source_id"] == source["id"]
        assert "> The project codename is Marigold." in material["body"]
        assert len(service.materials.list(notebook)) == 1  # Its underlying 0.2 artifact is not listed twice.
        assert len(store.list_notes(notebook, "artifacts")) == 1
        session = json.loads(
            (store.notebook_path(notebook) / "research" / (material["research_id"] + ".json")).read_text(
                "utf-8"
            )
        )
        assert session["status"] == "completed" and session["context_snapshot"] == job["context"]
    finally:
        service.close()
        knowledge.executor.shutdown(wait=True)


def test_single_worker_keeps_next_job_queued_until_first_finishes(setup, monkeypatch):
    store, notebook, source, service = setup
    entered, release = threading.Event(), threading.Event()
    provider = Provider(entered, release)
    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: provider
    )
    service.start()
    first = service.submit(notebook, request())
    try:
        assert entered.wait(3)
        second = service.submit(notebook, request())
        assert service.get(notebook, second["id"])["status"] == "queued"
        assert len(provider.calls) == 1 and store.active_operations[notebook] == 2
        release.set()
        assert terminal(service, notebook, first["id"])["status"] == "completed"
        assert terminal(service, notebook, second["id"])["status"] == "completed"
        assert len(provider.calls) == 4 and len(service.materials.list(notebook)) == 2
    finally:
        release.set()


def test_running_job_pins_provider_settings_and_credentials_for_critic(setup, monkeypatch):
    store, notebook, source, service = setup
    connections = []

    class PinnedProvider(Provider):
        def __init__(self, settings):
            super().__init__()
            self.settings = settings

        def complete(self, system, data):
            connections.append((self.settings["base_url"], provider_key(self.settings)))
            if not self.calls:
                settings = store.settings()
                settings["profiles"]["openai"]["base_url"] = "https://new.example/v1"
                write_json(store.root / "settings.json", settings)
                monkeypatch.setattr(
                    "on_knowledge.features.jobs.service.provider_key", lambda settings: "new-key"
                )
            return super().complete(system, data)

    monkeypatch.setattr("on_knowledge.features.studio.generator.completion_provider", PinnedProvider)
    service.start()
    job = terminal(service, notebook, service.submit(notebook, request())["id"])
    assert job["status"] == "completed", job
    assert connections == [("https://api.openai.com/v1", "test-private-key")] * 2
    assert (
        service.materials.get(notebook, job["result"]["material_id"])["provider"]["base_url"]
        == connections[0][0]
    )


def test_recovery_recognizes_committed_material_without_replaying_model(setup):
    store, notebook, source, service = setup
    job = service.submit(notebook, request())
    service.materials.create(
        notebook,
        {
            "id": job["id"],
            "job_id": job["id"],
            "kind": "summary",
            "title": "Committed",
            "created_at": now(),
            "body": "# Committed",
            "answer": {"validated": True},
        },
    )
    restarted = GenerationService(store, object())
    restarted.recover()
    recovered = restarted.get(notebook, job["id"])
    assert recovered["status"] == "completed" and recovered["result"] == {"material_id": job["id"]}
    restarted.close()
