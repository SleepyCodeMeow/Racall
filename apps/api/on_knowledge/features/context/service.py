from __future__ import annotations

import hashlib
import json

import yaml

from ...storage import ConflictError, Store, identifier, now, read_text
from ..notes.repository import validate_note_id
from .evidence import bounded_evidence, note_passages, representative_groups
from .schemas import normalize_selection


class ContextService:
    def __init__(self, store: Store):
        self.store = store

    def _note(self, notebook: str, note_id: str) -> dict:
        validate_note_id(note_id)
        path = self.store.notebook_path(notebook) / "notes" / (note_id + ".md")
        text = read_text(path)
        metadata, body = {}, text
        if text.startswith("---\n"):
            parts = text.split("---\n", 2)
            if len(parts) == 3:
                try:
                    parsed = yaml.safe_load(parts[1])
                    metadata = parsed if isinstance(parsed, dict) else {}
                except yaml.YAMLError:
                    pass
                body = parts[2].lstrip("\n")
        return {"id": note_id, "title": str(metadata.get("title", note_id)), "body": body,
                "revision": hashlib.sha256(text.encode("utf-8")).hexdigest()}

    def snapshot(self, notebook: str, selection=None) -> dict:
        notebook = identifier(notebook)
        selection = normalize_selection(selection)
        with self.store.lock:
            self.store.notebook_path(notebook)
            sources = {item["id"]: item for item in self.store.sources(notebook)}
            chosen = selection["source_ids"]
            if chosen is None:
                chosen = sorted(key for key, item in sources.items() if item["status"] == "ready")
            refs = []
            for source_id in chosen:
                item = sources.get(source_id)
                if item is None:
                    raise ValueError("A selected source does not belong to this notebook.")
                if item["status"] != "ready":
                    raise ConflictError("A selected source is not ready. Wait for import or change the selection.")
                refs.append({"id": source_id, "version": item["version"], "title": item["title"]})
            notes = []
            for note_id in selection["note_ids"]:
                try:
                    item = self._note(notebook, note_id)
                except FileNotFoundError:
                    raise ValueError("A selected note does not belong to this notebook.") from None
                notes.append({key: item[key] for key in ("id", "revision", "title")})
            return {"notebook": notebook, "selection": selection, "sources": refs,
                    "notes": notes, "created_at": now()}

    def validate_snapshot(self, notebook: str, snapshot: dict):
        notebook = identifier(notebook)
        if snapshot.get("notebook") != notebook:
            raise ValueError("Context belongs to a different notebook.")
        with self.store.lock:
            sources = {item["id"]: item for item in self.store.sources(notebook)}
            for ref in snapshot.get("sources", []):
                current = sources.get(ref["id"])
                if current is None or current["status"] != "ready" or current["version"] != ref["version"]:
                    raise ConflictError("Selected materials changed. Review the context and retry explicitly.")
            for ref in snapshot.get("notes", []):
                try:
                    current = self._note(notebook, ref["id"])
                except FileNotFoundError:
                    raise ConflictError("Selected materials changed. Review the context and retry explicitly.") from None
                if current["revision"] != ref["revision"]:
                    raise ConflictError("Selected materials changed. Review the context and retry explicitly.")

    def note_evidence(self, notebook: str, snapshot: dict) -> list[dict]:
        with self.store.lock:
            self.validate_snapshot(notebook, snapshot)
            groups = [note_passages(notebook, self._note(notebook, ref["id"]))
                      for ref in snapshot.get("notes", [])]
            return representative_groups(groups, limit=64)

    @staticmethod
    def info(snapshot: dict, evidence: list[dict] | None = None, *, truncated=False) -> dict:
        evidence = evidence or []
        return {
            "source_count": len(snapshot.get("sources", [])), "note_count": len(snapshot.get("notes", [])),
            "included_sources": len({item["source_id"] for item in evidence if item.get("kind") != "note"}),
            "included_notes": len({item["note_id"] for item in evidence if item.get("kind") == "note"}),
            "evidence_truncated": truncated,
        }

    def gather_snapshot(self, notebook: str, snapshot: dict, *, limit=16, max_chars=24000) -> dict:
        with self.store.lock:
            self.validate_snapshot(notebook, snapshot)
            groups, total_passages = [], 0
            with self.store.db() as db:
                for source in snapshot.get("sources", [])[:limit]:
                    args = (notebook, source["id"], source["version"])
                    count = db.execute("SELECT COUNT(*) FROM chunks WHERE notebook=? AND source=? AND version=?",
                                       args).fetchone()[0]
                    total_passages += count
                    indices = list(dict.fromkeys([0, count // 2, count - 1, *range(min(count, limit))]))
                    rows = [dict(row) for index in indices if index >= 0
                            for row in db.execute(
                                "SELECT * FROM chunks WHERE notebook=? AND source=? AND version=? "
                                "ORDER BY rowid LIMIT 1 OFFSET ?", (*args, index))]
                    groups.append([{
                        "id": row["id"], "source_id": source["id"], "version": source["version"],
                        "title": source["title"], "quote": row["text"],
                        "location": json.loads(row["location"]),
                    } for row in rows])
            for ref in snapshot.get("notes", [])[:limit]:
                passages = note_passages(notebook, self._note(notebook, ref["id"]))
                groups.append(representative_groups([passages], limit=limit))
                total_passages += len(passages)
            sampled = representative_groups(groups, limit=limit, spread=False)
            evidence, truncated = bounded_evidence(sampled, limit=limit, max_chars=max_chars)
            truncated = (truncated or total_passages > len(evidence)
                         or len(snapshot.get("sources", [])) > limit or len(snapshot.get("notes", [])) > limit)
            return {"evidence": evidence, "context_info": self.info(snapshot, evidence, truncated=truncated)}
