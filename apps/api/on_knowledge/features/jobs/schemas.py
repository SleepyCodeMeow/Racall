from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ...storage import identifier
from ..context.schemas import ContextSelection

GenerationKind = Literal["research", "summary", "study_guide", "review_questions"]


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    kind: GenerationKind
    question: str = Field(default="", max_length=8000)
    title: str = Field(default="", max_length=200)
    language: Literal["en", "ru"] = "en"
    context: ContextSelection = Field(default_factory=ContextSelection)

    @field_validator("request_id")
    @classmethod
    def request(cls, value):
        return identifier(value)

    @field_validator("question", "title")
    @classmethod
    def clean(cls, value):
        return value.strip()

    @model_validator(mode="after")
    def research_question(self):
        if self.kind == "research" and not self.question:
            raise ValueError("A research question is required.")
        return self


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str

    @field_validator("request_id")
    @classmethod
    def request(cls, value):
        return identifier(value)
