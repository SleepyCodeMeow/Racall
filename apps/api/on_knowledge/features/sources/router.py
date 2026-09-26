from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...ingestion import EXTENSIONS, MAX_BYTES, fetch_url
from ...knowledge import Knowledge
from ...storage import Store, now, uid


class URLBody(BaseModel):
    url: str = Field(min_length=1, max_length=4000)


def create_router(store: Store, knowledge: Knowledge) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooks/{notebook}/sources")
    def sources(notebook: str):
        return store.sources(notebook)

    def add_source(notebook: str, name: str, data: bytes, url: str | None = None):
        source_id = uid()
        suffix = Path(name).suffix.lower()
        if suffix not in EXTENSIONS:
            raise ValueError("Поддерживаются PDF, MD, TXT и DOCX")
        if not data or len(data) > MAX_BYTES:
            raise ValueError("Файл пустой или превышает 25 МБ")
        source = {
            "id": source_id,
            "title": name[:200],
            "type": suffix[1:],
            "original": "original" + suffix,
            "version": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "created_at": now(),
            "status": "queued",
            "chunks": 0,
            "url": url,
        }
        path = store.notebook_path(notebook) / "sources" / source_id
        path.mkdir()
        (path / source["original"]).write_bytes(data)
        store.save_source(notebook, source)
        knowledge.submit(notebook, source_id)
        return source

    @router.post("/api/notebooks/{notebook}/sources", status_code=202)
    async def upload(notebook: str, file: UploadFile = File(...)):
        store.notebook_path(notebook)
        data = await file.read(MAX_BYTES + 1)
        await file.close()
        return add_source(notebook, (file.filename or "document.txt").replace("\\", "/").split("/")[-1], data)

    @router.post("/api/notebooks/{notebook}/urls", status_code=202)
    def add_url(notebook: str, body: URLBody):
        store.notebook_path(notebook)
        title, text = fetch_url(body.url)
        return add_source(notebook, title[:150] + ".md", text.encode("utf-8"), body.url)

    @router.get("/api/notebooks/{notebook}/sources/{source}")
    def read_source(notebook: str, source: str):
        path = store.source_path(notebook, source)
        document = path / "document.json"
        return {
            "source": store.source(notebook, source),
            "document": json.loads(document.read_text("utf-8")) if document.exists() else None,
        }

    @router.get("/api/notebooks/{notebook}/sources/{source}/original")
    def original(notebook: str, source: str):
        item = store.source(notebook, source)
        return FileResponse(store.source_path(notebook, source) / item["original"], filename=item["title"])

    @router.post("/api/notebooks/{notebook}/reindex", status_code=202)
    def reindex(notebook: str):
        sources = store.sources(notebook)
        for source in sources:
            source.update(status="queued", error=None)
            store.save_source(notebook, source)
            knowledge.submit(notebook, source["id"])
        return {"queued": len(sources)}

    @router.post("/api/notebooks/{notebook}/sources/{source}/reindex", status_code=202)
    def reindex_source(notebook: str, source: str):
        item = store.source(notebook, source)
        item.update(status="queued", error=None)
        store.save_source(notebook, item)
        knowledge.submit(notebook, source)
        return item

    return router
