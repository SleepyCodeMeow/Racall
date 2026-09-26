from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter

from ...storage import Store


def create_router(store: Store) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooks/{notebook}/connection")
    def connection(notebook: str):
        store.notebook_path(notebook)
        command = sys.executable
        args = [] if getattr(sys, "frozen", False) else [str(Path(__file__).resolve().parents[3] / "run.py")]
        args += ["--mcp", "--data-dir", str(store.root), "--notebook", notebook]
        return {
            "mcpServers": {"open-notebook": {"command": command, "args": args}},
            "scope": "read-only",
            "notebook": notebook,
        }

    return router
