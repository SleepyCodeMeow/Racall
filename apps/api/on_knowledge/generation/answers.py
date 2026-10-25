"""Writer/critic answer generation over bounded, version-checked evidence."""

from __future__ import annotations

from ..answer_language import question_language
from ..claim_generation import AnswerLanguageError, generate_claims
from ..claim_verification import verify_claims
from ..evidence_references import prepare_evidence
from ..features.context.evidence import bounded_evidence
from ..features.context.history import limit_history, retrieval_query
from ..features.context.service import ContextService
from ..provider_factory import completion_provider
from ..storage import Store


def generate_answer(
    store: Store,
    context_service: ContextService,
    search,
    notebook: str,
    question: str,
    evidence: list[dict] | None = None,
    *,
    context: dict | None = None,
    history: list[dict] | None = None,
    settings: dict | None = None,
    progress=None,
    cancel=None,
) -> dict:
    def checkpoint():
        if cancel:
            cancel()
        if context is not None:
            context_service.validate_snapshot(notebook, context)

    def stage(name):
        checkpoint()
        if progress:
            progress(name, None)

    checkpoint()
    history, history_trimmed = limit_history(history)
    query = retrieval_query(question, history)
    if evidence is None:
        result = (
            search(notebook, query)
            if context is None and settings is None
            else search(notebook, query, context=context, settings=settings)
        )
    else:
        result = {"evidence": evidence, "mode": "research"}
    evidence, truncated = bounded_evidence(result["evidence"])
    if context is not None:
        source_versions = {item["id"]: item["version"] for item in context["sources"]}
        note_revisions = {item["id"]: item["revision"] for item in context["notes"]}
        for item in evidence:
            version = (
                note_revisions.get(item.get("note_id"))
                if item.get("kind") == "note"
                else source_versions.get(item.get("source_id"))
            )
            if version is None or version != item.get("version"):
                raise ValueError("Evidence is outside the selected material versions.")
    truncated = truncated or result.get("context_info", {}).get("evidence_truncated", False)
    context_info = (
        context_service.info(context, evidence, truncated=truncated) if context is not None else None
    )
    if context_info is not None and history_trimmed:
        context_info["history_truncated"] = True
    metadata = {"context_info": context_info} if context_info is not None else {}
    checkpoint()
    if not evidence:
        return {
            "claims": [],
            "citations": [],
            "message": "В источниках не найдено достаточно данных.",
            "mode": result["mode"],
            "validated": False,
            **metadata,
        }
    visible_evidence, references = prepare_evidence(evidence)
    raw_provider = completion_provider(store.settings() if settings is None else settings)

    class CheckedProvider:
        def complete(self, system, data):
            checkpoint()
            response = raw_provider.complete(system, data)
            checkpoint()
            return response

    provider = CheckedProvider()
    stage("writer")
    try:
        claims = (
            generate_claims(
                provider, question, visible_evidence, question_language(question), history=history
            )
            if history
            else generate_claims(provider, question, visible_evidence, question_language(question))
        )
    except AnswerLanguageError as exc:
        return {
            "claims": [],
            "citations": [],
            "message": str(exc),
            "mode": result["mode"],
            "validated": False,
            **metadata,
        }
    allowed = {e["id"]: e for e in evidence}
    if not claims:
        return {
            "claims": [],
            "citations": [],
            "message": "Модель не смогла обосновать ответ источниками.",
            "mode": result["mode"],
            "validated": False,
            **metadata,
        }
    stage("critic")
    claims = verify_claims(provider, question, claims, visible_evidence)
    claims = [{**c, "evidence_ids": [references[label]["id"] for label in c["evidence_ids"]]} for c in claims]
    used = list(dict.fromkeys(i for c in claims for i in c["evidence_ids"]))
    citations = [{**allowed[i], "number": n} for n, i in enumerate(used, 1)]
    store.audit("answer.validated", notebook, {"accepted_claims": len(claims), "citations": used})
    checkpoint()
    return {
        "claims": claims,
        "citations": citations,
        "mode": result["mode"],
        "validated": bool(claims),
        "message": "" if claims else "Проверка не подтвердила ответ. Уточните вопрос или добавьте источники.",
        **metadata,
    }
