"""Bounded local file parsing for PDF, DOCX, Markdown and plain text."""

from __future__ import annotations

import zipfile
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from .models import EXTENSIONS, MAX_BYTES, MAX_TEXT, Element, NormalizedDocument
from .text import text_elements


def parse(path: Path) -> NormalizedDocument:
    suffix = path.suffix.lower()
    if suffix not in EXTENSIONS:
        raise ValueError("Поддерживаются PDF, Markdown, TXT и DOCX")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Размер файла превышает 25 МБ")
    if suffix == ".pdf":
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("Сначала снимите пароль с PDF")
        if len(reader.pages) > 2000:
            raise ValueError("PDF превышает 2000 страниц")
        elements = []
        total = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text(extraction_mode="layout")
            total += len(text)
            if total > MAX_TEXT:
                raise ValueError("Слишком большой извлечённый текст")
            elements.extend(text_elements(text, page=number))
        parser = "pypdf-layout-v1"
    elif suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if (
                len(entries) > 3000
                or sum(f.file_size for f in entries) > 100 * 1024 * 1024
                or any(f.file_size > 1000 * max(f.compress_size, 1) for f in entries)
            ):
                raise ValueError("DOCX превышает лимит распаковки")
        elements, section = [], ""
        for block in Document(path).iter_inner_content():
            if isinstance(block, Paragraph) and block.text.strip():
                is_heading = block.style and block.style.name.startswith("Heading")
                if is_heading:
                    section = block.text
                elements.append(
                    Element(type="heading" if is_heading else "paragraph", text=block.text, section=section)
                )
            elif isinstance(block, Table):
                elements.append(
                    Element(
                        type="table",
                        section=section,
                        text="\n".join(" | ".join(c.text for c in row.cells) for row in block.rows),
                    )
                )
        parser = "python-docx-structure-v1"
    else:
        elements, parser = text_elements(path.read_text("utf-8-sig")), "markdown-blocks-v1"
    if not elements:
        raise ValueError("Текст не найден. Для сканированного PDF требуется OCR (ещё не включён).")
    if sum(len(e.text) for e in elements) > MAX_TEXT:
        raise ValueError("Слишком большой извлечённый текст")
    return NormalizedDocument(elements=elements, parser=parser)
