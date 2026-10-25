from __future__ import annotations

import json

from ...storage import ConflictError, Store, identifier, read_text, write_json
from ..notes.repository import validate_note_id


def empty_answer():
    return {"claims": [], "citations": [], "validated": False, "mode": "legacy", "message": ""}


class Materials:
    def __init__(self, store: Store):
        self.store = store

    def path(self, notebook: str, material: str):
        return self.store.notebook_path(notebook) / "materials" / (identifier(material) + ".json")

    def _legacy(self, notebook: str, note: dict) -> dict:
        answer = empty_answer()
        session = self.store.notebook_path(notebook) / "research" / (note["id"] + ".json")
        if session.exists():
            answer = json.loads(read_text(session)).get("answer") or answer
        return {
            "id": "legacy:" + note["id"],
            "title": note["title"],
            "kind": "research",
            "body": note["body"],
            "answer": answer,
            "legacy": True,
            "created_at": str(note["modified"]),
        }

    def get(self, notebook: str, material: str) -> dict:
        with self.store.lock:
            if material.startswith("legacy:"):
                note_id = material.removeprefix("legacy:")
                validate_note_id(note_id)
                note = next(
                    (item for item in self.store.list_notes(notebook, "artifacts") if item["id"] == note_id),
                    None,
                )
                if note is None:
                    raise FileNotFoundError("Material not found.")
                return self._legacy(notebook, note)
            return json.loads(read_text(self.path(notebook, material)))

    def list(self, notebook: str) -> list[dict]:
        with self.store.lock:
            directory = self.store.notebook_path(notebook) / "materials"
            materials = [json.loads(read_text(path)) for path in directory.glob("*.json")]
            represented = {item.get("research_id") for item in materials}
            materials.extend(
                self._legacy(notebook, note)
                for note in self.store.list_notes(notebook, "artifacts")
                if note["id"] not in represented
            )
            # Persisted JSON timestamps are ISO; legacy timestamps are numeric strings.
            # Keep the original legacy ordering while showing new materials first.
            return sorted(
                materials, key=lambda item: (not item.get("legacy", False), item["created_at"]), reverse=True
            )

    def create(self, notebook: str, material: dict) -> dict:
        with self.store.lock:
            path = self.path(notebook, material["id"])
            if path.exists():
                raise ConflictError("A material already exists for this generation.")
            write_json(path, material)
            return material

    def for_job(self, notebook: str, job: str) -> dict | None:
        with self.store.lock:
            path = self.path(notebook, job)
            return json.loads(read_text(path)) if path.exists() else None

    def copy(self, notebook: str, material: str) -> dict:
        with self.store.lock:
            item = self.get(notebook, material)
            return self.store.save_note(notebook, item["title"], item["body"])
