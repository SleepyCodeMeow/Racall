from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ...storage import Store, write_json

Theme = Literal["light", "dark", "system"]


class AppearanceBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    theme: Theme


def create_router(store: Store) -> APIRouter:
    """Keep appearance independent of locale, provider credentials, and notebooks."""
    router = APIRouter()
    path = store.root / "appearance.json"

    @router.get("/api/appearance")
    def appearance():
        with store.lock:
            try:
                theme = json.loads(path.read_text("utf-8")).get("theme", "light")
            except (FileNotFoundError, ValueError, AttributeError):
                theme = "light"
        return {"theme": theme if theme in ("light", "dark", "system") else "light"}

    @router.put("/api/appearance")
    def update_appearance(body: AppearanceBody):
        with store.lock:
            write_json(path, {"theme": body.theme})
        return {"theme": body.theme}

    return router
