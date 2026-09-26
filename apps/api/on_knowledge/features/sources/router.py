from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...ingestion import MAX_BYTES
from ...knowledge import Knowledge
from ...storage import Store
from .parser import fetch_url_isolated as fetch_url


class URLBody(BaseModel):
    url: str = Field(min_length=1, max_length=4000)


def create_router(store: Store, knowledge: Knowledge) -> APIRouter:
    router = APIRouter()
    service = knowledge.sources
    repository = service.repository

    @router.get("/api/notebooks/{notebook}/sources")
    def sources(notebook: str):
        return store.sources(notebook)

    async def read_upload(file: UploadFile):
        try:
            return file.filename or "document.txt", await file.read(MAX_BYTES + 1)
        finally:
            await file.close()

    def stage(notebook, name, data, url=None, source=None):
        item = repository.stage(notebook, name, data, url, source)
        if not item.get("unchanged"):
            service.submit(notebook, item["id"])
        return item

    @router.post("/api/notebooks/{notebook}/sources", status_code=202)
    async def upload(notebook: str, file: UploadFile = File(...)):
        with store.notebook_operation(notebook):
            name, data = await read_upload(file)
            return stage(notebook, name, data)

    @router.post("/api/notebooks/{notebook}/urls", status_code=202)
    def add_url(notebook: str, body: URLBody):
        with store.notebook_operation(notebook):
            title, text = fetch_url(body.url)
            return stage(notebook, title[:150] + ".md", text.encode("utf-8"), body.url)

    @router.put("/api/notebooks/{notebook}/sources/{source}", status_code=202)
    async def update_file(notebook: str, source: str, file: UploadFile = File(...)):
        with store.notebook_operation(notebook):
            store.source(notebook, source)
            name, data = await read_upload(file)
            return stage(notebook, name, data, source=source)

    @router.post("/api/notebooks/{notebook}/sources/{source}/refresh", status_code=202)
    def refresh_url(notebook: str, source: str):
        with store.notebook_operation(notebook):
            current = store.source(notebook, source)
            if not current.get("url"):
                raise ValueError("Choose a replacement file to update this source.")
            title, text = fetch_url(current["url"])
            return stage(notebook, title[:150] + ".md", text.encode("utf-8"), current["url"], source)

    @router.get("/api/notebooks/{notebook}/sources/{source}")
    def read_source(notebook: str, source: str):
        with store.lock:
            item = store.source(notebook, source)
            return {"source": item, "document": repository.document(notebook, item)}

    @router.get("/api/notebooks/{notebook}/sources/{source}/original")
    def original(notebook: str, source: str):
        item = store.source(notebook, source)
        return FileResponse(repository.file(notebook, source, item["original"]), filename=item["title"])

    @router.get("/api/notebooks/{notebook}/sources/{source}/versions")
    def versions(notebook: str, source: str):
        return repository.versions(notebook, source)

    @router.get("/api/notebooks/{notebook}/sources/{source}/versions/{version}")
    def version(notebook: str, source: str, version: str):
        item = repository.version(notebook, source, version)
        return {"source": item, "document": repository.document(notebook, item)}

    @router.get("/api/notebooks/{notebook}/sources/{source}/versions/{version}/original")
    def version_original(notebook: str, source: str, version: str):
        item = repository.version(notebook, source, version)
        return FileResponse(repository.file(notebook, source, item["original"]), filename=item["title"])

    @router.post("/api/notebooks/{notebook}/reindex", status_code=202)
    def reindex(notebook: str):
        with store.notebook_operation(notebook):
            items = store.sources(notebook)
            count = 0
            for item in items:
                if item["id"] not in service.pending:
                    service.retry(notebook, item["id"])
                    count += 1
            return {"queued": count}

    @router.post("/api/notebooks/{notebook}/sources/{source}/reindex", status_code=202)
    def reindex_source(notebook: str, source: str):
        return service.retry(notebook, source)

    return router
