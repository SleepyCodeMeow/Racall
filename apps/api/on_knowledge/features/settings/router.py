from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...providers import get_key, save_key, validate_endpoint
from ...storage import Store, write_json


class SettingsBody(BaseModel):
    base_url: str = Field(max_length=2000)
    model: str = Field(max_length=200)
    embedding_model: str = Field(default="", max_length=200)
    api_key: str | None = Field(default=None, max_length=4000)


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
        s = store.settings()
        return {**s, "has_key": bool(get_key(s["base_url"])), "vault_path": str(store.vault)}

    @router.put("/api/settings")
    def update_settings(body: SettingsBody):
        settings = body.model_dump(exclude={"api_key"})
        settings["base_url"] = validate_endpoint(body.base_url)
        if body.api_key is not None:
            save_key(settings["base_url"], body.api_key)
        write_json(store.root / "settings.json", settings)
        return {"saved": True}

    return router
