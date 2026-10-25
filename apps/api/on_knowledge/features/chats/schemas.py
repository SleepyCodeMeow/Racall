from typing import Literal

from ...schemas import Question, Title
from ..context.schemas import ContextSelection


class ChatCreate(Title):
    context: ContextSelection | None = None


class ChatQuestion(Question):
    request_id: str
    mode: Literal["ask", "search"] = "ask"
    context: ContextSelection | None = None
