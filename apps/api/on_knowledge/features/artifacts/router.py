from fastapi import APIRouter
from fastapi.responses import Response

from .repository import Materials


def create_router(materials: Materials) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooks/{notebook}/materials")
    def material_list(notebook: str):
        return materials.list(notebook)

    @router.get("/api/notebooks/{notebook}/materials/{material}")
    def material_get(notebook: str, material: str):
        return materials.get(notebook, material)

    @router.post("/api/notebooks/{notebook}/materials/{material}/copy", status_code=201)
    def material_copy(notebook: str, material: str):
        return materials.copy(notebook, material)

    @router.get("/api/notebooks/{notebook}/materials/{material}/export")
    def material_export(notebook: str, material: str):
        item = materials.get(notebook, material)
        return Response(item["body"], media_type="text/markdown",
                        headers={"Content-Disposition": 'attachment; filename="racall-material.md"'})

    return router
