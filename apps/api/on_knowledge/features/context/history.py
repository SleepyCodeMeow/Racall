"""Conversation helps resolve a question; it never supplies factual evidence."""

import re

MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 6000


def limit_history(history: list[dict] | None) -> tuple[list[dict], bool]:
    """Clamp even internal callers before conversation text reaches a provider."""
    turns = [
        {
            "status": "completed",
            "question": item.get("question", ""),
            "answer": {"validated": True, "claims": [{"text": item.get("answer", "")}]},
        }
        for item in (history or [])
        if isinstance(item, dict)
    ]
    return bounded_history(turns)


def bounded_history(
    turns: list[dict],
    snapshot: dict | None = None,
    *,
    max_turns: int = MAX_HISTORY_TURNS,
    max_chars: int = MAX_HISTORY_CHARS,
) -> tuple[list[dict], bool]:
    allowed_sources = {item["id"]: item["version"] for item in (snapshot or {}).get("sources", [])}
    allowed_notes = {item["id"]: item["revision"] for item in (snapshot or {}).get("notes", [])}
    candidates, filtered = [], False
    for turn in turns:
        if turn.get("status") != "completed" or turn.get("mode", "ask") != "ask":
            continue
        answer = turn.get("answer") or {}
        citations = answer.get("citations", [])
        if snapshot is not None and any(
            (
                allowed_notes.get(item.get("note_id"))
                if item.get("kind") == "note"
                else allowed_sources.get(item.get("source_id"))
            )
            != item.get("version")
            for item in citations
        ):
            # Changing selection must also exclude material echoed by an older AI answer.
            filtered = True
            continue
        question = turn.get("question", "")
        prose = (
            " ".join(
                claim.get("text", "")
                for claim in answer.get("claims", [])
                if isinstance(claim, dict) and isinstance(claim.get("text"), str)
            )
            if answer.get("validated")
            else ""
        )
        if isinstance(question, str) and question.strip():
            filtered = filtered or len(question) > 2000 or len(prose) > 4000
            candidates.append({"question": question[:2000], "answer": prose[:4000]})
    result, remaining = [], max(0, max_chars)
    for turn in reversed(candidates):
        if len(result) >= max_turns or remaining <= 0:
            break
        size = len(turn["question"]) + len(turn["answer"])
        if size > remaining:
            # Keep the latest question first. Truncation is explicit in returned metadata.
            question = turn["question"][:remaining]
            prose = turn["answer"][: max(0, remaining - len(question))]
            result.append({"question": question, "answer": prose})
            filtered = True
            remaining = 0
        else:
            result.append(turn)
            remaining -= size
    return list(reversed(result)), filtered or len(result) < len(candidates)


def retrieval_query(question: str, history: list[dict] | None) -> str:
    """Cheap follow-up expansion; no hidden extra inference request."""
    if not history:
        return question
    current = re.findall(r"\w+", question, re.UNICODE)[:12]
    previous = []
    for turn in reversed(history[-2:]):
        previous.extend(re.findall(r"\w+", turn.get("question", ""), re.UNICODE)[:12])
        previous.extend(re.findall(r"\w+", turn.get("answer", ""), re.UNICODE)[:12])
    return " ".join(dict.fromkeys([*current, *previous]))[:2000]
