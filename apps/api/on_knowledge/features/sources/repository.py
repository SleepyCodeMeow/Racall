from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ...ingestion import EXTENSIONS, MAX_BYTES
from ...storage import ConflictError, Store, atomic_write, now, read_text, uid, write_json


def version_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("Invalid source version.")
    return value


class Sources:
    def __init__(self, store: Store):
        self.store = store

    def file(self, notebook: str, source: str, relative: str) -> Path:
        root = self.store.source_path(notebook, source).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Invalid source path.")
        return path

    def document(self, notebook: str, item: dict):
        path = self.file(notebook, item["id"], item.get("document", "document.json"))
        return json.loads(read_text(path)) if path.exists() else None

    def snapshot(self, notebook: str, item: dict):
        """Archive legacy originals before advancing the active version pointer."""
        root = self.store.source_path(notebook, item["id"])
        folder = root / "versions" / version_id(item["version"])
        folder.mkdir(parents=True, exist_ok=True)
        original = folder / ("original." + item["type"])
        data = self.file(notebook, item["id"], item["original"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["version"]:
            raise ValueError("The stored source file changed outside Racall. Reimport it as a new source.")
        if not original.exists() or hashlib.sha256(original.read_bytes()).hexdigest() != item["version"]:
            atomic_write(original, data)
        doc = self.document(notebook, item)
        if doc is not None and not (folder / "document.json").exists():
            write_json(folder / "document.json", doc)
        saved = {
            k: v for k, v in item.items() if k not in ("pending_version", "refresh_status", "refresh_error")
        }
        saved.update(
            original=original.relative_to(root).as_posix(),
            document=(folder / "document.json").relative_to(root).as_posix(),
        )
        write_json(folder / "version.json", saved)
        return saved

    def versions(self, notebook: str, source: str) -> list[dict]:
        with self.store.lock:
            current = self.store.source(notebook, source)
            items = {current["version"]: current}
            for path in (self.store.source_path(notebook, source) / "versions").glob("*/version.json"):
                item = json.loads(read_text(path))
                items.setdefault(item["version"], item)
            return sorted(
                [
                    {
                        "version": item["version"],
                        "title": item["title"],
                        "type": item["type"],
                        "size": item["size"],
                        "created_at": item.get("version_created_at", item["created_at"]),
                        "current": item["version"] == current["version"],
                    }
                    for item in items.values()
                ],
                key=lambda item: item["created_at"],
                reverse=True,
            )

    def version(self, notebook: str, source: str, version: str) -> dict:
        with self.store.lock:
            current = self.store.source(notebook, source)
            if version_id(version) == current["version"]:
                return current
            return json.loads(
                read_text(self.store.source_path(notebook, source) / "versions" / version / "version.json")
            )

    def stage(
        self, notebook: str, name: str, data: bytes, url: str | None = None, source: str | None = None
    ) -> dict:
        name = name.replace("\\", "/").split("/")[-1][:200]
        suffix = Path(name).suffix.lower()
        if suffix not in EXTENSIONS:
            raise ValueError("Поддерживаются PDF, MD, TXT и DOCX")
        if not data or len(data) > MAX_BYTES:
            raise ValueError("Файл пустой или превышает 25 МБ")
        with self.store.lock:
            root = self.store.notebook_path(notebook) / "sources"
            existing = self.store.source(notebook, source) if source else None
            if existing and (
                existing["status"] in ("queued", "processing")
                or existing.get("refresh_status") in ("queued", "processing")
            ):
                raise ConflictError("This source is already being processed. Wait before updating it.")
            digest = hashlib.sha256(data).hexdigest()
            if existing and existing["version"] == digest:
                return {**existing, "unchanged": True}
            source = source or uid()
            folder = root / source / "versions" / digest
            folder.mkdir(parents=True, exist_ok=True)
            original = folder / ("original" + suffix)
            if not original.exists() or hashlib.sha256(original.read_bytes()).hexdigest() != digest:
                # Recover an orphaned/partial stage from an interrupted prior write.
                atomic_write(original, data)
            item = {
                "id": source,
                "title": name,
                "type": suffix[1:],
                "version": digest,
                "original": original.relative_to(root / source).as_posix(),
                "document": (folder / "document.json").relative_to(root / source).as_posix(),
                "size": len(data),
                "created_at": existing["created_at"] if existing else now(),
                "version_created_at": now(),
                "status": "queued",
                "chunks": 0,
                "url": url,
            }
            if existing and existing["status"] == "ready":
                self.snapshot(notebook, existing)
                existing.update(pending_version=item, refresh_status="queued", refresh_error=None)
                self.store.save_source(notebook, existing)
                return existing
            self.store.save_source(notebook, item)
            return item
