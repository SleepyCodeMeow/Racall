from fastapi import APIRouter

from ...schemas import Title
from ...storage import Store
from .repository import Notebooks


def create_router(store: Store, knowledge) -> APIRouter:
    router = APIRouter()
    notebooks = Notebooks(store)

    @router.get("/api/notebooks")
    def list_notebooks():
        return store.notebooks()

    @router.post("/api/notebooks", status_code=201)
    def create_notebook(body: Title):
        return store.create_notebook(body.title.strip())

    @router.get("/api/notebooks/trash")
    def list_trash():
        return notebooks.deleted()

    @router.put("/api/notebooks/{notebook}")
    def rename_notebook(notebook: str, body: Title):
        return notebooks.rename(notebook, body.title.strip())

    @router.delete("/api/notebooks/{notebook}")
    def delete_notebook(notebook: str):
        notebooks.delete(notebook)
        return {"deleted": True}

    @router.post("/api/notebooks/{notebook}/restore")
    def restore_notebook(notebook: str):
        restored = notebooks.restore(notebook)
        knowledge.recover()
        return restored

    return router
