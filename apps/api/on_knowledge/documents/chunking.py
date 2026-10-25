"""Stable chunk identifiers and exact source quote offsets."""

import hashlib
import re

from .models import NormalizedDocument


def chunk_document(document: NormalizedDocument, source: str, version: str) -> list[dict]:
    """Preserve element boundaries and exact quote offsets; long blocks split on words."""
    chunks = []
    for index, element in enumerate(document.elements):
        matches = list(re.finditer(r"\S+", element.text))
        for start in range(0, len(matches), 300):
            group = matches[start : start + 340]
            a, b = group[0].start(), group[-1].end()
            text = element.text[a:b]
            location = {
                **element.model_dump(exclude={"text"}),
                "element": index,
                "offset_start": a,
                "offset_end": b,
            }
            key = hashlib.sha256(f"{source}:{version}:{index}:{a}:{b}".encode()).hexdigest()
            chunks.append({"id": key, "text": text, "location": location})
            if start + 340 >= len(matches):
                break
    return chunks
