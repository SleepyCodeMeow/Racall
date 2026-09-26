from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING

import yaml

from ...storage import ConflictError, atomic_write, identifier, now, read_text, uid, write_json

if TYPE_CHECKING:
    from ...storage import Store


def validate_note_id(note_id: str):
    # Existing user-created filenames are allowed, but never separators or traversal.
    if not re.fullmatch(r"[^/\\:.\x00-\x1f][^/\\:\x00-\x1f]{0,180}", note_id) or ".." in note_id:
        raise ValueError("Недопустимое имя заметки")


class NoteRepository:
    def __init__(self, store: Store):
        self.store = store

    def list_notes(self, notebook: str, kind: str = "notes") -> list[dict]:
        if kind not in ("notes", "artifacts"):
            raise ValueError("Неизвестный тип записи")
        notes = []
        for path in (self.store.notebook_path(notebook) / kind).glob("*.md"):
            text = read_text(path)
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
            notes.append(
                {
                    "id": path.stem,
                    "title": str(frontmatter.get("title", path.stem)),
                    "body": body,
                    "modified": path.stat().st_mtime,
                    "revision": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                }
            )
        return sorted(notes, key=lambda n: n["modified"], reverse=True)

    def save_note(
        self,
        notebook: str,
        title: str,
        body: str,
        note_id: str | None = None,
        kind: str = "notes",
        revision: str | None = None,
    ) -> dict:
        with self.store.lock:
            return self._save_note(notebook, title, body, note_id, kind, revision)

    def _save_note(self, notebook, title, body, note_id, kind, revision):
        if kind not in ("notes", "artifacts"):
            raise ValueError("Неизвестный тип записи")
        if not note_id:
            stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title).strip(" .")[:120]
            reserved = (
                {"CON", "PRN", "AUX", "NUL"}
                | {f"COM{i}" for i in range(1, 10)}
                | {f"LPT{i}" for i in range(1, 10)}
            )
            if not stem or stem.upper() in reserved:
                stem = "note-" + uid()[:8]
            note_id = stem
            if (self.store.notebook_path(notebook) / kind / f"{note_id}.md").exists():
                note_id += "-" + uid()[:8]
        validate_note_id(note_id)
        path = self.store.notebook_path(notebook) / kind / f"{note_id}.md"
        previous = read_text(path) if path.exists() else None
        actual = hashlib.sha256(previous.encode("utf-8")).hexdigest() if previous is not None else ""
        if revision is not None and revision != actual:
            raise ConflictError(
                "This note changed outside this editor. Your draft is safe; save a copy or reload the file."
            )
        metadata = {}
        if previous is not None:
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
        text = "---\n" + yaml.safe_dump(metadata, allow_unicode=True) + "---\n\n" + body
        atomic_write(path, text)
        self.store.audit("note.saved", notebook, {"id": note_id, "kind": kind})
        return {
            "id": note_id,
            "title": title,
            "body": body,
            "revision": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    def autosave_note(self, notebook: str, draft_id: str, note: dict) -> dict:
        validate_note_id(note["id"])
        with self.store.lock:
            path = self.store.notebook_path(notebook) / "drafts" / (identifier(draft_id) + ".json")
            write_json(path, {"draft_id": draft_id, "note": note, "updated_at": now()})
            try:
                result = self.save_note(
                    notebook, note["title"], note["body"], note["id"], revision=note["revision"]
                )
            except ConflictError:
                # A committed save may have lost its HTTP response. Accept an identical
                # retry without replacing metadata another editor may have added.
                result = next(
                    (
                        saved
                        for saved in self.list_notes(notebook)
                        if saved["id"] == note["id"]
                        and saved["title"] == note["title"]
                        and saved["body"] == note["body"]
                    ),
                    None,
                )
                if result is None:
                    raise
            path.unlink(missing_ok=True)
            return result

    def drafts(self, notebook: str) -> list[dict]:
        with self.store.lock:
            notes = {note["id"]: note for note in self.list_notes(notebook)}
            drafts = []
            for path in (self.store.notebook_path(notebook) / "drafts").glob("*.json"):
                draft = json.loads(read_text(path))
                note = draft["note"]
                saved = notes.get(note["id"])
                # A crash may occur after committing Markdown but before removing its draft.
                if saved and all(saved[key] == note[key] for key in ("title", "body")):
                    path.unlink()
                else:
                    drafts.append(draft)
            return sorted(drafts, key=lambda d: d["updated_at"], reverse=True)

    def discard_draft(self, notebook: str, draft_id: str):
        with self.store.lock:
            path = self.store.notebook_path(notebook) / "drafts" / (identifier(draft_id) + ".json")
            path.unlink(missing_ok=True)
