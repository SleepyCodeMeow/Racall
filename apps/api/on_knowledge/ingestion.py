"""Public ingestion API used by isolated parser workers and import services.

Implementations live in documents/ so parsing, fetching and chunk provenance can
be reviewed independently without changing the worker's import contract.
"""

from .documents.chunking import chunk_document
from .documents.models import EXTENSIONS, MAX_BYTES, MAX_TEXT, Element, NormalizedDocument
from .documents.parsing import parse
from .documents.text import text_elements
from .documents.web import fetch_url, public_addresses

__all__ = [
    "EXTENSIONS",
    "MAX_BYTES",
    "MAX_TEXT",
    "Element",
    "NormalizedDocument",
    "chunk_document",
    "fetch_url",
    "parse",
    "public_addresses",
    "text_elements",
]
