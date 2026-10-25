"""A stopped live evaluator must drain its real app worker without new inference."""

from __future__ import annotations

import importlib
import json
import socket
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from on_knowledge import providers
from on_knowledge.app import create_app
from on_knowledge.completion_stream import _cancellation
from on_knowledge.storage import write_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def helper(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("model_evaluation03.guard")


def test_stop_during_studio_drains_worker_before_restoring_hooks(tmp_path, monkeypatch, helper):
    output = tmp_path / "evidence"
    output.mkdir()
    vault = tmp_path / "knowledge"
    vault.mkdir()
    write_json(
        vault / "settings.json",
        {
            "provider": "ollama",
            "profiles": {"ollama": {"base_url": "http://127.0.0.1:11434/v1", "model": "fixture"}},
            "embeddings": {"provider": "ollama", "base_url": "http://127.0.0.1:11434/v1", "model": ""},
        },
    )
    guard = helper.LiveGuard(output, "http://127.0.0.1:11434/v1", "fixture", "fixture-source")
    runtime_calls = []
    monkeypatch.setattr(guard, "runtime", lambda label: runtime_calls.append(label))
    monkeypatch.setattr(providers, "_stored_key", lambda base: "")

    def forbidden_network(*args, **kwargs):
        pytest.fail("The offline test must not access a real model or metadata endpoint")

    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    entered, stop_seen, app_closed, release = (threading.Event() for _ in range(4))
    hooks_observed = []
    transport_calls = []

    def blocked_transport(url, headers, payload, **kwargs):
        transport_calls.append(payload)
        entered.set()
        checkpoint = _cancellation.get()
        assert checkpoint is not None
        try:
            while True:
                checkpoint()
                time.sleep(0.01)
        except helper.EvaluationStop:
            stop_seen.set()
            assert release.wait(5), "Test did not release the stopped transport"
            raise
        finally:
            hooks_observed.append(providers.complete_json is not blocked_transport)

    monkeypatch.setattr(providers, "complete_json", blocked_transport)
    original_complete = providers.OpenAICompatible.complete
    app = create_app(vault, "offline-studio-stop-token")
    headers = {"Authorization": "Bearer offline-studio-stop-token"}

    def release_after_application_close():
        if app_closed.wait(5):
            time.sleep(0.05)
            release.set()

    releaser = threading.Thread(target=release_after_application_close)
    releaser.start()
    try:
        with guard.instrument():
            with TestClient(app, headers=headers) as client:
                notebook = client.post("/api/notebooks", json={"title": "Synthetic STOP"}).json()["id"]
                base = "/api/notebooks/" + notebook
                note = client.post(base + "/notes", json={"title": "Fixture", "body": "A saved fact."}).json()
                response = client.post(
                    base + "/jobs",
                    json={
                        "request_id": str(uuid4()),
                        "kind": "summary",
                        "language": "en",
                        "context": {"source_ids": [], "note_ids": [note["id"]]},
                    },
                )
                assert response.status_code == 202
                job = response.json()
                assert entered.wait(5)
                (output / "STOP").write_text("independent review rejected the answer", encoding="utf-8")
                assert stop_seen.wait(5)
                before_cleanup = list(runtime_calls)
                with pytest.raises(helper.EvaluationStop, match="STOP file"):
                    providers.OpenAICompatible(app.state.store.settings()).complete("No new inference", {})
                assert len(transport_calls) == 1
            # Application close signals its daemon worker; it deliberately does
            # not join it. The helper context must keep its hooks until release.
            app_closed.set()
        trace = json.loads((output / "provider-trace.json").read_text("utf-8"))
        assert trace["shutdown"]["status"] == "drained"
        assert trace["shutdown"]["unfinished_call_ids"] == []
        assert len(trace["calls"]) == len(transport_calls) == 1
        assert trace["calls"][0]["status"] == "failed"
        assert trace["calls"][0]["finished_at"]
        assert "STOP file" in trace["calls"][0]["error"]
        assert hooks_observed == [True], "Hooks restored before the worker finalized"
        assert runtime_calls == before_cleanup, "Shutdown made a resource/model request"
        assert providers.complete_json is blocked_transport
        assert providers.OpenAICompatible.complete is original_complete
        assert app.state.jobs.get(notebook, job["id"])["status"] == "interrupted"
        assert app.state.jobs.materials.list(notebook) == []
    finally:
        app_closed.set()
        release.set()
        releaser.join(timeout=5)


def test_shutdown_timeout_is_explicit_and_does_not_forge_a_terminal_call(tmp_path, monkeypatch, helper):
    guard = helper.LiveGuard(tmp_path, "http://127.0.0.1:11434/v1", "fixture", "source")
    runtime_calls = []
    monkeypatch.setattr(guard, "runtime", lambda label: runtime_calls.append(label))
    original_complete, original_transport = providers.OpenAICompatible.complete, providers.complete_json
    original_drain = guard.drain_shutdown
    monkeypatch.setattr(guard, "drain_shutdown", lambda: original_drain(timeout=0.01))
    try:
        with pytest.raises(helper.EvaluationStop, match="shutdown timed out"):
            with guard.instrument():
                guard.serial.acquire()
                guard.calls.append({"id": 1, "status": "running"})
                guard.failure = "A prior provider failure"
        trace = json.loads((tmp_path / "provider-trace.json").read_text("utf-8"))
        assert trace["shutdown"]["status"] == "timed_out"
        assert trace["shutdown"]["unfinished_call_ids"] == [1]
        assert trace["stop_reason"] == "A prior provider failure"
        assert trace["calls"] == [{"id": 1, "status": "running"}]
        assert runtime_calls == ["before acceptance"]
        assert providers.OpenAICompatible.complete is original_complete
        assert providers.complete_json is original_transport
    finally:
        guard.serial.release()
