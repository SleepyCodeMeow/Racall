"""Shared evidence scope for answers, learning materials and their critic."""

EVIDENCE_SCOPE = (
    "Preserve the source's exact scope, time, modality and certainty. "
    "Missing, unreported or unavailable information does not prove that an event never occurred "
    "or that a value does not exist. Do not turn absence of a report into proof of no event, "
    "zero results or failure. For example, 'No test results were published' does not support "
    "'No tests were performed'; it supports only a statement about the available reports. "
    "An explicit statement that no tests were performed can support that negative fact. "
    "Keep planned, scheduled or projected events distinct from completed or observed events. "
    "Do not invent causes or attach an unsupported clause to a supported fact. "
    "Prefer short atomic factual claims. If the requested fact is absent, state only what "
    "the passages establish about the available information, or return no claims. "
)

ENTAILMENT_CHECK = (
    "For every factual clause, premise and causal link, ask: could all of this claim's cited "
    "passages be true while that part of the claim is false? If yes, reject the ENTIRE claim. "
    "Use only the passages cited by that claim, not an uncited passage or outside knowledge. "
    "One supported clause cannot rescue an unsupported conjunction, question premise, "
    "explanation, stronger negation or assertion that an unreported event did not happen. "
)
