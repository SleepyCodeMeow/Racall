from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from on_knowledge.providers import frozen_provider_keys, provider_identity, provider_key


def profile(provider="openai", url="https://api.example.test/v1/"):
    return {"provider": provider, "base_url": url}


def test_job_credentials_survive_key_rotation_without_affecting_other_requests(monkeypatch):
    settings = profile()
    monkeypatch.setattr("on_knowledge.providers._stored_key", lambda base: "rotated-key")
    keys = {provider_identity(settings): "original-key"}
    with frozen_provider_keys(keys):
        assert provider_key(settings) == "original-key"
        keys[provider_identity(settings)] = "mutated-key"
        assert provider_key(profile(url="https://api.example.test/v1")) == "original-key"
    assert provider_key(settings) == "rotated-key"


def test_empty_key_does_not_adopt_a_later_environment_credential(monkeypatch):
    settings = profile("openai_compatible")
    with frozen_provider_keys({provider_identity(settings): ""}):
        monkeypatch.setenv("OPENNOTEBOOK_API_KEY", "new-key")
        assert provider_key(settings) == ""
    assert provider_key(settings) == "new-key"


def test_frozen_scope_never_looks_up_an_unknown_provider_or_endpoint(monkeypatch):
    def unexpected_lookup(base):
        pytest.fail("An unknown endpoint must not receive current keychain credentials")

    monkeypatch.setattr("on_knowledge.providers._stored_key", unexpected_lookup)
    with frozen_provider_keys({provider_identity(profile()): "old-key"}):
        with pytest.raises(ValueError, match="connection changed"):
            provider_key(profile(url="https://other.example.test/v1"))
        with pytest.raises(ValueError, match="connection changed"):
            provider_key(profile("anthropic"))


def test_nested_scope_restores_credentials_after_exception(monkeypatch):
    settings = profile()
    monkeypatch.setattr("on_knowledge.providers._stored_key", lambda base: "normal-key")
    with frozen_provider_keys({provider_identity(settings): "outer-key"}):
        with pytest.raises(RuntimeError):
            with frozen_provider_keys({provider_identity(settings): "inner-key"}):
                assert provider_key(settings) == "inner-key"
                raise RuntimeError("task failed")
        assert provider_key(settings) == "outer-key"
    assert provider_key(settings) == "normal-key"


def test_worker_scopes_are_isolated_from_each_other(monkeypatch):
    settings = profile()
    monkeypatch.setattr("on_knowledge.providers._stored_key", lambda base: "normal-key")
    barrier = Barrier(2)

    def run(key):
        with frozen_provider_keys({provider_identity(settings): key}):
            barrier.wait(timeout=5)
            return provider_key(settings)

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(run, key) for key in ("first-key", "second-key")]
        assert [future.result(timeout=5) for future in futures] == ["first-key", "second-key"]
    assert provider_key(settings) == "normal-key"
