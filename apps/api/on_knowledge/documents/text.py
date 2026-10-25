"""Markdown/text block boundaries, headings, code fences and source lines."""

import re

from .models import Element


def text_elements(text: str, page: int | None = None) -> list[Element]:
    result, lines, heading, start, code = [], [], "", 1, False

    def flush(end):
        if lines:
            result.append(
                Element(
                    text="\n".join(lines),
                    page=page,
                    section=heading,
                    type="code" if code else "paragraph",
                    line_start=start,
                    line_end=end,
                )
            )
            lines.clear()

    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            if code:
                lines.append(line)
                flush(i)
                code = False
            else:
                flush(i - 1)
                code, start = True, i
                lines.append(line)
        elif not code and re.match(r"^#{1,6}\s", line):
            flush(i - 1)
            heading = line.lstrip("# ")
            result.append(
                Element(type="heading", text=line, page=page, section=heading, line_start=i, line_end=i)
            )
        elif not code and not line.strip():
            flush(i - 1)
        else:
            if not lines:
                start = i
            lines.append(line)
    flush(len(text.splitlines()))
    return result
