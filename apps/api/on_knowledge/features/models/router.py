from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from .service import Models


class DownloadBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    model: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")


def create_router(service: Models) -> APIRouter:
    router = APIRouter()

    @router.get("/api/models")
    async def models(provider: str | None = None):
        return await service.catalog(provider)

    @router.get("/api/models/downloads")
    async def downloads():
        return {"job": service.current()}

    @router.post("/api/models/downloads", status_code=202)
    async def download(body: DownloadBody):
        return await service.download(body.model)

    @router.get("/api/models/downloads/{job_id}")
    async def download_status(job_id: str):
        return service.get(job_id)

    @router.delete("/api/models/downloads/{job_id}")
    async def cancel_download(job_id: str):
        return await service.cancel(job_id)

    return router
