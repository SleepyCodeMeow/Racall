import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from on_knowledge.app import create_app
from on_knowledge.features.chats.service import Chats
from on_knowledge.storage import ConflictError, Store

TOKEN = "test-session-token-long-enough"
HEADERS = {"Authorization": "Bearer " + TOKEN}


def client_for(path):
    return TestClient(create_app(path, TOKEN), headers=HEADERS)


def notebook(client):
    return client.post("/api/notebooks", json={"title": "Notebook"}).json()["id"]


def test_transcript_survives_restart_and_index_loss_with_exact_citations(tmp_path, monkeypatch):
    citation = {
        "id": "chunk1",
        "source_id": str(uuid4()),
        "version": "source-version",
        "quote": "A saved passage.",
        "title": "Original source",
        "location": {"element": 0, "offset_start": 0, "offset_end": 16},
        "number": 1,
    }
    answer = {
        "claims": [{"text": "A saved passage.", "evidence_ids": ["chunk1"]}],
        "citations": [citation],
        "validated": True,
        "mode": "keyword",
        "message": "",
    }
    calls = []
    with client_for(tmp_path) as c:
        n = notebook(c)
        thread = c.post(f"/api/notebooks/{n}/chats", json={"title": "Conversation"}).json()["id"]
        endpoint = f"/api/notebooks/{n}/chats/{thread}/turns"
        monkeypatch.setattr(c.app.state.knowledge, "answer", lambda *args: calls.append(args) or answer)
        payload = {"question": "What does the source say?", "request_id": str(uuid4())}
        first = c.post(endpoint, json=payload)
        assert first.status_code == 200 and first.json()["status"] == "completed"
        assert c.post(endpoint, json=payload).json() == first.json()
        assert len(calls) == 1  # A lost response/retry must not charge for another model call.
        assert c.post(endpoint, json={**payload, "question": "different"}).status_code == 409
        other = notebook(c)
        assert c.get(f"/api/notebooks/{other}/chats/{thread}").status_code == 404
        assert c.get(f"/api/notebooks/{n}/chats", headers={"Authorization": "bad"}).status_code == 401
    (tmp_path / "index.sqlite3").unlink()
    with client_for(tmp_path) as c:
        stored = c.get(f"/api/notebooks/{n}/chats/{thread}").json()
        assert stored["turns"][0]["answer"] == answer
        renamed = c.put(f"/api/notebooks/{n}/chats/{thread}", json={"title": "Renamed"})
        assert renamed.json()["turns"] == stored["turns"]
        assert c.delete(f"/api/notebooks/{n}/chats/{thread}").status_code == 200
        assert c.get(f"/api/notebooks/{n}/chats").json() == []
        trashed = tmp_path / "notebooks" / n / "trash/chats" / f"{thread}.json"
        assert json.loads(trashed.read_text())["turns"] == stored["turns"]


def test_interrupted_turn_is_not_replayed_and_failed_turn_keeps_question(tmp_path, monkeypatch):
    store = Store(tmp_path)
    n = store.create_notebook("Legacy notebook")["id"]
    chats = Chats(store)
    thread = chats.create(n, "Chat")["id"]
    request_id = str(uuid4())
    chats.begin(n, thread, request_id, "Interrupted?", "ask")
    with pytest.raises(ConflictError, match="current answer"):
        chats.delete(n, thread)
    with client_for(tmp_path) as c:
        endpoint = f"/api/notebooks/{n}/chats/{thread}/turns"

        def fail(*args):
            raise ValueError("secret-provider-key-must-not-persist")

        monkeypatch.setattr(c.app.state.knowledge, "answer", fail)
        replay = c.post(endpoint, json={"request_id": request_id, "question": "Interrupted?"}).json()
        assert replay["status"] == "interrupted"
        failed = c.post(endpoint, json={"request_id": str(uuid4()), "question": "Retry?"}).json()
        assert failed["status"] == "failed" and failed["question"] == "Retry?"
        assert "secret-provider" not in c.get(f"/api/notebooks/{n}/chats/{thread}").text
        assert c.post(endpoint, json={"request_id": "../outside", "question": "No"}).status_code == 400


def test_note_autosave_preserves_legacy_metadata_and_rejects_external_changes(tmp_path):
    with client_for(tmp_path) as c:
        n = notebook(c)
        original = c.post(f"/api/notebooks/{n}/notes", json={"title": "Legacy", "body": "old"}).json()
        path = tmp_path / "notebooks" / n / "notes" / (original["id"] + ".md")
        path.write_text(path.read_text().replace("---\n", "---\ntags: [keep]\n", 1), encoding="utf-8")
        original = c.get(f"/api/notebooks/{n}/notes").json()[0]
        payload = {k: original[k] for k in ("id", "title", "body", "revision")}
        payload.update(body="autosaved", draft_id=str(uuid4()))
        endpoint = f"/api/notebooks/{n}/notes/autosave"
        saved = c.post(endpoint, json=payload)
        assert saved.status_code == 200
        assert "tags:" in path.read_text() and "autosaved" in path.read_text()
        assert c.get(f"/api/notebooks/{n}/drafts").json() == []
        payload.update(revision=saved.json()["revision"], body="my draft")
        external = path.read_text() + "\nExternal edit from Obsidian\n"
        path.write_text(external, encoding="utf-8")
        assert c.post(endpoint, json=payload).status_code == 409
        assert path.read_text() == external
    with client_for(tmp_path) as c:
        drafts = c.get(f"/api/notebooks/{n}/drafts").json()
        assert drafts[0]["note"]["body"] == "my draft"
        copy = c.post(endpoint, json={**payload, "id": str(uuid4()), "revision": ""})
        assert copy.status_code == 200
        assert path.read_text() == external
        assert len(c.get(f"/api/notebooks/{n}/notes").json()) == 2
        assert c.get(f"/api/notebooks/{n}/drafts").json() == []


def test_autosave_io_failure_keeps_previous_file_and_recovery_draft(tmp_path, monkeypatch):
    import on_knowledge.features.notes.repository as storage

    with client_for(tmp_path) as c:
        n = notebook(c)
        old = c.post(f"/api/notebooks/{n}/notes", json={"title": "Existing", "body": "precious"}).json()
        payload = {**old, "body": "new draft", "draft_id": str(uuid4())}
        original_write = storage.atomic_write

        def fail_note(path, text):
            if path.suffix == ".md":
                raise PermissionError("read-only file")
            original_write(path, text)

        monkeypatch.setattr(storage, "atomic_write", fail_note)
        with pytest.raises(PermissionError):
            c.post(f"/api/notebooks/{n}/notes/autosave", json=payload)
        assert c.get(f"/api/notebooks/{n}/notes").json()[0]["body"] == "precious"
        assert c.get(f"/api/notebooks/{n}/drafts").json()[0]["note"]["body"] == "new draft"
        monkeypatch.setattr(storage, "atomic_write", original_write)
        assert c.post(f"/api/notebooks/{n}/notes/autosave", json=payload).status_code == 200
        assert c.get(f"/api/notebooks/{n}/drafts").json() == []


def test_new_note_revision_prevents_overwrite_and_drafts_are_notebook_scoped(tmp_path):
    with client_for(tmp_path) as c:
        n, other = notebook(c), notebook(c)
        payload = {
            "id": str(uuid4()),
            "title": "New",
            "body": "first",
            "revision": "",
            "draft_id": str(uuid4()),
        }
        endpoint = f"/api/notebooks/{n}/notes/autosave"
        assert c.post(endpoint, json=payload).status_code == 200
        # Replaying an acknowledged-on-disk save after a lost response is harmless.
        assert c.post(endpoint, json=payload).status_code == 200
        assert c.post(endpoint, json={**payload, "body": "second"}).status_code == 409
        assert c.get(f"/api/notebooks/{other}/drafts").json() == []
        assert c.delete(f"/api/notebooks/{other}/drafts/{payload['draft_id']}").status_code == 200
        assert len(c.get(f"/api/notebooks/{n}/drafts").json()) == 1
        assert c.post(endpoint, json={**payload, "id": "../escape"}).status_code == 400
        assert not (tmp_path / "escape.md").exists()
        assert c.get(f"/api/notebooks/{n}/drafts").json()[0]["note"]["body"] == "second"
