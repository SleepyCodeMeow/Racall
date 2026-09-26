from __future__ import annotations

import json

from fastapi import APIRouter

from ...knowledge import Knowledge
from ...schemas import Question
from ...storage import Store


def create_router(store: Store, knowledge: Knowledge) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooks/{notebook}/artifacts")
    def artifacts(notebook: str):
        return store.list_notes(notebook, "artifacts")

    @router.get("/api/notebooks/{notebook}/research")
    def sessions(notebook: str):
        return sorted(
            [
                json.loads(p.read_text("utf-8"))
                for p in (store.notebook_path(notebook) / "research").glob("*.json")
            ],
            key=lambda s: s["created_at"],
            reverse=True,
        )

    @router.post("/api/notebooks/{notebook}/research")
    def research(notebook: str, body: Question):
        return knowledge.research(notebook, body.question)

    @router.post("/api/notebooks/{notebook}/research/{session}/save")
    def save_research(notebook: str, session: str):
        return knowledge.save_research(notebook, session)

    return router
