"""Frozen provider protocol smoke: owned loopback fixtures, no real credentials or models."""

import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("RACALL_BACKEND_BINARY", str(
    ROOT / "release/win-unpacked/resources/backend/open-notebook-api.exe")))
PROVIDERS = ("openai", "anthropic", "ollama", "ollama_cloud", "llama_cpp")
FACT = "Marigold launches on October 18."
QUESTION = "When does Marigold launch?"
KEYS = {"openai": "fixture-openai", "anthropic": "fixture-anthropic", "ollama_cloud": "fixture-ollama"}


class Fixture(BaseHTTPRequestHandler):
    calls = []
    errors = []
    malformed = False
    session_token = ""

    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            assert len(raw) < 256 * 1024 and self.session_token not in raw.decode()
            assert all(self.session_token not in value for value in self.headers.values())
            body = json.loads(raw)
            provider = body["model"].removeprefix("fixture-")
            assert provider in PROVIDERS and body["stream"] is True
            native = provider == "anthropic"
            assert self.path == ("/v1/messages" if native else "/v1/chat/completions")
            if native:
                assert self.headers.get("x-api-key") == KEYS[provider]
                assert self.headers.get("anthropic-version") == "2023-06-01"
                assert "Authorization" not in self.headers and isinstance(body["system"], str)
                assert body["max_tokens"] == 4096 and len(body["messages"]) == 1
            else:
                assert self.headers.get("Authorization") == "Bearer " + KEYS.get(provider, "ollama")
                assert "x-api-key" not in self.headers and body["response_format"] == {"type": "json_object"}
            data = json.loads(body["messages"][0 if native else 1]["content"])
            stage = "critic" if "claims" in data else "writer" if "evidence" in data else "planner"
            self.calls.append({"provider": provider, "stage": stage, "native": native})
            if stage == "critic":
                assert data["claims"][0]["claim_id"] == "C1"
                result = {"supported_claim_ids": ["C1"]}
            elif stage == "writer":
                assert data["evidence"][0]["id"] == "E1" and FACT in data["evidence"][0]["quote"]
                result = {"claims": [{"text": FACT, "evidence_ids": ["E1"]}], "message": ""}
            else:
                result = {"queries": ["Marigold launch"]}
            content = json.dumps(result)
            if native:
                events = [{"type": "message_start", "message": {"type": "message", "role": "assistant",
                           "content": [], "stop_reason": None}},
                          {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                          {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": content}},
                          {"type": "content_block_stop", "index": 0},
                          {"type": "message_delta", "delta": {"stop_reason": "end_turn"}}, {"type": "message_stop"}]
                if self.malformed:
                    events.pop()
                wire = "".join(f"event: {item['type']}\ndata: {json.dumps(item)}\n\n" for item in events)
            else:
                wire = "".join("data: " + json.dumps({"choices": [{"index": 0, "delta": delta,
                               "finish_reason": reason}]}) + "\n\n" for delta, reason in
                               [({"reasoning": "Untrusted draft"}, None), ({"content": content}, None), ({}, "stop")])
                wire += "data: [DONE]\n\n"
            encoded = wire.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as error:
            self.errors.append(type(error).__name__)
            self.send_error(500, "Invalid deterministic fixture request")


@contextmanager
def backend(data, token):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "OPENNOTEBOOK_SESSION_TOKEN": token,
           "OPENAI_API_KEY": KEYS["openai"], "ANTHROPIC_API_KEY": KEYS["anthropic"],
           "OLLAMA_API_KEY": KEYS["ollama_cloud"], "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Keyring"}
    env.pop("OPENNOTEBOOK_API_KEY", None)
    with (data / "process.log").open("a", encoding="utf-8") as log:
        process = subprocess.Popen([str(BINARY), "--data-dir", str(data), "--port", str(port)], env=env,
                                   stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20, trust_env=False,
                              headers={"Authorization": "Bearer " + token}) as client:
                for _ in range(200):
                    assert process.poll() is None, "Frozen backend exited; inspect process.log"
                    try:
                        if client.get("/health", timeout=.5).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.1)
                else:
                    raise AssertionError("Frozen backend startup deadline exceeded")
                yield client
        finally:
            owned = psutil.Process(process.pid).children(recursive=True) if process.poll() is None else []
            if process.poll() is None:
                process.terminate()
            for child in owned:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            _, alive = psutil.wait_procs(owned, timeout=5)
            for child in alive:
                child.kill()
            psutil.wait_procs(alive, timeout=5)


def api(client, method, route, **kwargs):
    response = client.request(method, "/api" + route, **kwargs)
    assert response.is_success, f"Frozen API returned HTTP {response.status_code} for {route}"
    return response.json()


def main():
    assert BINARY.is_file(), "Build the frozen backend before running provider checks"
    data = ROOT / "test-results" / ("provider-bundle-" + secrets.token_hex(6))
    data.mkdir(parents=True)
    token = Fixture.session_token = secrets.token_hex(32)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/v1"
    profiles = {name: {"base_url": base, "model": "fixture-" + name} for name in PROVIDERS}
    try:
        with backend(data, token) as client:
            api(client, "PUT", "/settings", json={"provider": "openai", "profiles": profiles,
                "embeddings": {"provider": "openai", "base_url": base, "model": ""}})
            notebook = api(client, "POST", "/notebooks", json={"title": "Frozen provider fixtures"})["id"]
            route = f"/notebooks/{notebook}"
            source = api(client, "POST", route + "/sources", files={"file": ("facts.md", FACT.encode())})["id"]
            for _ in range(200):
                state = api(client, "GET", route + f"/sources/{source}")["source"]
                if state["status"] in ("ready", "error"):
                    break
                time.sleep(.1)
            assert state["status"] == "ready"
            sessions = []
            for provider in PROVIDERS:
                api(client, "PUT", "/settings", json={"provider": provider})
                before = len(Fixture.calls)
                session = api(client, "POST", route + "/research", json={"question": QUESTION})
                answer = session["answer"]
                assert session["status"] == "completed" and answer["validated"]
                citation = answer["citations"][0]
                assert citation["source_id"] == source and citation["version"] == state["version"]
                assert citation["id"] != "E1" and FACT in citation["quote"]
                assert answer["claims"] == [{"text": FACT, "evidence_ids": [citation["id"]]}]
                assert [item["stage"] for item in Fixture.calls[before:]] == ["planner", "writer", "critic"]
                saved = api(client, "POST", route + f"/research/{session['id']}/save")
                assert "## Sources" in saved["body"] and FACT in saved["body"]
                memory = json.loads((data / "notebooks" / notebook / "memory" / f"{session['id']}.json")
                                    .read_text("utf-8"))
                assert memory["finding"] == answer["claims"] and memory["supporting_citations"] == answer["citations"]
                sessions.append(session)
            artifacts = api(client, "GET", route + "/artifacts")
            snapshot = {str(path): path.read_bytes() for folder in ("research", "artifacts", "memory")
                        for path in (data / "notebooks" / notebook / folder).glob("*")}
            api(client, "PUT", "/settings", json={"provider": "anthropic"})
            Fixture.malformed = True
            before = len(Fixture.calls)
            failed = client.post("/api" + route + "/ask", json={"question": QUESTION})
            assert failed.status_code == 400 and set(failed.json()) == {"detail"}
            assert "поток ответа" in failed.json()["detail"] and len(Fixture.calls) == before + 1
            assert token not in failed.text and all(key not in failed.text for key in KEYS.values())
        calls = len(Fixture.calls)
        with backend(data, token) as client:
            assert api(client, "GET", route + "/research") == list(reversed(sessions))
            assert api(client, "GET", route + "/artifacts") == artifacts
            original = client.get("/api" + route + f"/sources/{source}/original")
            assert original.status_code == 200 and original.content == FACT.encode()
        assert len(Fixture.calls) == calls and not Fixture.errors
        assert all(Path(path).read_bytes() == value for path, value in snapshot.items())
        (data / "result.json").write_text(json.dumps({"providers": list(PROVIDERS), "calls": Fixture.calls,
            "research_saved_reopened": True, "truncated_claude_rejected": True}, indent=2), encoding="utf-8")
        print(f"Frozen provider protocols, citations, save/reopen and truncated Claude checks passed: {data}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
