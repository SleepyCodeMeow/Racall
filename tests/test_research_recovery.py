import json
from uuid import uuid4

from fastapi.testclient import TestClient
from on_knowledge.app import create_app
from on_knowledge.features.notebooks.repository import Notebooks
from on_knowledge.storage import Store, write_json

TOKEN = "research-recovery-test-token-long-enough"
HEADERS = {"Authorization": "Bearer " + TOKEN}


def session(status, question):
    return {
        "id": str(uuid4()), "question": question, "status": status,
        "created_at": "2026-10-17T10:00:00+00:00", "steps": [],
    }


def client_for(path):
    return TestClient(create_app(path, TOKEN), headers=HEADERS)


def test_startup_marks_interrupted_research_without_replaying_or_changing_results(tmp_path, monkeypatch):
    store = Store(tmp_path)
    notebook = store.create_notebook("Recovered research")["id"]
    directory = store.notebook_path(notebook) / "research"
    running = session("running", "Unfinished question")
    running["steps"] = [{"stage": "planner", "queries": ["saved plan"]}]
    completed = session("completed", "Completed question")
    completed["answer"] = {"claims": [{"text": "Keep this finding", "evidence_ids": ["c1"]}],
                           "citations": [{"id": "c1", "quote": "Exact saved quote"}]}
    failed = session("failed", "Failed question")
    for item in (running, completed, failed):
        write_json(directory / (item["id"] + ".json"), item)
    untouched = {
        item["id"]: (directory / (item["id"] + ".json")).read_bytes()
        for item in (completed, failed)
    }
    calls = []

    def no_provider(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Recovery must never replay model work")

    monkeypatch.setattr("on_knowledge.knowledge.completion_provider", no_provider)
    with client_for(tmp_path) as client:
        response = client.get(f"/api/notebooks/{notebook}/research")
        assert response.status_code == 200
        results = {item["id"]: item for item in response.json()}
        recovered = results[running["id"]]
        assert recovered["status"] == "interrupted"
        assert recovered["question"] == running["question"]
        assert recovered["steps"] == running["steps"]
        assert recovered["finished_at"]
        assert results[completed["id"]] == completed
        assert results[failed["id"]] == failed
    saved = (directory / (running["id"] + ".json")).read_bytes()
    with client_for(tmp_path) as client:
        assert client.get(f"/api/notebooks/{notebook}/research").status_code == 200
    assert (directory / (running["id"] + ".json")).read_bytes() == saved
    assert all((directory / (key + ".json")).read_bytes() == data for key, data in untouched.items())
    assert not calls


def test_research_recovery_only_visits_active_notebooks(tmp_path):
    store = Store(tmp_path)
    # A notebook without a research directory is valid older data.
    active = store.create_notebook("Older notebook")["id"]
    (store.notebook_path(active) / "research").rmdir()
    deleted = store.create_notebook("Trashed notebook")["id"]
    item = session("running", "Preserve trashed data")
    write_json(store.notebook_path(deleted) / "research" / (item["id"] + ".json"), item)
    notebooks = Notebooks(store)
    notebooks.delete(deleted)
    path = notebooks.trash / deleted / "research" / (item["id"] + ".json")
    before = path.read_bytes()
    with client_for(tmp_path) as client:
        assert client.get(f"/api/notebooks/{active}/research").json() == []
        assert client.get(f"/api/notebooks/{deleted}/research").status_code == 404
    assert path.read_bytes() == before
    assert json.loads(path.read_text("utf-8"))["status"] == "running"
