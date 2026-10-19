"""Observed mixed-language failures through the production answer workflow."""

import pytest
from on_knowledge.knowledge import Knowledge
from on_knowledge.providers import OpenAICompatible
from on_knowledge.storage import Store

RU_CLAIM = "Фактические результаты работы станции «Лис» ещё не получены."
EN_CLAIM = "The Лис station has not yet reported actual measurements."


@pytest.fixture
def workflow(tmp_path):
    store = Store(tmp_path)
    notebook = store.create_notebook("Language regression")["id"]
    knowledge = Knowledge(store)
    try:
        yield knowledge, notebook
    finally:
        knowledge.executor.shutdown(wait=True)


def passage():
    return {"id": "canonical-chunk", "source_id": "station", "version": "original-v1",
            "title": "Станция Лис", "quote": RU_CLAIM, "location": {"element": 0}}


def test_english_question_with_russian_name_has_explicit_language_and_one_repair(workflow, monkeypatch):
    knowledge, notebook = workflow
    calls = []

    def complete(self, system, data):
        calls.append((system, data))
        if "supported_claim_ids" in system:
            return {"supported_claim_ids": ["C1"]}
        assert data.get("answer_language") == "en"
        assert "English" in system
        text = RU_CLAIM if len(calls) == 1 else EN_CLAIM
        return {"claims": [{"text": text, "evidence_ids": ["E1"]}]}

    monkeypatch.setattr(OpenAICompatible, "complete", complete)
    answer = knowledge.answer(notebook, "What exact temperatures has the Лис station already measured?", [passage()])
    assert len(calls) == 3  # One repair, followed by a fresh evidence verification.
    assert answer["validated"]
    assert answer["claims"] == [{"text": EN_CLAIM, "evidence_ids": ["canonical-chunk"]}]
    assert answer["citations"][0]["quote"] == RU_CLAIM
    assert answer["citations"][0]["version"] == "original-v1"


def test_persistent_wrong_language_stops_after_one_repair_without_verification(workflow, monkeypatch):
    knowledge, notebook = workflow
    calls = []

    def complete(self, system, data):
        calls.append((system, data))
        assert "supported_claim_ids" not in system
        return {"claims": [{"text": RU_CLAIM, "evidence_ids": ["E1"]}]}

    monkeypatch.setattr(OpenAICompatible, "complete", complete)
    answer = knowledge.answer(notebook, "What has the Лис station measured?", [passage()])
    assert len(calls) == 2
    assert not answer["validated"] and not answer["claims"] and not answer["citations"]
    assert "язык" in answer["message"]


def test_unsupported_repaired_claim_is_still_rejected(workflow, monkeypatch):
    knowledge, notebook = workflow
    calls = []

    def complete(self, system, data):
        calls.append((system, data))
        if "supported_claim_ids" in system:
            return {"supported_claim_ids": []}
        text = RU_CLAIM if len(calls) == 1 else "The station has measured 999 degrees."
        return {"claims": [{"text": text, "evidence_ids": ["E1"]}]}

    monkeypatch.setattr(OpenAICompatible, "complete", complete)
    answer = knowledge.answer(notebook, "What has the Лис station measured?", [passage()])
    assert len(calls) == 3
    assert not answer["validated"] and not answer["claims"] and not answer["citations"]
