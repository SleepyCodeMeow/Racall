import hashlib
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from on_knowledge.app import create_app
from on_knowledge.features.sources.parser import fetch_url_isolated, parse_isolated, supervise


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(tmp_path, "test-session-token-long-enough"),
        headers={"Authorization": "Bearer test-session-token-long-enough"},
    ) as c:
        yield c


def notebook(c, title="Versioned research"):
    r = c.post("/api/notebooks", json={"title": title})
    assert r.status_code == 201
    return r.json()["id"]


def ready(c, n, source, refresh=False):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        item = c.get(f"/api/notebooks/{n}/sources/{source}").json()["source"]
        if refresh:
            if item.get("refresh_status") not in ("queued", "processing"):
                return item
        elif item["status"] not in ("queued", "processing"):
            return item
        time.sleep(0.05)
    pytest.fail("Source did not finish processing")


def upload(c, n, body=b"# Mission\n\nMarigold launches on October 18."):
    r = c.post(f"/api/notebooks/{n}/sources", files={"file": ("mission.md", body)})
    assert r.status_code == 202, r.text
    item = ready(c, n, r.json()["id"])
    assert item["status"] == "ready", item
    return item


def test_notebook_trash_roundtrip_preserves_data_and_isolation(client):
    c = client
    n, other = notebook(c), notebook(c, "Other")
    source = upload(c, n)
    c.post(f"/api/notebooks/{n}/notes", json={"title": "Note", "body": "keep me"})
    c.post(f"/api/notebooks/{n}/chats", json={"title": "Keep chat"})
    root = c.app.state.store.notebook_path(n)
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert c.put(f"/api/notebooks/{n}", json={"title": "Renamed"}).status_code == 200
    before["notebook.yaml"] = (root / "notebook.yaml").read_bytes()
    assert c.delete(f"/api/notebooks/{n}").status_code == 200
    assert c.get(f"/api/notebooks/{n}/sources").status_code == 404
    assert [x["id"] for x in c.get("/api/notebooks").json()] == [other]
    assert c.get("/api/notebooks/trash").json()[0]["title"] == "Renamed"
    assert c.get(f"/api/notebooks/{other}/sources/{source['id']}").status_code == 404
    assert c.post(f"/api/notebooks/{n}/restore").status_code == 200
    after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert before == after
    assert c.get("/api/notebooks/trash").json() == []
    assert c.post(f"/api/notebooks/{n}/search", json={"question": "Marigold"}).json()["evidence"]
    assert c.put(f"/api/notebooks/{n}", json={"title": "  "}).status_code == 422
    assert c.delete("/api/notebooks/not-a-uuid").status_code == 400
    assert c.delete(f"/api/notebooks/{n}", headers={"Authorization": "wrong"}).status_code == 401


def test_notebook_delete_rejects_active_work(client):
    n = notebook(client)
    with client.app.state.store.notebook_operation(n):
        assert client.delete(f"/api/notebooks/{n}").status_code == 409
    assert client.delete(f"/api/notebooks/{n}").status_code == 200


def test_source_versions_preserve_old_citations_and_originals(client):
    c, n = client, notebook(client)
    old = upload(c, n)
    prefix = f"/api/notebooks/{n}/sources/{old['id']}"
    evidence = c.post(f"/api/notebooks/{n}/search", json={"question": "Marigold"}).json()["evidence"][0]
    response = c.put(
        prefix, files={"file": ("updated.md", b"# Mission\n\nMarigold launches on November 22.")}
    )
    assert response.status_code == 202
    new = ready(c, n, old["id"], refresh=True)
    assert new["version"] != old["version"] and not new.get("refresh_error"), new
    versions = c.get(prefix + "/versions").json()
    assert len(versions) == 2 and sum(v["current"] for v in versions) == 1
    assert b"October 18" in c.get(prefix + f"/versions/{old['version']}/original").content
    assert b"November 22" in c.get(prefix + "/original").content
    historical = c.get(prefix + f"/versions/{old['version']}").json()["document"]
    loc = evidence["location"]
    assert (
        historical["elements"][loc["element"]]["text"][loc["offset_start"] : loc["offset_end"]]
        == evidence["quote"]
    )
    current = c.post(f"/api/notebooks/{n}/search", json={"question": "Marigold"}).json()["evidence"]
    assert all(e["version"] == new["version"] for e in current)
    assert any("November 22" in e["quote"] for e in current)
    same = c.put(
        prefix, files={"file": ("updated.md", b"# Mission\n\nMarigold launches on November 22.")}
    ).json()
    assert same["unchanged"]
    assert c.get(prefix + "/versions/not-a-hash").status_code == 400
    assert c.get(prefix + "/versions/" + "f" * 64).status_code == 404


def test_failed_update_keeps_working_version_and_can_retry(client, monkeypatch):
    c, n = client, notebook(client)
    old = upload(c, n)
    prefix = f"/api/notebooks/{n}/sources/{old['id']}"
    store = c.app.state.store
    real_save = store.save_source
    fail = True

    def refuse_promotion(notebook, item):
        nonlocal fail
        if fail and item["version"] != old["version"] and item["status"] == "ready":
            fail = False
            raise PermissionError("Injected commit failure")
        return real_save(notebook, item)

    monkeypatch.setattr(store, "save_source", refuse_promotion)
    assert c.put(prefix, files={"file": ("next.md", b"Marigold launches on December 9.")}).status_code == 202
    failed = ready(c, n, old["id"], refresh=True)
    assert failed["version"] == old["version"] and failed["refresh_status"] == "error"
    assert b"October 18" in c.get(prefix + "/original").content
    assert any(
        "October 18" in e["quote"]
        for e in c.post(f"/api/notebooks/{n}/search", json={"question": "Marigold"}).json()["evidence"]
    )
    with store.db() as db:
        db.execute("DELETE FROM chunks")
        db.execute("DELETE FROM chunks_fts")
    c.app.state.knowledge.recover()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if c.post(f"/api/notebooks/{n}/search", json={"question": "Marigold"}).json()["evidence"]:
            break
        time.sleep(0.05)
    assert c.post(f"/api/notebooks/{n}/search", json={"question": "Marigold"}).json()["evidence"]
    repaired = c.get(prefix).json()["source"]
    assert repaired["version"] == old["version"] and repaired["refresh_status"] == "error"
    assert c.post(prefix + "/reindex").status_code == 202
    new = ready(c, n, old["id"], refresh=True)
    assert new["version"] != old["version"] and not new.get("refresh_error")


def test_legacy_source_migrates_on_refresh(client):
    c, n = client, notebook(client)
    store = c.app.state.store
    data = b"Legacy Marigold is blue."
    source = {
        "id": str(uuid4()),
        "title": "legacy.md",
        "type": "md",
        "original": "original.md",
        "version": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "created_at": "2026-01-01",
        "status": "queued",
        "chunks": 0,
        "url": None,
    }
    root = store.notebook_path(n) / "sources" / source["id"]
    root.mkdir()
    (root / "original.md").write_bytes(data)
    store.save_source(n, source)
    c.app.state.knowledge.ingest(n, source["id"])
    prefix = f"/api/notebooks/{n}/sources/{source['id']}"
    assert c.put(prefix, files={"file": ("new.md", b"Marigold is orange.")}).status_code == 202
    assert ready(c, n, source["id"], refresh=True)["version"] != source["version"]
    assert c.get(prefix + f"/versions/{source['version']}/original").content == data


def test_url_refresh_reuses_identity_and_preserves_old_version(client, monkeypatch):
    import on_knowledge.features.sources.router as routes

    c, n = client, notebook(client)
    monkeypatch.setattr(routes, "fetch_url", lambda url: ("Example", "Marigold before refresh."))
    item = c.post(f"/api/notebooks/{n}/urls", json={"url": "https://example.com"}).json()
    old = ready(c, n, item["id"])
    monkeypatch.setattr(routes, "fetch_url", lambda url: ("Example", "Marigold after refresh."))
    prefix = f"/api/notebooks/{n}/sources/{item['id']}"
    assert c.post(prefix + "/refresh").status_code == 202
    new = ready(c, n, item["id"], refresh=True)
    assert old["version"] != new["version"] and new["id"] == old["id"]
    assert len(c.get(prefix + "/versions").json()) == 2


def test_parser_worker_valid_file_and_ssrf_rejection(tmp_path):
    path = tmp_path / "document.md"
    path.write_text("# Safe\n\nA bounded document.", encoding="utf-8")
    assert parse_isolated(path).elements[-1].text == "A bounded document."
    with pytest.raises(ValueError, match="публичный сайт"):
        fetch_url_isolated("http://127.0.0.1/private")


@pytest.mark.parametrize("limit,seconds,memory", [("time", 0.3, 512), ("memory", 10, 1)])
def test_parser_supervisor_kills_over_budget_process(tmp_path, limit, seconds, memory):
    command = [sys.executable, "-c", "import time; data=bytearray(64*1024*1024); time.sleep(15)"]
    start = time.monotonic()
    with pytest.raises(ValueError, match=limit + " limit"):
        supervise(command, tmp_path / "output.json", seconds, memory)
    assert time.monotonic() - start < 8


@pytest.mark.parametrize("script", ["publish_release.py", "verify_release_build.py"])
def test_release_hold_stops_publication_before_external_actions(tmp_path, script):
    import subprocess

    root = Path(__file__).resolve().parents[1]
    (tmp_path / "scripts").mkdir()
    (tmp_path / "apps/shared").mkdir(parents=True)
    (tmp_path / "apps/shared/release.json").write_text('{"publication": "hold"}', encoding="utf-8")
    target = tmp_path / "scripts" / script
    target.write_bytes((root / "scripts" / script).read_bytes())
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "Publication is on hold" in result.stderr


def test_windows_crt_read_conflict_without_winerror_is_retried(tmp_path, monkeypatch):
    import errno

    import on_knowledge.storage as storage

    path = tmp_path / "new-document.json"
    path.write_text('{"safe":true}', encoding="utf-8")
    read = Path.read_text
    calls = 0

    def temporarily_locked(self, *args, **kwargs):
        nonlocal calls
        if self == path:
            calls += 1
            if calls < 3:
                raise PermissionError(errno.EACCES, "Temporary CRT sharing conflict")
        return read(self, *args, **kwargs)

    monkeypatch.setattr(storage, "WINDOWS", True)
    monkeypatch.setattr(Path, "read_text", temporarily_locked)
    assert storage.read_text(path) == '{"safe":true}'
    assert calls == 3
