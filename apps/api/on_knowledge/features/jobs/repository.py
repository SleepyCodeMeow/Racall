from __future__ import annotations

import json

from ...storage import Store, identifier, read_text, write_json

TERMINAL = frozenset({"completed", "failed", "cancelled", "interrupted"})


class JobRepository:
    """Authoritative portable files, never the rebuildable retrieval index."""

    def __init__(self, store: Store):
        self.store = store

    def path(self, notebook: str, job: str):
        return self.store.notebook_path(notebook) / "jobs" / (identifier(job) + ".json")

    def get(self, notebook: str, job: str) -> dict:
        with self.store.lock:
            return json.loads(read_text(self.path(notebook, job)))

    def save(self, notebook: str, job: dict):
        with self.store.lock:
            write_json(self.path(notebook, job["id"]), job)

    def list(self, notebook: str) -> list[dict]:
        with self.store.lock:
            directory = self.store.notebook_path(notebook) / "jobs"
            return sorted(
                [json.loads(read_text(path)) for path in directory.glob("*.json")],
                key=lambda job: job["created_at"],
                reverse=True,
            )

    @staticmethod
    def public(job: dict) -> dict:
        return {key: value for key, value in job.items() if not key.startswith("_")}
