from __future__ import annotations

import json

from ...storage import Store, now, read_text, write_json


def recover_research(store: Store):
    """Close unfinished sessions at startup without repeating provider requests."""
    with store.lock:
        for notebook in store.notebooks():
            directory = store.notebook_path(notebook["id"]) / "research"
            for path in directory.glob("*.json"):
                session = json.loads(read_text(path))
                if session.get("status") == "running":
                    session.update(status="interrupted", finished_at=now())
                    write_json(path, session)
