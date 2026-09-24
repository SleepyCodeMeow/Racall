from __future__ import annotations

import hashlib
import hmac
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ingestion import EXTENSIONS, MAX_BYTES, fetch_url
from .knowledge import Knowledge
from .providers import get_key, save_key, validate_endpoint
from .storage import Store, now, uid, write_json
from .version import VERSION


class Title(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class NoteBody(Title):
    body: str = Field(default="", max_length=1_000_000)
    id: str | None = None


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class URLBody(BaseModel):
    url: str = Field(min_length=1, max_length=4000)


class SettingsBody(BaseModel):
    base_url: str = Field(max_length=2000)
    model: str = Field(max_length=200)
    embedding_model: str = Field(default="", max_length=200)
    api_key: str | None = Field(default=None, max_length=4000)


class PreferencesBody(BaseModel):
    locale: Literal["en", "ru"]


def create_app(root: Path, token: str, web: Path | None = None) -> FastAPI:
    store = Store(root)
    knowledge = Knowledge(store)

    @asynccontextmanager
    async def lifespan(app):
        knowledge.recover()
        yield
        knowledge.executor.shutdown(wait=True)

    app = FastAPI(title="Racall", version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store, app.state.knowledge = store, knowledge
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.method != "OPTIONS" and (request.url.path.startswith("/api/") or request.url.path == "/openapi.json"):
            authorization = request.headers.get("authorization", "")
            if not hmac.compare_digest(authorization, "Bearer " + token):
                return JSONResponse({"detail": "Требуется авторизация настольного приложения"}, status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Запись или файл не найден"}, status_code=404)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": VERSION}

    @app.get("/api/notebooks")
    def notebooks():
        return store.notebooks()

    @app.post("/api/notebooks", status_code=201)
    def create_notebook(body: Title):
        if not body.title.strip():
            raise ValueError("Введите название блокнота")
        return store.create_notebook(body.title.strip())

    @app.get("/api/notebooks/{notebook}/sources")
    def sources(notebook: str):
        return store.sources(notebook)

    def add_source(notebook: str, name: str, data: bytes, url: str | None = None):
        source_id = uid()
        suffix = Path(name).suffix.lower()
        if suffix not in EXTENSIONS:
            raise ValueError("Поддерживаются PDF, MD, TXT и DOCX")
        if not data or len(data) > MAX_BYTES:
            raise ValueError("Файл пустой или превышает 25 МБ")
        source = {"id": source_id, "title": name[:200], "type": suffix[1:], "original": "original" + suffix,
                  "version": hashlib.sha256(data).hexdigest(), "size": len(data), "created_at": now(),
                  "status": "queued", "chunks": 0, "url": url}
        path = store.notebook_path(notebook) / "sources" / source_id
        path.mkdir()
        (path / source["original"]).write_bytes(data)
        store.save_source(notebook, source)
        knowledge.submit(notebook, source_id)
        return source

    @app.post("/api/notebooks/{notebook}/sources", status_code=202)
    async def upload(notebook: str, file: UploadFile = File(...)):
        store.notebook_path(notebook)
        data = await file.read(MAX_BYTES + 1)
        await file.close()
        return add_source(notebook, (file.filename or "document.txt").replace("\\", "/").split("/")[-1], data)

    @app.post("/api/notebooks/{notebook}/urls", status_code=202)
    def add_url(notebook: str, body: URLBody):
        store.notebook_path(notebook)
        title, text = fetch_url(body.url)
        return add_source(notebook, title[:150] + ".md", text.encode("utf-8"), body.url)

    @app.get("/api/notebooks/{notebook}/sources/{source}")
    def read_source(notebook: str, source: str):
        path = store.source_path(notebook, source)
        document = path / "document.json"
        return {"source": store.source(notebook, source),
                "document": json.loads(document.read_text("utf-8")) if document.exists() else None}

    @app.get("/api/notebooks/{notebook}/sources/{source}/original")
    def original(notebook: str, source: str):
        item = store.source(notebook, source)
        return FileResponse(store.source_path(notebook, source) / item["original"], filename=item["title"])

    @app.post("/api/notebooks/{notebook}/reindex", status_code=202)
    def reindex(notebook: str):
        sources = store.sources(notebook)
        for source in sources:
            source.update(status="queued", error=None)
            store.save_source(notebook, source)
            knowledge.submit(notebook, source["id"])
        return {"queued": len(sources)}

    @app.post("/api/notebooks/{notebook}/sources/{source}/reindex", status_code=202)
    def reindex_source(notebook: str, source: str):
        item = store.source(notebook, source)
        item.update(status="queued", error=None)
        store.save_source(notebook, item)
        knowledge.submit(notebook, source)
        return item

    @app.post("/api/notebooks/{notebook}/search")
    def search(notebook: str, body: Question):
        return knowledge.search(notebook, body.question)

    @app.post("/api/notebooks/{notebook}/ask")
    def ask(notebook: str, body: Question):
        return knowledge.answer(notebook, body.question)

    @app.get("/api/notebooks/{notebook}/notes")
    def notes(notebook: str):
        return store.list_notes(notebook)

    @app.post("/api/notebooks/{notebook}/notes")
    def save_note(notebook: str, body: NoteBody):
        return store.save_note(notebook, body.title, body.body, body.id)

    @app.get("/api/notebooks/{notebook}/artifacts")
    def artifacts(notebook: str):
        return store.list_notes(notebook, "artifacts")

    @app.get("/api/notebooks/{notebook}/research")
    def sessions(notebook: str):
        return sorted([json.loads(p.read_text("utf-8")) for p in
                       (store.notebook_path(notebook) / "research").glob("*.json")],
                      key=lambda s: s["created_at"], reverse=True)

    @app.post("/api/notebooks/{notebook}/research")
    def research(notebook: str, body: Question):
        return knowledge.research(notebook, body.question)

    @app.post("/api/notebooks/{notebook}/research/{session}/save")
    def save_research(notebook: str, session: str):
        return knowledge.save_research(notebook, session)

    @app.get("/api/preferences")
    def preferences():
        path = store.root / "preferences.json"
        try:
            locale = json.loads(path.read_text("utf-8")).get("locale", "en")
        except (FileNotFoundError, ValueError, AttributeError):
            locale = "en"
        return {"locale": locale if locale in ("en", "ru") else "en"}

    @app.put("/api/preferences")
    def update_preferences(body: PreferencesBody):
        with store.lock:
            write_json(store.root / "preferences.json", {"locale": body.locale})
        return {"locale": body.locale}

    @app.get("/api/settings")
    def settings():
        s = store.settings()
        return {**s, "has_key": bool(get_key(s["base_url"])), "vault_path": str(store.vault)}

    @app.put("/api/settings")
    def update_settings(body: SettingsBody):
        settings = body.model_dump(exclude={"api_key"})
        settings["base_url"] = validate_endpoint(body.base_url)
        if body.api_key is not None:
            save_key(settings["base_url"], body.api_key)
        write_json(store.root / "settings.json", settings)
        return {"saved": True}

    @app.get("/api/notebooks/{notebook}/connection")
    def connection(notebook: str):
        store.notebook_path(notebook)
        command = sys.executable
        args = [] if getattr(sys, "frozen", False) else [str(Path(__file__).parent.parent / "run.py")]
        args += ["--mcp", "--data-dir", str(store.root), "--notebook", notebook]
        return {"mcpServers": {"open-notebook": {"command": command, "args": args}},
                "scope": "read-only", "notebook": notebook}

    if web and web.exists():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app
