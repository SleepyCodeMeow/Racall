from pydantic import BaseModel, ConfigDict, Field, field_validator

from ...storage import identifier
from ..notes.repository import validate_note_id


class ContextSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ids: list[str] | None = Field(default=None, max_length=128)
    note_ids: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("source_ids")
    @classmethod
    def sources(cls, value):
        return None if value is None else sorted({identifier(item) for item in value})

    @field_validator("note_ids")
    @classmethod
    def notes(cls, value):
        for item in value:
            validate_note_id(item)
        return sorted(set(value))


def normalize_selection(value=None) -> dict:
    if isinstance(value, ContextSelection):
        return value.model_dump()
    return ContextSelection.model_validate({} if value is None else value).model_dump()
