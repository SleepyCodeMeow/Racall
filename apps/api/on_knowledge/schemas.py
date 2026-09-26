from pydantic import BaseModel, Field, field_validator


class Title(BaseModel):
    title: str = Field(min_length=1, max_length=160)

    @field_validator("title")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A title is required.")
        return value


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
