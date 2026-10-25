"""Research and Studio generation using an already accepted execution snapshot."""

from __future__ import annotations

from ...answer_language import question_language
from ..context.service import ContextService
from ..studio.generator import UnverifiedMaterial, generate_material


def generate_payload(
    notebook: str, job: dict, settings: dict, *, context: ContextService, knowledge, checkpoint, progress
) -> tuple[dict, dict | None]:
    """Generate content only; the service fences and commits its durable result."""
    if job["kind"] == "research":
        question = job["question"] or job["title"]
        if question_language(question) != job["language"]:
            question += "\n" + ("Ответь на русском." if job["language"] == "ru" else "Answer in English.")
        result = knowledge.research(
            notebook,
            question,
            context=job["context"],
            settings=settings,
            progress=progress,
            cancel=checkpoint,
        )
        if not result.get("answer", {}).get("validated"):
            raise UnverifiedMaterial()
        return {"answer": result["answer"]}, result

    progress("retrieval")
    gathered = context.gather_snapshot(notebook, job["context"])
    generated = generate_material(
        job["kind"],
        job["question"],
        job["title"],
        job["language"],
        gathered["evidence"],
        settings,
        checkpoint,
        progress,
    )
    generated["context_info"] = gathered["context_info"]
    return generated, None
