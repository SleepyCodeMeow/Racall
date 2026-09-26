from pydantic import Field

from ...schemas import Title


class NoteBody(Title):
    body: str = Field(default="", max_length=1_000_000)
    id: str | None = None
    revision: str | None = Field(default=None, max_length=64)


class AutosaveBody(NoteBody):
    id: str = Field(min_length=1, max_length=181)
    revision: str = Field(max_length=64)
    draft_id: str
