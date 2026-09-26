from __future__ import annotations

from fastapi import APIRouter

from ...schemas import Title
from ...storage import Store


def create_router(store: Store) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooks")
    def notebooks():
        return store.notebooks()

    @router.post("/api/notebooks", status_code=201)
    def create_notebook(body: Title):
        if not body.title.strip():
            raise ValueError("Введите название блокнота")
        return store.create_notebook(body.title.strip())

    return router
