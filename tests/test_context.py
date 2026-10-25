"""Context isolation and provenance through the real deterministic retrieval pipeline."""

import json
from uuid import uuid4

import pytest
from on_knowledge.features.context.evidence import bounded_evidence
from on_knowledge.features.context.history import bounded_history
from on_knowledge.features.context.schemas import normalize_selection
from on_knowledge.features.context.service import ContextService
from on_knowledge.knowledge import Knowledge
from on_knowledge.providers import OpenAICompatible
from on_knowledge.storage import ConflictError, Store, now, uid, write_json


@pytest.fixture
def workflow(tmp_path):
    store = Store(tmp_path)
    notebook = store.create_notebook("Context tests")["id"]
    knowledge = Knowledge(store)
    try:
        yield store, notebook, knowledge, ContextService(store)
    finally:
        knowledge.executor.shutdown(wait=True)


def source(store, notebook, texts, *, title="Document", embedding=None):
    item = {"id": uid(), "title": title, "version": uid(), "created_at": now(), "status": "ready"}
    chunks = [
        {
            "id": uid(),
            "text": text,
            "location": {"element": i, "offset_start": 0, "offset_end": len(text)},
            **(embedding or {}),
        }
        for i, text in enumerate(texts)
    ]
    store.save_source(notebook, item)
    store.replace_chunks(notebook, item["id"], item["version"], chunks)
    return item, chunks


def fake_model(monkeypatch, *, hook=None):
    calls = []

    def complete(self, system, data):
        calls.append((system, data))
        if hook:
            hook(len(calls))
        if "Plan research" in system:
            return {"queries": ["Marigold"]}
        if "supported_claim_ids" in system:
            return {"supported_claim_ids": [data["claims"][0]["claim_id"]]}
        return {
            "claims": [{"text": "Marigold launches in October.", "evidence_ids": [data["evidence"][0]["id"]]}]
        }

    monkeypatch.setattr(OpenAICompatible, "complete", complete)
    return calls


def test_filter_is_applied_before_fts_top40_and_reranking(workflow):
    store, notebook, knowledge, contexts = workflow
    excluded, _ = source(store, notebook, ["Marigold " * 30 for _ in range(55)])
    allowed, chunks = source(store, notebook, ["Marigold has one modest lexical match among many words."])
    snapshot = contexts.snapshot(notebook, {"source_ids": [allowed["id"]]})
    evidence = knowledge.search(notebook, "Marigold", context=snapshot)["evidence"]
    assert [item["id"] for item in evidence] == [chunks[0]["id"]]
    assert excluded["id"] not in json.dumps(evidence)


def test_explicit_none_is_empty_and_no_paid_or_embedding_calls(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    item, _ = source(
        store,
        notebook,
        ["Marigold"],
        embedding={"embedding": [1.0, 0.0], "model": "http://127.0.0.1:11434/v1/fixture"},
    )
    settings = {"base_url": "http://127.0.0.1:11434/v1", "embedding_model": "fixture", "model": "test"}
    calls = fake_model(monkeypatch)
    monkeypatch.setattr(
        OpenAICompatible, "embed", lambda *args: pytest.fail("No embedding for empty context")
    )
    assert contexts.snapshot(notebook)["sources"][0]["id"] == item["id"]
    snapshot = contexts.snapshot(notebook, {"source_ids": []})
    assert knowledge.search(notebook, "Marigold", context=snapshot, settings=settings)["evidence"] == []
    answer = knowledge.answer(notebook, "Marigold", context=snapshot, settings=settings)
    assert not answer["validated"] and answer["context_info"]["source_count"] == 0
    session = knowledge.research(notebook, "Marigold", context=snapshot, settings=settings)
    assert session["status"] == "completed" and not session["answer"]["validated"]
    assert calls == []


def test_selected_notes_are_real_revisioned_evidence_for_generic_question(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    note = store.save_note(notebook, "Mission", "Marigold launches in October.\nKeep this exact passage.")
    snapshot = contexts.snapshot(notebook, {"source_ids": [], "note_ids": [note["id"]]})
    calls = fake_model(monkeypatch)
    answer = knowledge.answer(notebook, "Summarize my note", context=snapshot)
    assert answer["validated"] and len(calls) == 2
    citation = answer["citations"][0]
    assert citation["kind"] == "note" and citation["note_id"] == note["id"]
    assert citation["source_id"] == note["id"] and citation["version"] == note["revision"]
    loc = citation["location"]
    assert note["body"][loc["offset_start"] : loc["offset_end"]] == citation["quote"]
    assert citation["id"] != "E1" and answer["claims"][0]["evidence_ids"] == [citation["id"]]
    assert answer["context_info"]["note_count"] == answer["context_info"]["included_notes"] == 1


@pytest.mark.parametrize("change_during_call", [False, True])
def test_note_revision_changes_reject_before_next_provider_phase(workflow, monkeypatch, change_during_call):
    store, notebook, knowledge, contexts = workflow
    note = store.save_note(notebook, "Mission", "Marigold launches in October.")
    snapshot = contexts.snapshot(notebook, {"source_ids": [], "note_ids": [note["id"]]})

    def change():
        store.save_note(notebook, "Mission", "Different current content.", note["id"])

    calls = fake_model(
        monkeypatch, hook=lambda count: change() if count == 1 and change_during_call else None
    )
    if not change_during_call:
        change()
    with pytest.raises(ConflictError, match="materials changed"):
        knowledge.answer(notebook, "Marigold", context=snapshot)
    assert len(calls) == int(change_during_call)


def test_changed_source_version_and_cross_notebook_selection_are_rejected(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    item, _ = source(store, notebook, ["Marigold"])
    snapshot = contexts.snapshot(notebook)
    other = store.create_notebook("Other")["id"]
    with pytest.raises(ValueError, match="belong"):
        contexts.snapshot(other, {"source_ids": [item["id"]]})
    with pytest.raises(ValueError, match="different notebook"):
        knowledge.answer(other, "Marigold", context=snapshot)
    calls = fake_model(monkeypatch)
    store.save_source(notebook, {**item, "version": uid()})
    with pytest.raises(ConflictError):
        knowledge.answer(notebook, "Marigold", context=snapshot)
    assert not calls


def test_excluded_and_stale_vectors_never_trigger_embedding(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    settings = {"base_url": "http://127.0.0.1:11434/v1", "model": "test", "embedding_model": "fixture"}
    source(
        store,
        notebook,
        ["Forbidden"],
        embedding={"embedding": [1.0, 0.0], "model": settings["base_url"] + "/fixture"},
    )
    allowed, _ = source(store, notebook, ["Marigold"])
    # A stale vector in the cache is not part of the selected current source version.
    stale = {
        "id": uid(),
        "text": "stale",
        "location": {},
        "embedding": [1.0, 0.0],
        "model": settings["base_url"] + "/fixture",
    }
    with store.db() as db:
        db.execute(
            "INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)",
            (stale["id"], notebook, allowed["id"], "old-version", "stale", "{}", "[1,0]", stale["model"]),
        )
    monkeypatch.setattr(
        OpenAICompatible, "embed", lambda *args: pytest.fail("Excluded vector reached embeddings")
    )
    snapshot = contexts.snapshot(notebook, {"source_ids": [allowed["id"]]})
    assert knowledge.search(notebook, "Marigold", context=snapshot, settings=settings)["mode"] == "keyword"


def test_history_is_bounded_and_drops_answers_from_excluded_or_changed_material():
    source_id = str(uuid4())
    snapshot = {"sources": [{"id": source_id, "version": "v1"}], "notes": []}
    turns = [
        {
            "status": "completed",
            "mode": "ask",
            "question": "Question " + str(i),
            "answer": {
                "validated": True,
                "claims": [{"text": "x" * 1500}],
                "citations": [{"source_id": source_id, "version": "v1"}],
            },
        }
        for i in range(10)
    ]
    turns.append(
        {
            "status": "completed",
            "question": "Excluded secret question",
            "answer": {
                "validated": True,
                "claims": [{"text": "Excluded secret"}],
                "citations": [{"source_id": source_id, "version": "v0"}],
            },
        }
    )
    history, trimmed = bounded_history(turns, snapshot)
    assert trimmed and len(history) <= 6
    assert sum(len(item["question"]) + len(item["answer"]) for item in history) <= 6000
    assert history[-1]["question"] == "Question 9" and "Excluded" not in json.dumps(history)


def test_history_is_context_only_with_no_extra_rewrite_call(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    item, _ = source(store, notebook, ["Marigold launches in October."])
    calls = fake_model(monkeypatch)
    history = [{"question": "Tell me about Marigold", "answer": "An unsupported past answer."}]
    answer = knowledge.answer(
        notebook, "When does it launch?", context=contexts.snapshot(notebook), history=history
    )
    assert answer["validated"] and len(calls) == 2
    system, data = calls[0]
    assert "NOT evidence" in system and data["conversation_history"] == history
    assert all(e["source_id"] == item["id"] for e in answer["citations"])
    assert "unsupported past answer" not in json.dumps(data["evidence"]).lower()
    assert "conversation_history" not in calls[1][1]  # The critic only judges supplied real evidence.


def test_gather_is_representative_and_reports_bounded_coverage(workflow):
    store, notebook, _, contexts = workflow
    first, chunks = source(store, notebook, [f"Passage {i} with exact data." for i in range(11)])
    snapshot = contexts.snapshot(notebook)
    gathered = contexts.gather_snapshot(notebook, snapshot, limit=3)
    assert [item["id"] for item in gathered["evidence"]] == [chunks[i]["id"] for i in (0, 5, 10)]
    assert gathered["context_info"]["evidence_truncated"]
    assert all(item["version"] == first["version"] for item in gathered["evidence"])
    source(store, notebook, ["A second source."])
    gathered = contexts.gather_snapshot(notebook, contexts.snapshot(notebook), limit=2)
    assert gathered["context_info"]["included_sources"] == 2
    capped, truncated = bounded_evidence(gathered["evidence"], max_chars=10)
    assert truncated and sum(len(item["quote"]) for item in capped) == 10
    assert capped[0]["location"]["offset_end"] == 10


def test_wrong_supplied_evidence_never_reaches_provider(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    item, chunks = source(store, notebook, ["Forbidden secret."])
    calls = fake_model(monkeypatch)
    evidence = [
        {
            "id": chunks[0]["id"],
            "source_id": item["id"],
            "version": item["version"],
            "title": "Forbidden",
            "quote": chunks[0]["text"],
            "location": chunks[0]["location"],
        }
    ]
    with pytest.raises(ValueError, match="outside"):
        knowledge.answer(
            notebook, "Secret", evidence, context=contexts.snapshot(notebook, {"source_ids": []})
        )
    assert not calls


def test_selection_is_strict_and_normalized():
    identifier = str(uuid4())
    assert normalize_selection({"source_ids": [identifier, identifier]}) == {
        "source_ids": [identifier],
        "note_ids": [],
    }
    assert normalize_selection({"source_ids": []})["source_ids"] == []
    for value in ([], "", False, {"source_ids": ["bad"]}, {"note_ids": ["../note"]}, {"unknown": True}):
        with pytest.raises(ValueError):
            normalize_selection(value)


def test_research_uses_one_settings_snapshot_for_planner_embeddings_writer_and_critic(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    settings = {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "frozen-model",
        "embedding_model": "frozen-vector",
    }
    source(
        store,
        notebook,
        ["Marigold launches in October."],
        embedding={"embedding": [1.0, 0.0], "model": settings["base_url"] + "/frozen-vector"},
    )
    calls, embeddings = [], []

    def complete(self, system, data):
        calls.append((self.settings["model"], system))
        # Settings changed on disk after planning must not switch any later phase.
        write_json(
            store.root / "settings.json", {**settings, "model": "different", "embedding_model": "different"}
        )
        if "Plan research" in system:
            return {"queries": ["Marigold"]}
        if "supported_claim_ids" in system:
            return {"supported_claim_ids": ["C1"]}
        return {"claims": [{"text": "Marigold launches in October.", "evidence_ids": ["E1"]}]}

    def embed(self, texts):
        embeddings.append(self.settings["embedding_model"])
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(OpenAICompatible, "complete", complete)
    monkeypatch.setattr(OpenAICompatible, "embed", embed)
    session = knowledge.research(notebook, "Marigold", context=contexts.snapshot(notebook), settings=settings)
    assert session["status"] == "completed" and session["answer"]["validated"]
    assert len(calls) == 3 and {model for model, _ in calls} == {"frozen-model"}
    assert embeddings and set(embeddings) == {"frozen-vector"}
    assert {step["stage"] for step in session["steps"]} >= {"planner", "retrieval", "writer", "critic"}


def test_research_cancel_stops_next_provider_phase_and_persists_progress(workflow, monkeypatch):
    store, notebook, knowledge, contexts = workflow
    source(store, notebook, ["Marigold launches in October."])
    calls = fake_model(monkeypatch)
    stopped = False
    observed = []

    class Cancelled(Exception):
        cancelled = True

    def cancel():
        if stopped:
            raise Cancelled()

    def progress(stage, detail):
        nonlocal stopped
        paths = list((store.notebook_path(notebook) / "research").glob("*.json"))
        persisted = json.loads(paths[0].read_text("utf-8"))
        if detail is not None:
            assert persisted["steps"][-1]["stage"] == stage
        observed.append(stage)
        if stage == "writer":
            stopped = True

    with pytest.raises(Cancelled):
        knowledge.research(
            notebook, "Marigold", context=contexts.snapshot(notebook), progress=progress, cancel=cancel
        )
    sessions = list((store.notebook_path(notebook) / "research").glob("*.json"))
    persisted = json.loads(sessions[0].read_text("utf-8"))
    assert persisted["status"] == "cancelled" and "answer" not in persisted
    assert len(calls) == 1 and observed[-1] == "writer"
    assert persisted["steps"][-1]["stage"] == "writer"
