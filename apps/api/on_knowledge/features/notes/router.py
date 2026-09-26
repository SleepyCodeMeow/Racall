from __future__ import annotations

from fastapi import APIRouter

from ...storage import Store
from .schemas import AutosaveBody, NoteBody


def create_router(store: Store) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooks/{notebook}/notes")
    def notes(notebook: str):
        return store.list_notes(notebook)

    @router.post("/api/notebooks/{notebook}/notes")
    def save_note(notebook: str, body: NoteBody):
        return store.save_note(notebook, body.title, body.body, body.id, revision=body.revision)

    @router.post("/api/notebooks/{notebook}/notes/autosave")
    def autosave_note(notebook: str, body: AutosaveBody):
        if not body.title.strip():
            raise ValueError("A note title is required.")
        return store.autosave_note(notebook, body.draft_id, body.model_dump(exclude={"draft_id"}))

    @router.get("/api/notebooks/{notebook}/drafts")
    def drafts(notebook: str):
        return store.drafts(notebook)

    @router.delete("/api/notebooks/{notebook}/drafts/{draft_id}")
    def discard_draft(notebook: str, draft_id: str):
        store.discard_draft(notebook, draft_id)
        return {"deleted": True}

    return router
