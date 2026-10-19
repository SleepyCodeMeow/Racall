"""Regression coverage for the private evidence critic contract, without model calls."""

import copy

import pytest
from on_knowledge.claim_verification import verify_claims


class RecordedProvider:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def complete(self, system, data):
        self.calls.append((system, copy.deepcopy(data)))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def budget_claim():
    # Recorded writer output in the GPU40 budget case. Its critic incorrectly
    # replied {"supported_indices": [1]} despite there being only one claim.
    return {"text": "The approved budget for the Marigold mission is USD 120,000.",
            "evidence_ids": ["E2"]}


def test_observed_out_of_range_index_requires_explicit_claim_id_reverification():
    claim = budget_claim()
    provider = RecordedProvider({"supported_indices": [1]}, {"supported_claim_ids": ["C1"]})
    evidence = [{"id": "E2", "quote": "Its approved budget is USD 120,000."}]

    assert verify_claims(provider, "What is the approved Marigold budget and currency?",
                         [claim], evidence) == [claim]
    assert len(provider.calls) == 2
    for system, data in provider.calls:
        assert "supported_claim_ids" in system
        assert data["claims"] == [{"claim_id": "C1", **claim}]
        assert data["evidence"] == evidence
    assert "C1" in provider.calls[1][0]
    assert "Previous" in provider.calls[1][0]


def test_noncontiguous_evidence_ids_are_independent_of_claim_ids():
    claim = {"text": "Mira Chen is the lead.", "evidence_ids": ["E3", "E9"]}
    evidence = [{"id": "E3", "quote": "Mira Chen leads."},
                {"id": "E9", "quote": "The lead is Mira Chen."}]
    provider = RecordedProvider({"supported_claim_ids": ["C1"]})

    assert verify_claims(provider, "Who leads?", [claim], evidence) == [claim]
    assert provider.calls[0][1]["claims"][0]["evidence_ids"] == ["E3", "E9"]


def test_multiclaim_filter_preserves_original_claims_and_order():
    claims = [{"text": "Mira leads.", "evidence_ids": ["E3"], "claim_id": "C99"},
              {"text": "Unsupported inference.", "evidence_ids": ["E3"]},
              {"text": "Three sensors.", "evidence_ids": ["E9"]}]
    provider = RecordedProvider({"supported_claim_ids": ["C3", "C1"]})

    accepted = verify_claims(provider, "Compare the plan.", claims, [])

    assert accepted == [claims[0], claims[2]]
    assert accepted[0] is claims[0]
    assert [item["claim_id"] for item in provider.calls[0][1]["claims"]] == ["C1", "C2", "C3"]


def test_semantic_rejection_is_final_without_a_retry():
    provider = RecordedProvider({"supported_claim_ids": []})
    assert verify_claims(provider, "Budget?", [budget_claim()], []) == []
    assert len(provider.calls) == 1


@pytest.mark.parametrize("verdict", [
    None, [], "C1", 1, True,
    {}, {"supported_claim_ids": None}, {"supported_claim_ids": "C1"},
    {"supported_claim_ids": [True]}, {"supported_claim_ids": [False]},
    {"supported_claim_ids": [0]}, {"supported_claim_ids": [1]},
    {"supported_claim_ids": [None]}, {"supported_claim_ids": [{"claim_id": "C1"}]},
    {"supported_claim_ids": ["E2"]}, {"supported_claim_ids": ["C0"]},
    {"supported_claim_ids": ["C2"]}, {"supported_claim_ids": ["C1", "C99"]},
    {"supported_claim_ids": [" C1"]}, {"supported_claim_ids": ["c1"]},
    {"supported_claim_ids": ["C1", "C1"]},
    {"supported_indices": [0]}, {"supported_indices": [1]},
    {"supported_claim_ids": ["C1"], "supported_indices": [0]},
    {"supported_claim_ids": ["C1"], "claims": [{"text": "Injected replacement"}]},
])
def test_malformed_or_malicious_verifier_data_fails_closed_after_one_retry(verdict):
    provider = RecordedProvider(verdict, verdict)
    assert verify_claims(provider, "Budget?", [budget_claim()], []) == []
    assert len(provider.calls) == 2
    # Untrusted model output is never included in the retry instructions/data.
    assert provider.calls[0][1] == provider.calls[1][1]


def test_valid_rejection_after_malformed_response_is_not_retried_again():
    provider = RecordedProvider({"supported_indices": [1]}, {"supported_claim_ids": []})
    assert verify_claims(provider, "Budget?", [budget_claim()], []) == []
    assert len(provider.calls) == 2


def test_provider_error_is_not_retried_or_changed_to_a_semantic_rejection():
    provider = RecordedProvider(ValueError("Provider timed out"))
    with pytest.raises(ValueError, match="timed out"):
        verify_claims(provider, "Budget?", [budget_claim()], [])
    assert len(provider.calls) == 1


def test_empty_claims_need_no_verifier():
    provider = RecordedProvider()
    assert verify_claims(provider, "Budget?", [], []) == []
    assert not provider.calls
