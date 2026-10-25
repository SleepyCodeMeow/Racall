"""An isolated application API session and reviewable provenance assertions."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from pathlib import Path

from .guard import EvaluationStop, timestamp, write_json


class EvaluationSession:
    def __init__(self, root, output, guard, cases):
        self.root, self.output, self.guard, self.cases = Path(root), Path(output), guard, cases
        self.vault = self.output / "isolated-knowledge"
        self.token = secrets.token_hex(24)
        self.results = []
        self.sources = {}
        self.note_revisions = {}
        self.client = None
        self.app = None
        self.notebook = None
        self.vault.mkdir()
        write_json(
            self.vault / "settings.json",
            {
                "provider": "ollama",
                "profiles": {"ollama": {"base_url": guard.endpoint, "model": guard.model}},
                "embeddings": {"provider": "ollama", "base_url": guard.endpoint, "model": ""},
            },
        )

    def start(self):
        from fastapi.testclient import TestClient
        from on_knowledge.app import create_app

        self.app = create_app(self.vault, self.token)
        self.client = TestClient(self.app, headers={"Authorization": "Bearer " + self.token})
        self.client.__enter__()

    def close(self):
        if self.client is not None:
            self.client.__exit__(None, None, None)
            self.client = None

    def restart(self):
        self.close()
        self.guard.wait_idle()
        self.start()

    def api(self, path, method="GET", body=None, *, raw=False, **kwargs):
        self.guard.check()
        response = self.client.request(method, "/api" + path, json=body, **kwargs)
        self.guard.check()
        if not response.is_success:
            raise EvaluationStop(
                f"Application API {method} {path} failed: {response.status_code} {response.text}"
            )
        return response if raw else response.json()

    @property
    def base(self):
        return "/notebooks/" + self.notebook

    def wait(self, condition, timeout=360):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.guard.check()
            value = condition()
            if value:
                return value
            time.sleep(0.1)
        raise EvaluationStop("Application state did not reach the expected checkpoint.")

    def prepare(self):
        self.notebook = self.api("/notebooks", "POST", {"title": "Synthetic 0.3 live acceptance"})["id"]
        for file in sorted((self.root / "evals/release02/sources").glob("*.md")):
            response = self.client.post(
                "/api" + self.base + "/sources",
                files={"file": (file.name, file.read_bytes(), "text/markdown")},
            )
            assert response.is_success, response.text
            item = response.json()
            self.wait(lambda: self.ready_source(item["id"]))
            self.sources[file.name] = self.api(self.base + "/sources/" + item["id"])["source"]
        self.save()

    def ready_source(self, source):
        item = self.api(self.base + "/sources/" + source)["source"]
        if item["status"] == "error" or item.get("refresh_status") == "error":
            raise EvaluationStop(
                "Synthetic source import failed: " + str(item.get("error") or item.get("refresh_error"))
            )
        return (
            item
            if item["status"] == "ready" and item.get("refresh_status") not in {"queued", "processing"}
            else None
        )

    def save(self, status="running", error=None):
        write_json(
            self.output / "results.json",
            {
                "status": status,
                "error": error,
                "model": self.guard.model,
                "digests": self.guard.digests,
                "notebook": self.notebook,
                "sources": self.sources,
                "results": self.results,
                "quality_verdict": "manual_pending",
                "limits": {
                    "live_provider": "local Ollama only",
                    "embeddings": "disabled in this isolated vault",
                    "desktop_owner_acceptance": "not performed by this API runner",
                    "publication": "hold",
                    "generation_parameters": "production defaults; alias options are external",
                },
            },
        )

    def run_case(self, case_id, run):
        self.guard.wait_idle()
        self.guard.case = case_id
        record = {
            "id": case_id,
            "started_at": timestamp(),
            "first_call": len(self.guard.calls) + 1,
            "quality_verdict": "manual_pending",
            "contract_verdict": "running",
        }
        self.results.append(record)
        self.save()
        print("Evaluating " + case_id, flush=True)
        try:
            record["result"] = run()
            self.guard.check()
            record["contract_verdict"] = "passed"
        except BaseException as error:
            record.update(contract_verdict="failed", error_type=type(error).__name__, error=str(error))
            raise
        finally:
            record.update(finished_at=timestamp(), last_call=len(self.guard.calls))
            self.save()

    def note(self, title, body, previous=None):
        payload = {"title": title, "body": body}
        if previous:
            payload.update(id=previous["id"], revision=previous["revision"])
        note = self.api(self.base + "/notes", "POST", payload)
        self.note_revisions[(note["id"], note["revision"])] = note["body"]
        return note

    def chat(self, title, selection):
        return self.api(self.base + "/chats", "POST", {"title": title, "context": selection})

    def turn(self, thread, question):
        from uuid import uuid4

        return self.api(
            self.base + f"/chats/{thread['id']}/turns",
            "POST",
            {
                "request_id": str(uuid4()),
                "question": question,
            },
        )

    def submit(self, kind, question, selection, language="en"):
        from uuid import uuid4

        return self.api(
            self.base + "/jobs",
            "POST",
            {
                "request_id": str(uuid4()),
                "kind": kind,
                "question": question,
                "language": language,
                "context": selection,
            },
        )

    def terminal(self, job):
        return self.wait(
            lambda: (
                item
                if (item := self.api(self.base + "/jobs/" + job["id"]))["status"] not in {"queued", "running"}
                else None
            ),
            timeout=1200,
        )

    def material(self, job):
        assert job["status"] == "completed", job
        item = self.api(self.base + "/materials/" + job["result"]["material_id"])
        self.provenance(item["answer"], job["context"])
        return item

    def provenance(self, answer, snapshot=None):
        citations = answer.get("citations", [])
        identifiers = {item["id"] for item in citations}
        assert len(identifiers) == len(citations), "Duplicate canonical citations"
        assert all(not re.fullmatch(r"E\d+", value) for value in identifiers), (
            "Request-local citation labels escaped"
        )
        for claim in answer.get("claims", []):
            assert claim.get("evidence_ids") and set(claim["evidence_ids"]) <= identifiers, (
                "Unmapped claim citation"
            )
        if snapshot is not None:
            allowed_sources = {(row["id"], row["version"]) for row in snapshot["sources"]}
            allowed_notes = {(row["id"], row["revision"]) for row in snapshot["notes"]}
        for citation in citations:
            location = citation["location"]
            if citation.get("kind") == "note":
                identity = citation["note_id"], citation["version"]
                if snapshot is not None:
                    assert identity in allowed_notes, "Citation escaped selected note revisions"
                text = self.note_revisions[identity]
            else:
                if snapshot is not None:
                    assert (citation["source_id"], citation["version"]) in allowed_sources, (
                        "Citation escaped selected source versions"
                    )
                prefix = self.base + f"/sources/{citation['source_id']}/versions/{citation['version']}"
                document = self.api(prefix)["document"]
                element = document["elements"][location["element"]]
                text = element["text"]
                original = self.api(prefix + "/original", raw=True).content
                assert hashlib.sha256(original).hexdigest() == citation["version"], (
                    "Source original/version hash mismatch"
                )
                if location.get("page"):
                    assert location["page"] == element.get("page"), "Wrong page location"
            assert 0 <= location["offset_start"] <= location["offset_end"] <= len(text), (
                "Invalid passage offsets"
            )
            assert text[location["offset_start"] : location["offset_end"]] == citation["quote"], (
                "Quotation/offset mismatch"
            )
        return {
            "citations_checked": len(citations),
            "claims_checked": len(answer.get("claims", [])),
            "claim_entailment_verdict": "manual_pending",
        }

    def review(self, answer, case, *, snapshot=None):
        provenance = self.provenance(answer, snapshot)
        prose = " ".join(item["text"] for item in answer.get("claims", []))
        flags = []
        if not case.get("unknown") and not answer.get("validated"):
            flags.append("Known-fact question did not return a validated answer")
        for pattern in case.get("patterns", []):
            if not re.search(pattern, prose, re.I):
                flags.append("Expected fact pattern missing: " + pattern)
        for forbidden in case.get("forbidden", []):
            if forbidden.casefold() in prose.casefold():
                flags.append("Forbidden instruction output appeared: " + forbidden)
        if len({item["source_id"] for item in answer.get("citations", [])}) < case.get("min_sources", 0):
            flags.append("Not all required sources were cited")
        return {
            "answer": answer,
            "provenance": provenance,
            "review_flags": flags,
            "review_requirements": case,
            "quality_verdict": "manual_pending",
        }
