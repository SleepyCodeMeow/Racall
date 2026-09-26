from typing import Literal

from ...schemas import Question


class ChatQuestion(Question):
    request_id: str
    mode: Literal["ask", "search"] = "ask"
