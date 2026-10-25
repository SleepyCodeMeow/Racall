"""Shared evidence scope for answers, learning materials and their critic."""

EVIDENCE_SCOPE = (
    "Preserve the source's exact scope, time, modality and certainty. "
    "When paraphrasing or translating, preserve the factual predicate and the identity of the "
    "event. Approval, drafting, finalization, announcement, delivery and execution are different "
    "milestones; a date belongs only to the milestone explicitly dated in the passage. "
    "For example, an approval date does not establish when a plan was written or finalized. "
    "Prefer a close factual translation to an embellished synonym, and focus on the requested facts. "
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
    "Check each subject, predicate, event, date and unit separately, including translations. "
    "Do not treat a nearby lifecycle milestone as the same event: approval on a date does not "
    "entail finalization on that date unless the passage explicitly says so. "
    "Use only the passages cited by that claim, not an uncited passage or outside knowledge. "
    "One supported clause cannot rescue an unsupported conjunction, question premise, "
    "explanation, stronger negation or assertion that an unreported event did not happen. "
)
