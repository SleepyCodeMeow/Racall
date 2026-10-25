"""Saved per-thread choices and lost-response retries through the HTTP API."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from on_knowledge.app import create_app
from on_knowledge.storage import write_json
from test_context import fake_model, source

TOKEN = "context-chat-test-token-long-enough"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path, TOKEN)
    with TestClient(app, headers={"Authorization": "Bearer " + TOKEN}) as client:
        yield client


def chat(client, notebook, **extra):
    response = client.post(f"/api/notebooks/{notebook}/chats", json={"title": "Conversation", **extra})
    assert response.status_code == 201, response.text
    return response.json()


def turn(client, notebook, thread, question="Marigold", **extra):
    return client.post(
        f"/api/notebooks/{notebook}/chats/{thread}/turns",
        json={"request_id": str(uuid4()), "question": question, **extra},
    )


def test_context_create_put_empty_choice_and_invalid_cross_notebook(client, monkeypatch):
    store = client.app.state.store
    notebook = store.create_notebook("One")["id"]
    other = store.create_notebook("Other")["id"]
    local, _ = source(store, notebook, ["Marigold launches in October."])
    foreign, _ = source(store, other, ["Foreign secret."])
    thread = chat(client, notebook, context={"source_ids": [local["id"]]})
    assert thread["context"]["source_ids"] == [local["id"]]
    endpoint = f"/api/notebooks/{notebook}/chats/{thread['id']}/context"
    calls = fake_model(monkeypatch)
    changed = client.put(endpoint, json={"source_ids": []})
    assert changed.status_code == 200 and changed.json()["context"] == {"source_ids": [], "note_ids": []}
    empty = turn(client, notebook, thread["id"]).json()
    assert empty["status"] == "completed" and empty["context_info"]["source_count"] == 0
    assert not empty["answer"]["validated"] and calls == []
    for selection in (
        {"source_ids": [foreign["id"]]},
        {"source_ids": [str(uuid4())]},
        {"note_ids": ["Missing note"]},
    ):
        assert client.put(endpoint, json=selection).status_code == 400
        assert turn(client, notebook, thread["id"], context=selection).status_code == 400
    assert not calls
    restored = client.put(endpoint, json={"source_ids": None}).json()
    assert restored["context"]["source_ids"] is None
    completed = turn(client, notebook, thread["id"]).json()
    assert completed["answer"]["validated"] and len(calls) == 2
    assert completed["context_info"]["source_count"] == 1


def test_followup_only_uses_completed_turns_of_active_thread(client, monkeypatch):
    store = client.app.state.store
    notebook = store.create_notebook("One")["id"]
    source(store, notebook, ["Marigold launches in October."])
    first, second = chat(client, notebook), chat(client, notebook)
    calls = fake_model(monkeypatch)
    initial = turn(client, notebook, first["id"], "Tell me about Marigold").json()
    assert initial["answer"]["validated"]
    followup = turn(client, notebook, first["id"], "When does it launch?").json()
    assert followup["answer"]["validated"] and followup["context_info"]["history_turns"] == 1
    assert calls[2][1]["conversation_history"][0]["question"] == "Tell me about Marigold"
    assert len(calls) == 4  # Two calls per answer, no follow-up rewrite request.
    isolated = turn(client, notebook, second["id"], "When does it launch?").json()
    assert isolated["context_info"]["history_turns"] == 0
    # No matching terms and no active-thread history means no calls for this thread.
    assert not isolated["answer"]["validated"] and len(calls) == 4


def test_selection_change_excludes_previous_assistant_echo(client, monkeypatch):
    store = client.app.state.store
    notebook = store.create_notebook("One")["id"]
    first, _ = source(store, notebook, ["Marigold launches in October."])
    second, _ = source(store, notebook, ["Cedar is a separate source."])
    thread = chat(client, notebook, context={"source_ids": [first["id"]]})
    calls = fake_model(monkeypatch)
    assert turn(client, notebook, thread["id"]).json()["answer"]["validated"]
    changed = turn(
        client, notebook, thread["id"], "What about it?", context={"source_ids": [second["id"]]}
    ).json()
    assert changed["context_info"]["history_turns"] == 0
    assert changed["context_info"]["history_truncated"] and len(calls) == 2


def test_request_id_retry_preserves_snapshot_and_rejects_changed_payload(client, monkeypatch):
    store = client.app.state.store
    notebook = store.create_notebook("One")["id"]
    item, _ = source(store, notebook, ["Marigold launches in October."])
    thread = chat(client, notebook)
    calls = fake_model(monkeypatch)
    request_id = str(uuid4())
    first = turn(client, notebook, thread["id"], request_id=request_id).json()
    assert first["status"] == "completed"
    store.save_source(notebook, {**item, "version": "edited-after-completion"})
    retried = turn(client, notebook, thread["id"], request_id=request_id)
    assert retried.json() == first and len(calls) == 2
    for extra in ({"question": "different"}, {"mode": "search"}, {"context": {"source_ids": []}}):
        question = extra.pop("question", "Marigold")
        assert (
            turn(client, notebook, thread["id"], question, request_id=request_id, **extra).status_code == 409
        )


def test_material_change_during_model_discards_partial_response(client, monkeypatch):
    store = client.app.state.store
    notebook = store.create_notebook("One")["id"]
    item, _ = source(store, notebook, ["Marigold launches in October."])
    thread = chat(client, notebook)
    calls = fake_model(
        monkeypatch,
        hook=lambda count: (
            store.save_source(notebook, {**item, "version": "changed-during-model"}) if count == 1 else None
        ),
    )
    failed = turn(client, notebook, thread["id"]).json()
    assert failed["status"] == "failed" and failed["error_code"] == "context_changed"
    assert "answer" not in failed and len(calls) == 1
    saved = client.get(f"/api/notebooks/{notebook}/chats/{thread['id']}").json()["turns"][0]
    assert saved == failed


def test_old_transcript_opens_with_default_context_without_rewriting(client):
    store = client.app.state.store
    notebook = store.create_notebook("One")["id"]
    thread = chat(client, notebook)
    path = store.notebook_path(notebook) / "chats" / (thread["id"] + ".json")
    thread.pop("context")
    write_json(path, thread)
    before = path.read_bytes()
    response = client.get(f"/api/notebooks/{notebook}/chats/{thread['id']}")
    assert response.json()["context"] == {"source_ids": None, "note_ids": []}
    assert path.read_bytes() == before
    assert "context" not in json.loads(before)
