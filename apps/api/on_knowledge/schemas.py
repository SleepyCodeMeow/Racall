from pydantic import BaseModel, Field


class Title(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
