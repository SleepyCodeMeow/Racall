"""Exact note passages and bounded source material for generation."""
import re
from uuid import NAMESPACE_URL, uuid5

MAX_EVIDENCE_CHARS = 24000


def note_passages(notebook: str, note: dict, *, size: int = 1600) -> list[dict]:
    body = note["body"]
    result = []
    for start in range(0, len(body), size):
        end = min(len(body), start + size)
        quote = body[start:end]
        if not quote.strip():
            continue
        result.append({
            "id": str(uuid5(NAMESPACE_URL, f"racall-note:{notebook}:{note['id']}:{note['revision']}:{start}:{end}")),
            "kind": "note", "note_id": note["id"], "source_id": note["id"],
            "version": note["revision"], "title": note["title"], "quote": quote,
            "location": {"element": 0, "type": "note", "section": note["title"],
                         "line_start": body[:start].count("\n") + 1,
                         "line_end": body[:end].count("\n") + 1,
                         "offset_start": start, "offset_end": end},
        })
    return result


def rank_note_passages(evidence: list[dict], query: str) -> list[dict]:
    terms = set(re.findall(r"\w+", query.casefold(), re.UNICODE)[:32])
    scored = [(item, sum(term in item["quote"].casefold() for term in terms)) for item in evidence]
    ranked = [item for item, score in sorted(scored, key=lambda pair: pair[1], reverse=True) if score]
    # A selected note can answer a generic request such as "summarize this note".
    return ranked or evidence


def bounded_evidence(evidence: list[dict], *, limit: int = 16,
                     max_chars: int = MAX_EVIDENCE_CHARS) -> tuple[list[dict], bool]:
    result, remaining, truncated = [], max_chars, False
    for original in evidence:
        if len(result) >= limit or remaining <= 0:
            truncated = True
            break
        quote = original["quote"]
        item = dict(original)
        if len(quote) > remaining:
            quote = quote[:remaining]
            location = {**item["location"], "offset_end": item["location"].get("offset_start", 0) + len(quote)}
            if "line_start" in location:
                location["line_end"] = location["line_start"] + quote.count("\n")
            item.update(quote=quote, location=location)
            truncated = True
        remaining -= len(quote)
        if quote.strip():
            result.append(item)
    return result, truncated


def representative_groups(groups: list[list[dict]], *, limit: int = 16, spread: bool = True) -> list[dict]:
    """Round-robin first/middle/last passages, so one long source cannot dominate."""
    ordered = []
    for group in groups:
        if group:
            indices = (list(dict.fromkeys([0, len(group) // 2, len(group) - 1, *range(len(group))]))
                       if spread else range(len(group)))
            ordered.append([group[index] for index in indices])
    result = []
    for depth in range(limit):
        for group in ordered:
            if depth < len(group):
                result.append(group[depth])
                if len(result) >= limit:
                    return result
    return result
