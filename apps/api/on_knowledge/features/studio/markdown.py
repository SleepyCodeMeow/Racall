"""Readable Markdown export of verified Studio records and exact quotations."""


def location_label(location: dict, language: str) -> str:
    russian = language == "ru"
    parts = []
    if location.get("page") is not None:
        parts.append(("стр. " if russian else "page ") + str(location["page"]))
    if location.get("section"):
        parts.append(str(location["section"]).replace("\n", " "))
    start, end = location.get("line_start"), location.get("line_end")
    if start is not None:
        span = str(start) + ("–" + str(end) if end is not None and end != start else "")
        parts.append(("строки " if russian else "lines ") + span)
    return " · ".join(parts) or ("Фрагмент источника" if russian else "Source passage")


def material_markdown(title: str, kind: str, records: list[dict], citations: list[dict], language: str) -> str:
    numbers = {item["id"]: item["number"] for item in citations}
    body = "# " + title.replace("\n", " ") + "\n\n"
    section = None
    for index, record in enumerate(records, 1):
        links = " ".join(f'[{numbers[label]}]' for label in record["evidence_ids"])
        if kind == "review_questions":
            body += f'## {index}. {record["question"]}\n\n{record["answer"]} {links}\n\n'
        else:
            if kind == "study_guide" and record["section"] and record["section"] != section:
                section = record["section"]
                body += "## " + section + "\n\n"
            body += "- " + record["text"] + " " + links + "\n\n"
    body += "## " + ("Источники" if language == "ru" else "Sources") + "\n\n"
    for item in citations:
        location = location_label(item["location"], language)
        quote = "\n".join("> " + line for line in item["quote"].splitlines())
        body += f'[{item["number"]}] {item["title"]} — {location}\n\n{quote}\n\n'
    return body
