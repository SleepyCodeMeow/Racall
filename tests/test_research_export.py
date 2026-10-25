"""Research exports keep their answer language and exact source provenance."""

import json
from uuid import uuid4

import pytest
from on_knowledge.knowledge import Knowledge
from on_knowledge.storage import Store, write_json


@pytest.mark.parametrize(
    "question,language,heading",
    [
        ("What has the Лис station measured?", None, "Sources"),
        ("Что известно о Marigold?", None, "Источники"),
        ("Marigold", "ru", "Источники"),
        ("Marigold", "en", "Sources"),
    ],
)
def test_research_export_heading_and_provenance(tmp_path, question, language, heading):
    store = Store(tmp_path)
    notebook = store.create_notebook("Export")["id"]
    session_id = str(uuid4())
    citation = {
        "id": "canonical-chunk",
        "source_id": str(uuid4()),
        "version": "historical-version",
        "title": "План станции",
        "quote": "Фактические результаты ещё не получены.",
        "location": {"element": 1, "offset_start": 0, "offset_end": 41},
        "number": 1,
    }
    answer = {
        "validated": True,
        "claims": [{"text": "No measurements have been reported.", "evidence_ids": [citation["id"]]}],
        "citations": [citation],
    }
    session = {"id": session_id, "question": question, "answer": answer}
    if language:
        session["language"] = language
    write_json(store.notebook_path(notebook) / "research" / (session_id + ".json"), session)
    knowledge = Knowledge(store)
    try:
        note = knowledge.save_research(notebook, session_id)
        assert f"## {heading}\n\n" in note["body"]
        assert citation["quote"] in note["body"]  # Never translate source quotations.
        assert "No measurements have been reported. [1]" in note["body"]
        memory = json.loads(
            (store.notebook_path(notebook) / "memory" / (session_id + ".json")).read_text("utf-8")
        )
        assert memory["supporting_citations"] == [citation]
        assert memory["finding"] == answer["claims"]
    finally:
        knowledge.executor.shutdown(wait=True)
