"""Workflow regressions for an observed absence-of-report semantic failure.

These tests check policy propagation and filtering. Actual entailment by a model
is evaluated separately against the recorded live failure.
"""

import json
from pathlib import Path

import pytest
from on_knowledge.evidence_policy import ENTAILMENT_CHECK, EVIDENCE_SCOPE
from on_knowledge.features.studio.generator import UnverifiedMaterial, generate_material
from on_knowledge.knowledge import Knowledge
from on_knowledge.storage import Store


def recorded_failure():
    path = Path(__file__).resolve().parents[1] / "evals/release03/regressions/absence-versus-event.json"
    return json.loads(path.read_text("utf-8"))


@pytest.mark.parametrize("explicit_negative", [False, True])
def test_answer_preserves_record_scope_without_banning_supported_negative_facts(
    tmp_path, monkeypatch, explicit_negative
):
    failure = recorded_failure()
    unsupported = failure["unsupported_claim"]["text"]
    safe = (
        "No samples were collected on April 3, 2031."
        if explicit_negative
        else "The records do not report exact measured temperatures."
    )
    quote = (
        "The log confirms that no samples were collected on April 3, 2031."
        if explicit_negative
        else failure["evidence"][0]["quote"]
    )
    calls = []

    class Provider:
        def complete(self, system, data):
            calls.append((system, data))
            assert EVIDENCE_SCOPE in system
            if "supported_claim_ids" in system:
                assert ENTAILMENT_CHECK in system
                assert data["claims"][-1]["text"] == safe
                return {"supported_claim_ids": ["C1" if explicit_negative else "C2"]}
            claims = [] if explicit_negative else [{"text": unsupported, "evidence_ids": ["E1"]}]
            return {"claims": [*claims, {"text": safe, "evidence_ids": ["E1"]}]}

    monkeypatch.setattr("on_knowledge.generation.answers.completion_provider", lambda settings: Provider())
    store = Store(tmp_path)
    knowledge = Knowledge(store)
    notebook = store.create_notebook("Synthetic evidence scope")["id"]
    evidence = [{"id": "canonical-passage", "quote": quote, "source_id": "synthetic", "version": "r1"}]
    try:
        answer = knowledge.answer(notebook, failure["question"], evidence)
    finally:
        knowledge.executor.shutdown(wait=True)
    assert answer["validated"]
    assert answer["claims"] == [{"text": safe, "evidence_ids": ["canonical-passage"]}]
    assert answer["citations"] == [{**evidence[0], "number": 1}]
    assert len(calls) == 2


def test_review_question_with_unsupported_premise_is_not_saved_as_valid_material(monkeypatch):
    question = "Why were no measurements taken?"
    answer = "The records do not report measured values."
    calls = []

    class Provider:
        def complete(self, system, data):
            calls.append((system, data))
            assert EVIDENCE_SCOPE in system
            if "supported_claim_ids" in system:
                assert ENTAILMENT_CHECK in system
                assert question in data["claims"][0]["text"]
                assert answer in data["claims"][0]["text"]
                return {"supported_claim_ids": []}
            return {"questions": [{"question": question, "answer": answer, "evidence_ids": ["E1"]}]}

    monkeypatch.setattr(
        "on_knowledge.features.studio.generator.completion_provider", lambda settings: Provider()
    )
    with pytest.raises(UnverifiedMaterial):
        generate_material(
            "review_questions",
            "Review the records.",
            "Review",
            "en",
            [{"id": "canonical", "quote": "No measured values were reported."}],
            {},
            lambda: None,
            lambda *args: None,
        )
    assert len(calls) == 2
