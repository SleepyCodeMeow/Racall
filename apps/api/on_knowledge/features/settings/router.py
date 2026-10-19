from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ...provider_settings import EMBEDDING_PROVIDERS, PROVIDER_DEFAULTS, persistent_settings
from ...providers import save_key, validate_endpoint
from ...storage import Store, write_json


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProfileBody(StrictBody):
    base_url: str = Field(max_length=2000)
    model: str = Field(max_length=200)

    @field_validator("base_url")
    @classmethod
    def endpoint(cls, value: str) -> str:
        return validate_endpoint(value)


class LegacySettingsBody(ProfileBody):
    embedding_model: str = Field(default="", max_length=200)
    api_key: str | None = Field(default=None, max_length=4000)


class EmbeddingBody(ProfileBody):
    provider: str = Field(max_length=40)

    @field_validator("provider")
    @classmethod
    def known_provider(cls, value: str) -> str:
        if value not in EMBEDDING_PROVIDERS:
            raise ValueError("Unsupported embedding provider.")
        return value


class SettingsBody(StrictBody):
    provider: str = Field(max_length=40)
    profiles: dict[str, ProfileBody] = Field(default_factory=dict, max_length=len(PROVIDER_DEFAULTS))
    embeddings: EmbeddingBody | None = None
    api_key: str | None = Field(default=None, max_length=4000)
    embedding_api_key: str | None = Field(default=None, max_length=4000)

    @field_validator("provider")
    @classmethod
    def known_provider(cls, value: str) -> str:
        if value not in PROVIDER_DEFAULTS:
            raise ValueError("Unknown AI provider.")
        return value

    @field_validator("profiles")
    @classmethod
    def known_profiles(cls, value: dict[str, ProfileBody]) -> dict[str, ProfileBody]:
        if any(name not in PROVIDER_DEFAULTS for name in value):
            raise ValueError("Unknown AI provider profile.")
        return value


class PreferencesBody(BaseModel):
    locale: Literal["en", "ru"]


def create_router(store: Store) -> APIRouter:
    router = APIRouter()

    @router.get("/api/preferences")
    def preferences():
        path = store.root / "preferences.json"
        try:
            locale = json.loads(path.read_text("utf-8")).get("locale", "en")
        except (FileNotFoundError, ValueError, AttributeError):
            locale = "en"
        return {"locale": locale if locale in ("en", "ru") else "en"}

    @router.put("/api/preferences")
    def update_preferences(body: PreferencesBody):
        with store.lock:
            write_json(store.root / "preferences.json", {"locale": body.locale})
        return {"locale": body.locale}

    @router.get("/api/settings")
    def settings():
        from ...providers import provider_key

        s = store.settings()
        profiles = {
            name: {**config, "has_key": bool(provider_key({"provider": name, **config}))}
            for name, config in s["profiles"].items()
        }
        return {
            **s, "profiles": profiles,
            "embeddings": {**s["embeddings"], "has_key": bool(provider_key(s["embeddings"]))},
            "has_key": profiles[s["provider"]]["has_key"], "vault_path": str(store.vault),
        }

    @router.put("/api/settings")
    def update_settings(body: object = Body(...)):
        schema = SettingsBody if isinstance(body, dict) and any(
            key in body for key in ("provider", "profiles", "embeddings", "embedding_api_key")
        ) else LegacySettingsBody
        try:
            request = schema.model_validate(body)
        except ValidationError as exc:
            # Validation details must never echo API keys back in an error body.
            raise HTTPException(status_code=422, detail=[
                {"loc": ["body", *error["loc"]], "msg": error["msg"], "type": error["type"]}
                for error in exc.errors(include_url=False, include_input=False, include_context=False)
            ]) from None
        with store.lock:
            settings = persistent_settings(store.settings())
            key_updates = {}

            def queue_key(base_url: str, value: str):
                endpoint = validate_endpoint(base_url)
                if endpoint in key_updates and key_updates[endpoint] != value:
                    raise ValueError("Use one API key for connections that share the same API URL.")
                key_updates[endpoint] = value

            if isinstance(request, LegacySettingsBody):
                settings["provider"] = "openai_compatible"
                settings["profiles"]["openai_compatible"] = {
                    "base_url": request.base_url, "model": request.model,
                }
                settings["embeddings"] = {
                    "provider": "openai_compatible", "base_url": request.base_url,
                    "model": request.embedding_model,
                }
            else:
                settings["provider"] = request.provider
                settings["profiles"].update({name: profile.model_dump() for name, profile in request.profiles.items()})
                if request.embeddings is not None:
                    settings["embeddings"] = request.embeddings.model_dump()
                if request.embedding_api_key is not None:
                    queue_key(settings["embeddings"]["base_url"], request.embedding_api_key)
            if request.api_key is not None:
                queue_key(settings["profiles"][settings["provider"]]["base_url"], request.api_key)
            for endpoint, value in key_updates.items():
                save_key(endpoint, value)
            write_json(store.root / "settings.json", settings)
        return {"saved": True}

    return router
