"""Provider profiles and a separate, stable embedding configuration.

Reading old settings is intentionally an in-memory projection: opening Racall must
not silently rewrite a user's endpoint or change the embedding index identity.
"""

from __future__ import annotations

from copy import deepcopy

PROVIDER_DEFAULTS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "ollama": "http://127.0.0.1:11434/v1",
    "ollama_cloud": "https://ollama.com/v1",
    "llama_cpp": "http://127.0.0.1:8080/v1",
    "openai_compatible": "https://api.openai.com/v1",
}
EMBEDDING_PROVIDERS = frozenset({"openai", "ollama", "llama_cpp", "openai_compatible"})


def default_profiles() -> dict[str, dict[str, str]]:
    return {provider: {"base_url": url, "model": ""} for provider, url in PROVIDER_DEFAULTS.items()}


def _profile(value: object, fallback: dict[str, str]) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("Invalid stored provider profile.")
    result = {key: value.get(key, fallback[key]) for key in ("base_url", "model")}
    if any(not isinstance(item, str) for item in result.values()):
        raise ValueError("Invalid stored provider profile.")
    return result


def normalize_settings(raw: dict | None = None) -> dict:
    """Return safe settings plus the legacy flat fields used by old callers."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("Invalid stored AI settings.")
    profiles = default_profiles()
    legacy = bool(raw) and "provider" not in raw
    provider = "openai_compatible" if legacy else raw.get("provider", "openai")
    if not isinstance(provider, str) or provider not in profiles:
        raise ValueError("Unknown AI provider.")
    stored_profiles = raw.get("profiles", {})
    if not isinstance(stored_profiles, dict):
        raise ValueError("Invalid stored provider profiles.")
    for name, config in stored_profiles.items():
        if name not in profiles:
            raise ValueError("Unknown stored AI provider.")
        profiles[name] = _profile(config, profiles[name])
    if legacy:
        profiles[provider] = _profile(raw, profiles[provider])

    if "embeddings" in raw:
        config = raw["embeddings"]
        if not isinstance(config, dict):
            raise ValueError("Invalid stored embedding settings.")
        embedding_provider = config.get("provider", "openai")
        if not isinstance(embedding_provider, str) or embedding_provider not in EMBEDDING_PROVIDERS:
            raise ValueError("Unknown embedding provider.")
        embedding_profile = _profile(
            config,
            {
                "base_url": PROVIDER_DEFAULTS[embedding_provider],
                "model": "",
            },
        )
        embeddings = {"provider": embedding_provider, **embedding_profile}
    elif legacy:
        embedding_model = raw.get("embedding_model", "")
        if not isinstance(embedding_model, str):
            raise ValueError("Invalid stored embedding model.")
        embeddings = {
            "provider": "openai_compatible",
            "base_url": raw.get("embedding_base_url", profiles[provider]["base_url"]),
            "model": embedding_model,
        }
        if not isinstance(embeddings["base_url"], str):
            raise ValueError("Invalid stored embedding endpoint.")
    else:
        embeddings = {"provider": "openai", "base_url": PROVIDER_DEFAULTS["openai"], "model": ""}

    return {
        "provider": provider,
        "profiles": profiles,
        "embeddings": embeddings,
        **profiles[provider],
        "embedding_model": embeddings["model"],
        "embedding_base_url": embeddings["base_url"],
    }


def persistent_settings(settings: dict) -> dict:
    """Keep one source of truth on disk, without flat projections or secrets."""
    normalized = normalize_settings(settings)
    return deepcopy({key: normalized[key] for key in ("provider", "profiles", "embeddings")})


def embedding_settings(settings: dict) -> dict:
    """Adapt independent embeddings for the existing embedding provider interface."""
    config = normalize_settings(settings)["embeddings"]
    return {
        "provider": config["provider"],
        "base_url": config["base_url"],
        "model": "",
        "embedding_model": config["model"],
    }
