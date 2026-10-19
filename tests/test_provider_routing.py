"""Provider choices preserve the cited-answer contract and independent retrieval."""

import json

import pytest
from on_knowledge import providers
from on_knowledge.anthropic_provider import AnthropicProvider
from on_knowledge.knowledge import Knowledge
from on_knowledge.provider_factory import completion_provider
from on_knowledge.provider_settings import embedding_settings, normalize_settings
from on_knowledge.providers import OpenAICompatible, provider_key, validate_endpoint
from on_knowledge.storage import Store, write_json


@pytest.mark.parametrize("provider", ["openai", "ollama", "ollama_cloud", "llama_cpp", "openai_compatible"])
def test_http_provider_profiles_select_exact_endpoint_and_model(provider):
    settings = normalize_settings({})
    settings["provider"] = provider
    settings["profiles"][provider] = {"base_url": "http://127.0.0.1:9123/v1", "model": "selected-model"}
    instance = completion_provider(settings)
    assert isinstance(instance, OpenAICompatible)
    assert instance.base == "http://127.0.0.1:9123/v1"
    assert instance.settings["model"] == "selected-model"
    assert instance.settings["provider"] == provider


def test_anthropic_uses_messages_protocol_in_answer_and_research(tmp_path, monkeypatch):
    store = Store(tmp_path)
    settings = normalize_settings({})
    settings["provider"] = "anthropic"
    settings["profiles"]["anthropic"]["model"] = "chosen-claude-model"
    write_json(store.root / "settings.json", settings)
    notebook = store.create_notebook("Provider routing")["id"]
    knowledge = Knowledge(store)
    passage = {"id": "canonical-evidence", "source_id": "source", "version": "original-v1",
               "title": "Approved plan", "quote": "The launch is planned for November 22, 2030.",
               "location": {"element": 0}}
    calls = []

    def complete(self, system, data):
        assert self.settings["model"] == "chosen-claude-model"
        calls.append((system, data))
        if "supported_claim_ids" in system:
            return {"supported_claim_ids": ["C1"]}
        if "queries" in system:
            return {"queries": ["approved launch date"]}
        return {"claims": [{"text": passage["quote"], "evidence_ids": ["E1"]}]}

    monkeypatch.setattr(AnthropicProvider, "complete", complete)
    monkeypatch.setattr(OpenAICompatible, "complete", lambda *args: pytest.fail("Wrong provider"))
    monkeypatch.setattr(knowledge, "search", lambda *args: {"evidence": [passage], "mode": "keyword"})
    try:
        answer = knowledge.answer(notebook, "When is the launch planned?")
        assert answer["validated"] and answer["claims"][0]["evidence_ids"] == [passage["id"]]
        assert answer["citations"][0]["quote"] == passage["quote"]
        research = knowledge.research(notebook, "Compare the approved schedule.")
        assert research["status"] == "completed" and research["answer"]["validated"]
        assert len(calls) == 5  # Direct writer/critic, then planner/writer/critic.
    finally:
        knowledge.executor.shutdown(wait=True)


def test_retrieval_embeddings_keep_their_endpoint_when_chat_vendor_changes(tmp_path, monkeypatch):
    store = Store(tmp_path)
    settings = normalize_settings({})
    settings["provider"] = "anthropic"
    settings["profiles"]["anthropic"]["model"] = "chosen-model"
    settings["embeddings"] = {"provider": "ollama", "base_url": "http://127.0.0.1:9911/v1",
                              "model": "local-embedding"}
    write_json(store.root / "settings.json", settings)
    notebook = store.create_notebook("Separate embedding connection")["id"]
    knowledge = Knowledge(store)
    calls = []

    def embed(self, texts):
        assert self.base == "http://127.0.0.1:9911/v1"
        assert self.settings["provider"] == "ollama"
        assert self.settings["embedding_model"] == "local-embedding"
        calls.append(texts)
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(OpenAICompatible, "embed", embed)
    try:
        source = knowledge.sources.repository.stage(notebook, "plan.md", b"# Plan\n\nThe launch is planned for November 22, 2030.")
        knowledge.ingest(notebook, source["id"])
        assert store.source(notebook, source["id"])["status"] == "ready"
        assert knowledge.search(notebook, "launch")["mode"] == "hybrid"
        assert len(calls) == 2
        with store.db() as db:
            assert {row["model"] for row in db.execute("SELECT model FROM chunks")} == {
                "http://127.0.0.1:9911/v1/local-embedding"
            }
        settings["provider"] = "llama_cpp"
        write_json(store.root / "settings.json", settings)
        assert knowledge.search(notebook, "launch")["mode"] == "hybrid"
        assert len(calls) == 3
    finally:
        knowledge.executor.shutdown(wait=True)


def test_provider_environment_keys_do_not_cross_vendor_or_local_boundaries(monkeypatch):
    monkeypatch.setattr(providers.keyring, "get_password", lambda *args: None)
    for variable, value in {"OPENNOTEBOOK_API_KEY": "legacy", "OPENAI_API_KEY": "openai",
                            "ANTHROPIC_API_KEY": "claude", "OLLAMA_API_KEY": "ollama-cloud"}.items():
        monkeypatch.setenv(variable, value)
    expected = {"openai": "openai", "anthropic": "claude", "ollama_cloud": "ollama-cloud",
                "ollama": "", "llama_cpp": "", "openai_compatible": "legacy"}
    for provider, key in expected.items():
        assert provider_key({"provider": provider, "base_url": "http://127.0.0.1:9999/v1"}) == key


def test_saved_provider_key_takes_precedence_over_scoped_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    monkeypatch.setattr(providers.keyring, "get_password", lambda *args: "user-saved-key")
    assert provider_key({"provider": "openai", "base_url": "https://api.openai.com/v1"}) == "user-saved-key"


def test_legacy_trailing_slash_preserves_runtime_keychain_lookup_and_index_identity(monkeypatch):
    monkeypatch.delenv("OPENNOTEBOOK_API_KEY", raising=False)
    seen = []

    def stored(service, account):
        seen.append((service, account))
        return "legacy-saved-key" if account == "https://api.example.com/v1" else None

    monkeypatch.setattr(providers.keyring, "get_password", stored)
    settings = normalize_settings({"base_url": "https://api.example.com/v1/", "model": "answer",
                                   "embedding_model": "embedding"})
    assert provider_key(settings) == "legacy-saved-key"
    assert seen == [("OpenNotebook", "https://api.example.com/v1")]
    assert embedding_settings(settings)["base_url"] + "/embedding" == "https://api.example.com/v1//embedding"


def test_missing_cloud_key_fails_before_http_without_leaking_details(monkeypatch):
    monkeypatch.setattr(providers, "provider_key", lambda settings: "")
    monkeypatch.setattr(providers, "complete_json", lambda *args: pytest.fail("HTTP must not start"))
    instance = OpenAICompatible({"provider": "ollama_cloud", "base_url": "https://ollama.com/v1", "model": "selected"})
    with pytest.raises(ValueError, match="API-ключ"):
        instance.complete("Return JSON", {})


@pytest.mark.parametrize("url", ["https://example.com:invalid/v1", "https://example.com:99999/v1",
                                 " https://example.com/v1", "https://example.com/with space",
                                 "https://example.com/\npath", "https://[broken/v1"])
def test_provider_url_rejects_ambiguous_or_invalid_address(url):
    with pytest.raises(ValueError, match="Неверный URL API"):
        validate_endpoint(url)


def test_evaluation_snapshot_does_not_silently_turn_claude_into_openai(tmp_path):
    settings = normalize_settings({})
    settings["provider"] = "anthropic"
    settings["profiles"]["anthropic"]["model"] = "selected-claude-model"
    copied = json.loads(json.dumps({key: settings[key] for key in ("provider", "profiles", "embeddings")}))
    instance = completion_provider(copied)
    assert isinstance(instance, AnthropicProvider)
    assert embedding_settings(copied)["embedding_model"] == ""
