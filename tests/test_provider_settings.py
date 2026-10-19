import json

import pytest
from fastapi.testclient import TestClient
from on_knowledge import providers
from on_knowledge.app import create_app
from on_knowledge.provider_settings import embedding_settings, normalize_settings
from on_knowledge.storage import Store, write_json

TOKEN = "provider-settings-token-long-enough"


@pytest.fixture
def credentials(monkeypatch):
    keys = {}
    reads = []
    writes = []

    def read(settings):
        reads.append((settings["provider"], settings["base_url"]))
        return keys.get(settings["base_url"], "")

    def save(base_url, value):
        writes.append((base_url, value))
        keys[base_url] = value

    monkeypatch.setattr(providers, "provider_key", read, raising=False)
    monkeypatch.setattr("on_knowledge.features.settings.router.save_key", save)
    return keys, reads, writes


def connection(root):
    return TestClient(create_app(root, TOKEN), headers={"Authorization": "Bearer " + TOKEN})


def test_fresh_defaults_are_four_services_with_ollama_modes_and_separate_embeddings(tmp_path, credentials):
    with connection(tmp_path) as client:
        result = client.get("/api/settings").json()
    assert result["provider"] == "openai"
    assert set(result["profiles"]) == {
        "openai", "anthropic", "ollama", "ollama_cloud", "llama_cpp", "openai_compatible",
    }
    assert result["base_url"] == "https://api.openai.com/v1"
    assert result["profiles"]["anthropic"]["base_url"] == "https://api.anthropic.com/v1"
    assert result["profiles"]["ollama_cloud"]["base_url"] == "https://ollama.com/v1"
    assert result["profiles"]["llama_cpp"]["base_url"] == "http://127.0.0.1:8080/v1"
    assert result["embeddings"]["model"] == result["embedding_model"] == ""
    assert not result["has_key"]
    assert not (tmp_path / "settings.json").exists()


def test_legacy_read_preserves_endpoint_and_embedding_identity_without_rewriting(tmp_path, credentials):
    raw = {"base_url": "http://localhost:11434/v1/", "model": "My model:Q4", "embedding_model": "nomic"}
    path = tmp_path / "settings.json"
    write_json(path, raw)
    before = path.read_bytes()
    with connection(tmp_path) as client:
        result = client.get("/api/settings").json()
    assert path.read_bytes() == before
    assert result["provider"] == "openai_compatible"
    assert result["base_url"] == raw["base_url"]
    assert result["model"] == raw["model"]
    assert embedding_settings(result) == {
        "provider": "openai_compatible", "base_url": raw["base_url"],
        "model": "", "embedding_model": "nomic",
    }
    assert result["embedding_base_url"] + "/" + result["embedding_model"] == raw["base_url"] + "/nomic"


def test_profiles_switch_and_survive_restart_without_changing_embeddings(tmp_path, credentials):
    keys, _, writes = credentials
    with connection(tmp_path) as client:
        assert client.put("/api/settings", json={
            "provider": "ollama",
            "profiles": {"ollama": {"base_url": "http://127.0.0.1:11434/v1", "model": "local-model"}},
            "embeddings": {"provider": "ollama", "base_url": "http://localhost:11434/v1", "model": "embed-model"},
            "embedding_api_key": "embedding-secret",
        }).status_code == 200
        assert client.put("/api/settings", json={
            "provider": "anthropic",
            "profiles": {"anthropic": {"base_url": "https://api.anthropic.com/v1", "model": "claude-model"}},
            "api_key": "anthropic-secret",
        }).status_code == 200
        current = client.get("/api/settings").json()
        assert current["profiles"]["ollama"]["model"] == "local-model"
        assert current["model"] == "claude-model"
        assert current["has_key"] and current["embeddings"]["has_key"]
        assert current["embeddings"]["model"] == "embed-model"
        assert "anthropic-secret" not in json.dumps(current)
        assert "embedding-secret" not in json.dumps(current)
    with connection(tmp_path) as restarted:
        assert restarted.get("/api/settings").json() == current
        assert restarted.put("/api/settings", json={"provider": "ollama"}).status_code == 200
        result = restarted.get("/api/settings").json()
    assert result["model"] == "local-model"
    assert result["embeddings"] == current["embeddings"]
    stored = json.loads((tmp_path / "settings.json").read_text())
    assert set(stored) == {"provider", "profiles", "embeddings"}
    assert "secret" not in json.dumps(stored)
    assert writes == [
        ("http://localhost:11434/v1", "embedding-secret"),
        ("https://api.anthropic.com/v1", "anthropic-secret"),
    ]
    assert keys["https://api.anthropic.com/v1"] == "anthropic-secret"


def test_legacy_put_preserves_inactive_profiles_and_old_embedding_semantics(tmp_path, credentials):
    with connection(tmp_path) as client:
        client.put("/api/settings", json={
            "provider": "anthropic", "profiles": {
                "anthropic": {"base_url": "https://api.anthropic.com/v1", "model": "remember-me"},
            },
        })
        assert client.put("/api/settings", json={
            "base_url": "http://localhost:11234/v1/", "model": "legacy", "embedding_model": "embed",
            "api_key": "legacy-secret",
        }).status_code == 200
        result = client.get("/api/settings").json()
        assert result["provider"] == "openai_compatible"
        assert result["base_url"] == "http://localhost:11234/v1"
        assert result["profiles"]["anthropic"]["model"] == "remember-me"
        assert result["embeddings"] == {
            "provider": "openai_compatible", "base_url": result["base_url"], "model": "embed", "has_key": True,
        }
        assert client.put("/api/settings", json={"base_url": result["base_url"], "model": "legacy"}).status_code == 200
        assert client.get("/api/settings").json()["embedding_model"] == ""


@pytest.mark.parametrize("body", [
    {"provider": "codex"},
    {"provider": "openai", "profiles": {"invalid": {"base_url": "https://example.com/v1", "model": "m"}}},
    {"provider": "openai", "profiles": {"openai": {"base_url": "https://example.com/v1", "model": "m", "api_key": "nested-secret"}}},
    {"provider": "openai", "embeddings": {"provider": "anthropic", "base_url": "https://example.com/v1", "model": "e"}},
    {"provider": "openai", "embeddings": {"provider": "openai", "base_url": "https://example.com/v1", "model": "e", "other": True}},
    {"provider": "openai", "extra": True},
    {"base_url": "https://example.com/v1", "model": 123},
    {"provider": "openai", "api_key": "long-secret-" * 500},
    {"provider": "openai", "profiles": {"openai": {"base_url": "https://example.com/v1", "model": "m" * 201}}},
    {"base_url": "http://example.com/v1", "model": "m"},
    {"provider": "openai", "profiles": {"openai": {"base_url": "https://user:password@example.com/v1", "model": "m"}}},
    {"provider": "openai", "profiles": {"openai": {"base_url": "https://example.com/v1?api_key=secret", "model": "m"}}},
    {"provider": "openai", "profiles": {"openai": {"base_url": "https://example.com/v1#fragment", "model": "m"}}},
])
def test_invalid_settings_reject_without_writing_or_echoing_secrets(tmp_path, credentials, body):
    _, _, writes = credentials
    with connection(tmp_path) as client:
        response = client.put("/api/settings", json=body)
    assert response.status_code == 422, response.text
    assert "nested-secret" not in response.text
    assert "long-secret" not in response.text
    assert not writes
    assert not (tmp_path / "settings.json").exists()


def test_settings_auth_precedes_secret_storage_and_validation(tmp_path, credentials):
    _, reads, writes = credentials
    with connection(tmp_path) as client:
        assert client.put("/api/settings", headers={"Authorization": "wrong"}, json={
            "provider": "anthropic", "api_key": "must-not-be-saved",
        }).status_code == 401
        assert client.get("/api/settings", headers={"Authorization": "wrong"}).status_code == 401
    assert reads == writes == []
    assert not (tmp_path / "settings.json").exists()


def test_invalid_profile_cannot_partially_replace_saved_settings_or_credentials(tmp_path, credentials):
    _, _, writes = credentials
    with connection(tmp_path) as client:
        assert client.put("/api/settings", json={
            "provider": "openai", "profiles": {
                "openai": {"base_url": "https://api.openai.com/v1", "model": "keep-model"},
            },
        }).status_code == 200
        before = (tmp_path / "settings.json").read_bytes()
        assert client.put("/api/settings", json={
            "provider": "anthropic", "api_key": "must-not-be-saved",
            "embeddings": {"provider": "ollama", "base_url": "http://remote.example/v1", "model": "e"},
        }).status_code == 422
    assert (tmp_path / "settings.json").read_bytes() == before
    assert writes == []


def test_store_settings_does_not_read_credentials_or_expose_unknown_secret_fields(tmp_path, credentials):
    _, reads, writes = credentials
    write_json(tmp_path / "settings.json", {
        "base_url": "http://localhost:11434/v1", "model": "m", "api_key": "old-unsafe-secret",
    })
    result = Store(tmp_path).settings()
    assert "old-unsafe-secret" not in json.dumps(result)
    assert "api_key" not in result
    assert reads == writes == []
    assert normalize_settings(result) == result


def test_explicit_empty_key_clears_only_current_endpoint(tmp_path, credentials):
    keys, _, writes = credentials
    keys["https://api.anthropic.com/v1"] = "keep-other-key"
    keys["https://api.openai.com/v1"] = "clear-this-key"
    with connection(tmp_path) as client:
        assert client.put("/api/settings", json={"provider": "openai", "api_key": ""}).status_code == 200
        assert not client.get("/api/settings").json()["has_key"]
    assert writes == [("https://api.openai.com/v1", "")]
    assert keys["https://api.anthropic.com/v1"] == "keep-other-key"


@pytest.mark.parametrize("completion_key,embedding_key", [("chat-private", "embed-private"), ("", "keep-private")])
def test_conflicting_keys_for_same_endpoint_reject_before_any_write(
    tmp_path, credentials, completion_key, embedding_key,
):
    _, _, writes = credentials
    with connection(tmp_path) as client:
        assert client.put("/api/settings", json={"provider": "openai"}).status_code == 200
        before = (tmp_path / "settings.json").read_bytes()
        response = client.put("/api/settings", json={
            "provider": "openai", "api_key": completion_key, "embedding_api_key": embedding_key,
            "profiles": {"openai": {"base_url": "https://shared.example/v1/", "model": "chat-model"}},
            "embeddings": {"provider": "openai", "base_url": "https://shared.example/v1", "model": "embed-model"},
        })
    assert response.status_code == 400
    assert response.json()["detail"] == "Use one API key for connections that share the same API URL."
    assert "private" not in response.text
    assert (tmp_path / "settings.json").read_bytes() == before
    assert writes == []


def test_identical_keys_for_same_endpoint_are_written_once(tmp_path, credentials):
    _, _, writes = credentials
    with connection(tmp_path) as client:
        assert client.put("/api/settings", json={
            "provider": "openai", "api_key": "shared-private", "embedding_api_key": "shared-private",
            "profiles": {"openai": {"base_url": "https://shared.example/v1/", "model": "chat-model"}},
            "embeddings": {"provider": "openai", "base_url": "https://shared.example/v1", "model": "embed-model"},
        }).status_code == 200
    assert writes == [("https://shared.example/v1", "shared-private")]
