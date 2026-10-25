import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from on_knowledge.features.appearance.router import create_router
from on_knowledge.storage import Store, write_json


def connection(root):
    app = FastAPI()
    app.include_router(create_router(Store(root)))
    return TestClient(app)


def test_default_preserves_existing_light_ui_without_writing_a_preference(tmp_path):
    with connection(tmp_path) as client:
        assert client.get("/api/appearance").json() == {"theme": "light"}
    assert not (tmp_path / "appearance.json").exists()


@pytest.mark.parametrize("theme", ["light", "dark", "system"])
def test_theme_survives_application_restart(tmp_path, theme):
    with connection(tmp_path) as client:
        response = client.put("/api/appearance", json={"theme": theme})
        assert response.status_code == 200
        assert response.json() == {"theme": theme}
    with connection(tmp_path) as restarted:
        assert restarted.get("/api/appearance").json() == {"theme": theme}
    assert json.loads((tmp_path / "appearance.json").read_text("utf-8")) == {"theme": theme}
    assert list(tmp_path.glob("appearance.json.*.tmp")) == []


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"theme": "night"},
        {"theme": "Dark"},
        {"theme": None},
        {"theme": 1},
        {"theme": True},
        {"theme": ["dark"]},
        {"theme": "dark", "locale": "ru"},
        {"theme": "dark", "api_key": "secret"},
    ],
)
def test_invalid_body_cannot_replace_the_saved_theme(tmp_path, body):
    path = tmp_path / "appearance.json"
    write_json(path, {"theme": "system"})
    before = path.read_bytes()
    with connection(tmp_path) as client:
        assert client.put("/api/appearance", json=body).status_code == 422
        assert client.get("/api/appearance").json() == {"theme": "system"}
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "raw",
    [
        "{",
        "[]",
        '"dark"',
        "null",
        '{"theme": "unknown"}',
        '{"theme": null}',
        '{"theme": 7}',
        "{}",
    ],
)
def test_corrupt_or_unsupported_preference_falls_back_without_rewriting(tmp_path, raw):
    path = tmp_path / "appearance.json"
    path.write_text(raw, "utf-8")
    before = path.read_bytes()
    with connection(tmp_path) as client:
        assert client.get("/api/appearance").json() == {"theme": "light"}
    assert path.read_bytes() == before


def test_theme_save_does_not_change_locale_provider_settings_or_content(tmp_path):
    write_json(tmp_path / "preferences.json", {"locale": "ru"})
    write_json(tmp_path / "settings.json", {"provider": "ollama", "model": "personal-model"})
    vault = tmp_path / "notebooks"
    vault.mkdir()
    (vault / "personal-note.md").write_text("# Personal note\nDo not change.", "utf-8")
    protected = [tmp_path / "preferences.json", tmp_path / "settings.json", vault / "personal-note.md"]
    before = {path: path.read_bytes() for path in protected}
    with connection(tmp_path) as client:
        assert client.put("/api/appearance", json={"theme": "dark"}).status_code == 200
    assert {path: path.read_bytes() for path in protected} == before
