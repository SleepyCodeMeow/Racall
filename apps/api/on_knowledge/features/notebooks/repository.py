from __future__ import annotations

import json
import os

import yaml

from ...storage import ConflictError, Store, atomic_write, identifier, now, read_text, write_json


class Notebooks:
    def __init__(self, store: Store):
        self.store = store
        self.trash = store.root / "trash" / "notebooks"

    def rename(self, notebook: str, title: str) -> dict:
        with self.store.lock:
            path = self.store.notebook_path(notebook) / "notebook.yaml"
            item = yaml.safe_load(read_text(path))
            item.update(title=title, updated_at=now())
            atomic_write(path, yaml.safe_dump(item, allow_unicode=True))
            self.store.audit("notebook.renamed", notebook)
            return item

    def deleted(self) -> list[dict]:
        with self.store.lock:
            items = []
            for path in self.trash.glob("*/notebook.yaml"):
                item = yaml.safe_load(read_text(path))
                stamp = path.parent / "trash.json"
                item["deleted_at"] = (
                    json.loads(read_text(stamp)).get("deleted_at") if stamp.exists() else None
                )
                items.append(item)
            return sorted(items, key=lambda item: item.get("deleted_at") or "", reverse=True)

    def delete(self, notebook: str):
        notebook = identifier(notebook)
        with self.store.lock:
            path = self.store.notebook_path(notebook)
            if self.store.active_operations.get(notebook) or any(
                s.get("status") in ("queued", "processing")
                or s.get("refresh_status") in ("queued", "processing")
                for s in self.store.sources(notebook)
            ):
                raise ConflictError(
                    "Wait for this notebook's current operations to finish before moving it to trash."
                )
            destination = self.trash / notebook
            self.trash.mkdir(parents=True, exist_ok=True)
            # Both paths are derived from validated UUIDs within this knowledge directory.
            if (
                path.resolve().parent != self.store.vault.resolve()
                or destination.resolve().parent != self.trash.resolve()
            ):
                raise ValueError("Invalid notebook path.")
            if destination.exists():
                raise ConflictError("A notebook with this ID is already in trash.")
            write_json(path / "trash.json", {"deleted_at": now()})
            os.rename(path, destination)
            self.store.audit("notebook.trashed", notebook)

    def restore(self, notebook: str) -> dict:
        notebook = identifier(notebook)
        with self.store.lock:
            path, destination = self.trash / notebook, self.store.vault / notebook
            if not (path / "notebook.yaml").exists():
                raise FileNotFoundError("Notebook not found in trash.")
            if destination.exists():
                raise ConflictError("An active notebook already has this ID.")
            if (
                path.resolve().parent != self.trash.resolve()
                or destination.resolve().parent != self.store.vault.resolve()
            ):
                raise ValueError("Invalid notebook path.")
            os.rename(path, destination)
            (destination / "trash.json").unlink(missing_ok=True)
            self.store.audit("notebook.restored", notebook)
            return yaml.safe_load(read_text(destination / "notebook.yaml"))
