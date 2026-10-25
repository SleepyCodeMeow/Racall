"""Normalized source structure and ingestion limits shared by all parsers."""

from pydantic import BaseModel, Field

MAX_BYTES = 25 * 1024 * 1024
MAX_TEXT = 8_000_000
EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}


class Element(BaseModel):
    type: str = "paragraph"
    text: str
    page: int | None = None
    section: str = ""
    line_start: int | None = None
    line_end: int | None = None


class NormalizedDocument(BaseModel):
    elements: list[Element] = Field(default_factory=list)
    parser: str
