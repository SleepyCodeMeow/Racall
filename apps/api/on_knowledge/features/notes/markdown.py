"""Shared Markdown/frontmatter decoding and exact-text note revision hashes."""

from __future__ import annotations

import hashlib

import yaml


def split_note(text: str) -> tuple[dict, str]:
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
    return metadata, body


def note_revision(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def note_document(note_id: str, text: str) -> dict:
    metadata, body = split_note(text)
    return {
        "id": note_id,
        "title": str(metadata.get("title", note_id)),
        "body": body,
        "revision": note_revision(text),
    }
