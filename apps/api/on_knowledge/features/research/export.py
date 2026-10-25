"""Render accepted Research findings without changing their source quotations."""

import json


def research_markdown(question: str, answer: dict, language: str = "en") -> str:
    citations = {item["id"]: item for item in answer["citations"]}
    body = "# " + question + "\n\n"
    for claim in answer["claims"]:
        links = " ".join(f"[{citations[key]['number']}]" for key in claim["evidence_ids"])
        body += claim["text"] + " " + links + "\n\n"
    heading = "Источники" if language == "ru" else "Sources"
    body += f"## {heading}\n\n"
    for item in citations.values():
        location = json.dumps(item["location"], ensure_ascii=False)
        body += f"[{item['number']}] {item['title']} — {location}\n\n> {item['quote']}\n\n"
    return body
