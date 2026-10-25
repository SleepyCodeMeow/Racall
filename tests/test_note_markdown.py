import hashlib

import pytest
import yaml
from on_knowledge.features.context.service import ContextService
from on_knowledge.features.notes.repository import NoteRepository
from on_knowledge.storage import Store


@pytest.mark.parametrize(
    "text,title,body",
    [
        ("# Plain\n\nBody", "fixture", "# Plain\n\nBody"),
        ("---\ntitle: Saved title\n---\n\n\nBody", "Saved title", "Body"),
        ("---\ntitle: 42\n---\nBody", "42", "Body"),
        ("---\n- not\n- metadata\n---\n\nBody", "fixture", "Body"),
        ("---\ntitle: [broken\n---\n\nBody", "fixture", "Body"),
        ("---\ntitle: Unfinished", "fixture", "---\ntitle: Unfinished"),
    ],
)
def test_note_listing_and_context_share_exact_markdown_snapshot(tmp_path, text, title, body):
    store = Store(tmp_path)
    notebook = store.create_notebook("Notes")["id"]
    path = store.notebook_path(notebook) / "notes" / "fixture.md"
    path.write_bytes(text.encode("utf-8"))

    note = NoteRepository(store).list_notes(notebook)[0]
    context = ContextService(store)
    snapshot = context.snapshot(notebook, {"source_ids": [], "note_ids": ["fixture"]})
    expected = {"id": "fixture", "title": title, "revision": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    assert {key: note[key] for key in expected} == expected
    assert note["body"] == body
    assert snapshot["notes"] == [expected]
    context.validate_snapshot(notebook, snapshot)


def test_saving_note_preserves_custom_frontmatter_and_aliases(tmp_path):
    store = Store(tmp_path)
    notebook = store.create_notebook("Notes")["id"]
    path = store.notebook_path(notebook) / "notes" / "fixture.md"
    path.write_text(
        "---\ntitle: Original\naliases: Other name\ncustom:\n  count: 3\n---\n\nBefore", encoding="utf-8"
    )
    repository = NoteRepository(store)
    previous = repository.list_notes(notebook)[0]

    saved = repository.save_note(notebook, "Renamed", "After", "fixture", revision=previous["revision"])
    text = path.read_text(encoding="utf-8")
    metadata = yaml.safe_load(text.split("---\n", 2)[1])
    assert metadata == {
        "title": "Renamed",
        "id": "fixture",
        "aliases": ["Other name", "Renamed"],
        "custom": {"count": 3},
    }
    assert saved["revision"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    snapshot = ContextService(store).snapshot(notebook, {"source_ids": [], "note_ids": ["fixture"]})
    assert snapshot["notes"] == [{key: saved[key] for key in ("id", "title", "revision")}]
