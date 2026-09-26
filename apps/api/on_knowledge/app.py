from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .features.chats import router as chats
from .features.chats.service import Chats
from .features.connections import router as connections
from .features.notebooks import router as notebooks
from .features.notes import router as notes
from .features.research import router as research
from .features.settings import router as settings
from .features.sources import router as sources
from .knowledge import Knowledge
from .storage import ConflictError, Store
from .version import VERSION


def create_app(root: Path, token: str, web: Path | None = None) -> FastAPI:
    store = Store(root)
    knowledge = Knowledge(store)
    chat_service = Chats(store)

    @asynccontextmanager
    async def lifespan(app):
        chat_service.recover()
        knowledge.recover()
        yield
        knowledge.executor.shutdown(wait=True)

    app = FastAPI(title="Racall", version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store, app.state.knowledge = store, knowledge
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.method != "OPTIONS" and (
            request.url.path.startswith("/api/") or request.url.path == "/openapi.json"
        ):
            authorization = request.headers.get("authorization", "")
            if not hmac.compare_digest(authorization, "Bearer " + token):
                return JSONResponse(
                    {"detail": "Требуется авторизация настольного приложения"}, status_code=401
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ConflictError)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Запись или файл не найден"}, status_code=404)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": VERSION}

    for router in (
        notebooks.create_router(store, knowledge),
        sources.create_router(store, knowledge),
        chats.create_router(chat_service, knowledge),
        notes.create_router(store),
        research.create_router(store, knowledge),
        settings.create_router(store),
        connections.create_router(store),
    ):
        app.include_router(router)

    if web and web.exists():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app
