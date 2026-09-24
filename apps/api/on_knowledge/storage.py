from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import yaml


def now() -> str:
    return datetime.now(UTC).isoformat()


def uid() -> str:
    return str(uuid.uuid4())


def identifier(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise ValueError("Некорректный идентификатор") from None


def write_json(path: Path, value: object):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2))


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uid() + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    try:
        for attempt in range(8):
            try:
                os.replace(temporary, path)
                break
            except PermissionError as exc:
                # Windows readers and antivirus scanners can briefly hold the target.
                # Retry only Windows sharing/access conflicts, never arbitrary errors.
                if getattr(exc, "winerror", None) not in (5, 32, 33) or attempt == 7:
                    raise
                time.sleep(0.01 * 2**attempt)
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


class Store:
    """Portable files are authoritative. SQLite is a disposable retrieval cache."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.vault = self.root / "notebooks"
        self.vault.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db_path = self.root / "index.sqlite3"
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
                INSERT OR IGNORE INTO schema_version VALUES(1);
                CREATE TABLE IF NOT EXISTS chunks(
                    id TEXT PRIMARY KEY, notebook TEXT NOT NULL, source TEXT NOT NULL,
                    version TEXT NOT NULL, text TEXT NOT NULL, location TEXT NOT NULL,
                    embedding TEXT, model TEXT
                );
                CREATE INDEX IF NOT EXISTS chunks_notebook ON chunks(notebook);
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(id UNINDEXED, text);
            ''')

    @contextmanager
    def db(self):
        with self.lock:
            db = sqlite3.connect(self.db_path, timeout=30)
            db.row_factory = sqlite3.Row
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

    def notebook_path(self, notebook: str) -> Path:
        path = self.vault / identifier(notebook)
        if not (path / "notebook.yaml").exists():
            raise FileNotFoundError("Блокнот не найден")
        return path

    def notebooks(self) -> list[dict]:
        result = []
        for path in self.vault.glob("*/notebook.yaml"):
            data = yaml.safe_load(path.read_text("utf-8"))
            data["sources_count"] = len(list((path.parent / "sources").glob("*/source.json")))
            result.append(data)
        return sorted(result, key=lambda n: n["created_at"])

    def create_notebook(self, title: str) -> dict:
        data = {"id": uid(), "title": title, "created_at": now()}
        path = self.vault / data["id"]
        for folder in ("sources", "notes", "research", "artifacts", "attachments", "memory"):
            (path / folder).mkdir(parents=True)
        atomic_write(path / "notebook.yaml", yaml.safe_dump(data, allow_unicode=True))
        self.audit("notebook.created", data["id"])
        return data

    def source_path(self, notebook: str, source: str) -> Path:
        path = self.notebook_path(notebook) / "sources" / identifier(source)
        if not (path / "source.json").exists():
            raise FileNotFoundError("Источник не найден")
        return path

    def sources(self, notebook: str) -> list[dict]:
        return sorted(
            [json.loads(p.read_text("utf-8")) for p in
             (self.notebook_path(notebook) / "sources").glob("*/source.json")],
            key=lambda s: s["created_at"], reverse=True,
        )

    def source(self, notebook: str, source: str) -> dict:
        return json.loads((self.source_path(notebook, source) / "source.json").read_text("utf-8"))

    def save_source(self, notebook: str, source: dict):
        path = self.notebook_path(notebook) / "sources" / identifier(source["id"])
        write_json(path / "source.json", source)

    def replace_chunks(self, notebook: str, source: str, version: str, chunks: list[dict]):
        with self.db() as db:
            db.execute("DELETE FROM chunks_fts WHERE id IN (SELECT id FROM chunks WHERE source=?)", (source,))
            db.execute("DELETE FROM chunks WHERE source=?", (source,))
            for c in chunks:
                db.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)", (
                    c["id"], notebook, source, version, c["text"], json.dumps(c["location"]),
                    json.dumps(c.get("embedding")), c.get("model"),
                ))
                db.execute("INSERT INTO chunks_fts VALUES(?,?)", (c["id"], c["text"]))

    def list_notes(self, notebook: str, kind: str = "notes") -> list[dict]:
        if kind not in ("notes", "artifacts"):
            raise ValueError("Неизвестный тип записи")
        notes = []
        for path in (self.notebook_path(notebook) / kind).glob("*.md"):
            text = path.read_text("utf-8")
            frontmatter = {}
            body = text
            if text.startswith("---\n"):
                parts = text.split("---\n", 2)
                if len(parts) == 3:
                    try:
                        parsed = yaml.safe_load(parts[1])
                        frontmatter = parsed if isinstance(parsed, dict) else {}
                    except yaml.YAMLError:
                        frontmatter = {}
                    body = parts[2].lstrip("\n")
            notes.append({"id": path.stem, "title": str(frontmatter.get("title", path.stem)),
                          "body": body, "modified": path.stat().st_mtime})
        return sorted(notes, key=lambda n: n["modified"], reverse=True)

    def save_note(self, notebook: str, title: str, body: str, note_id: str | None = None,
                  kind: str = "notes") -> dict:
        if kind not in ("notes", "artifacts"):
            raise ValueError("Неизвестный тип записи")
        if not note_id:
            stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title).strip(" .")[:120]
            reserved = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
            if not stem or stem.upper() in reserved:
                stem = "note-" + uid()[:8]
            note_id = stem
            if (self.notebook_path(notebook) / kind / f"{note_id}.md").exists():
                note_id += "-" + uid()[:8]
        # Existing user-created filenames are allowed, but never separators or traversal.
        if not re.fullmatch(r"[^/\\:.\x00-\x1f][^/\\:\x00-\x1f]{0,180}", note_id) or ".." in note_id:
            raise ValueError("Недопустимое имя заметки")
        path = self.notebook_path(notebook) / kind / f"{note_id}.md"
        metadata = {}
        if path.exists():
            previous = path.read_text("utf-8")
            if previous.startswith("---\n"):
                parts = previous.split("---\n", 2)
                if len(parts) == 3:
                    try:
                        parsed = yaml.safe_load(parts[1])
                        metadata = parsed if isinstance(parsed, dict) else {}
                    except yaml.YAMLError:
                        pass
        aliases = metadata.get("aliases", [])
        aliases = aliases if isinstance(aliases, list) else [str(aliases)]
        metadata.update(title=title, id=note_id, aliases=list(dict.fromkeys([*map(str, aliases), title])))
        atomic_write(path, "---\n" + yaml.safe_dump(metadata, allow_unicode=True)
                     + "---\n\n" + body)
        self.audit("note.saved", notebook, {"id": note_id, "kind": kind})
        return {"id": note_id, "title": title, "body": body}

    def settings(self) -> dict:
        path = self.root / "settings.json"
        return json.loads(path.read_text("utf-8")) if path.exists() else {
            "base_url": "https://api.openai.com/v1", "model": "", "embedding_model": "",
        }

    def audit(self, event: str, notebook: str = "", detail: dict | None = None):
        with self.lock, (self.root / "audit.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), "event": event, "notebook": notebook,
                                "detail": detail or {}}, ensure_ascii=False) + "\n")
