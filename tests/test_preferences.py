import json

from fastapi.testclient import TestClient
from on_knowledge.app import create_app

TOKEN = "test-session-token-long-enough"


def test_language_preference_survives_restart_without_changing_provider_or_notes(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN), headers={"Authorization": "Bearer " + TOKEN}) as client:
        assert client.get("/api/preferences").json() == {"locale": "en"}
        original_settings = client.get("/api/settings").json()
        notebook = client.post("/api/notebooks", json={"title": "Мои источники"}).json()
        note = client.post(f'/api/notebooks/{notebook["id"]}/notes', json={"title": "Моя заметка", "body": "Text stays unchanged. Текст не меняется."}).json()
        assert client.put("/api/preferences", json={"locale": "ru"}).json() == {"locale": "ru"}
        assert client.put("/api/preferences", json={"locale": "de"}).status_code == 422
        assert client.get("/api/preferences").json() == {"locale": "ru"}
        assert client.get("/api/preferences", headers={"Authorization": "bad"}).status_code == 401
        assert client.get("/api/settings").json() == original_settings
        assert client.get(f'/api/notebooks/{notebook["id"]}/notes').json()[0]["body"] == note["body"]
    with TestClient(create_app(tmp_path, TOKEN), headers={"Authorization": "Bearer " + TOKEN}) as restarted:
        assert restarted.get("/api/preferences").json() == {"locale": "ru"}
        assert restarted.put("/api/preferences", json={"locale": "en"}).status_code == 200
    assert json.loads((tmp_path / "preferences.json").read_text())["locale"] == "en"


def test_invalid_preference_file_falls_back_to_english(tmp_path):
    (tmp_path / "preferences.json").write_text("broken", encoding="utf-8")
    with TestClient(create_app(tmp_path, TOKEN), headers={"Authorization": "Bearer " + TOKEN}) as client:
        assert client.get("/api/preferences").json() == {"locale": "en"}
        assert client.put("/api/preferences", json={"locale": "ru"}).status_code == 200


def test_atomic_write_retries_windows_sharing_conflicts(tmp_path, monkeypatch):
    from on_knowledge import storage

    path = tmp_path / "source.json"
    storage.atomic_write(path, "old")
    replace = storage.os.replace
    calls = []

    def briefly_locked(source, target):
        calls.append(1)
        if len(calls) < 3:
            error = PermissionError("sharing violation")
            error.winerror = 32
            raise error
        replace(source, target)

    monkeypatch.setattr(storage.os, "replace", briefly_locked)
    monkeypatch.setattr(storage.time, "sleep", lambda _: None)
    storage.atomic_write(path, "new")
    assert path.read_text() == "new"
    assert len(calls) == 3
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_keeps_original_on_permanent_failure(tmp_path, monkeypatch):
    import pytest
    from on_knowledge import storage

    path = tmp_path / "preferences.json"
    storage.atomic_write(path, "original")
    calls = []

    def locked(source, target):
        calls.append(1)
        error = PermissionError("access denied")
        error.winerror = 5
        raise error

    monkeypatch.setattr(storage.os, "replace", locked)
    monkeypatch.setattr(storage.time, "sleep", lambda _: None)
    with pytest.raises(PermissionError):
        storage.atomic_write(path, "replacement")
    assert path.read_text() == "original"
    assert len(calls) == 8
    assert not list(tmp_path.glob("*.tmp"))


def test_metadata_read_retries_transient_windows_access_conflict(tmp_path, monkeypatch):
    from pathlib import Path

    from on_knowledge import storage

    path = tmp_path / "source.json"
    path.write_text('{"status": "ready"}', encoding="utf-8")
    original = Path.read_text
    calls = []

    def briefly_locked(self, *args, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            error = PermissionError("sharing violation")
            error.winerror = 32
            raise error
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", briefly_locked)
    monkeypatch.setattr(storage.time, "sleep", lambda _: None)
    assert json.loads(storage.read_text(path))["status"] == "ready"
    assert len(calls) == 3


def test_metadata_read_does_not_hide_real_permission_failure(tmp_path, monkeypatch):
    from pathlib import Path

    import pytest
    from on_knowledge import storage

    calls = []

    def denied(self, *args, **kwargs):
        calls.append(1)
        raise PermissionError("permission denied")

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(PermissionError):
        storage.read_text(tmp_path / "source.json")
    assert len(calls) == 1
