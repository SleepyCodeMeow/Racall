"""Research planning, retrieval, revision and accepted-memory export."""

from __future__ import annotations

import json

from ..answer_language import language_instruction, question_language
from ..features.context.service import ContextService
from ..features.research.export import research_markdown
from ..provider_factory import completion_provider
from ..storage import Store, identifier, now, uid, write_json


def run_research(
    store: Store,
    context_service: ContextService,
    search,
    answer_question,
    notebook: str,
    question: str,
    *,
    context: dict | None = None,
    settings: dict | None = None,
    progress=None,
    cancel=None,
) -> dict:
    def checkpoint():
        if cancel:
            cancel()
        if context is not None:
            context_service.validate_snapshot(notebook, context)

    def step(stage, detail):
        checkpoint()
        session["steps"].append({"stage": stage, **detail})
        write_json(path, session)
        if progress:
            progress(stage, detail)

    checkpoint()
    language = question_language(question)
    session = {
        "id": uid(),
        "question": question,
        "language": language,
        "created_at": now(),
        "steps": [],
        "status": "running",
    }
    if context is not None:
        session.update(context_snapshot=context, context_info=context_service.info(context))
    path = store.notebook_path(notebook) / "research" / (session["id"] + ".json")
    write_json(path, session)
    try:
        if context is not None and not context["sources"] and not context["notes"]:
            answer = answer_question(
                notebook, question, [], context=context, settings=settings, cancel=cancel
            )
            session.update(status="completed", answer=answer)
            return session
        if progress:
            progress("planner", None)
        checkpoint()
        planner = completion_provider(store.settings() if settings is None else settings).complete(
            'Plan research over the user\'s documents. Return JSON {"queries": [up to 4 specific search queries]} '
            "No external knowledge or browsing. " + language_instruction(language),
            {"question": question, "answer_language": language},
        )
        checkpoint()
        queries = [question] + [q[:1000] for q in planner.get("queries", []) if isinstance(q, str)][:4]
        step("planner", {"queries": queries})
        evidence = {}
        for query in queries:
            checkpoint()
            found = (
                search(notebook, query, 5)
                if context is None and settings is None
                else search(notebook, query, 5, context=context, settings=settings)
            )["evidence"]
            evidence.update({e["id"]: e for e in found})
            step("retrieval", {"query": query, "count": len(found)})
        options = {"context": context, "settings": settings, "cancel": cancel}
        if any(value is not None for value in options.values()) or progress is not None:
            options["progress"] = lambda stage, detail: step(stage, detail or {})
        answer = (
            answer_question(notebook, question, list(evidence.values())[:16], **options)
            if any(value is not None for value in options.values())
            else answer_question(notebook, question, list(evidence.values())[:16])
        )
        step("critic", {"accepted": answer["validated"]})
        if not answer["validated"]:
            checkpoint()
            found = (
                search(notebook, question, 16)
                if context is None and settings is None
                else search(notebook, question, 16, context=context, settings=settings)
            )["evidence"]
            answer = (
                answer_question(notebook, question, found, **options)
                if any(value is not None for value in options.values())
                else answer_question(notebook, question, found)
            )
            step("revision", {"accepted": answer["validated"]})
        checkpoint()
        session.update(status="completed", answer=answer)
    except Exception as exc:
        session.update(status="cancelled" if getattr(exc, "cancelled", False) else "failed")
        raise
    finally:
        write_json(path, session)
    return session


def save_research(store: Store, notebook: str, session_id: str) -> dict:
    path = store.notebook_path(notebook) / "research" / (identifier(session_id) + ".json")
    session = json.loads(path.read_text("utf-8"))
    answer = session.get("answer", {})
    if not answer.get("validated") or not answer.get("claims"):
        raise ValueError("Нельзя сохранить неподтверждённое исследование в память")
    language = session.get("language")
    if language not in ("en", "ru"):
        language = question_language(session["question"])
    body = research_markdown(session["question"], answer, language)
    artifact = store.save_note(notebook, session["question"], body, session_id, "artifacts")
    write_json(
        store.notebook_path(notebook) / "memory" / (session_id + ".json"),
        {
            "id": session_id,
            "finding": answer["claims"],
            "supporting_citations": answer["citations"],
            "originating_session": session_id,
            "created_at": now(),
            "status": "accepted",
            "validation": "model-critic-and-provenance; not a guarantee of factual truth",
        },
    )
    return artifact
