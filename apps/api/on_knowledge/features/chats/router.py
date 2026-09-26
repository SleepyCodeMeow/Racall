from __future__ import annotations

from fastapi import APIRouter

from ...knowledge import Knowledge
from ...schemas import Question, Title
from .schemas import ChatQuestion
from .service import Chats


def create_router(chats: Chats, knowledge: Knowledge) -> APIRouter:
    router = APIRouter()

    @router.post("/api/notebooks/{notebook}/search")
    def search(notebook: str, body: Question):
        return knowledge.search(notebook, body.question)

    @router.post("/api/notebooks/{notebook}/ask")
    def ask(notebook: str, body: Question):
        return knowledge.answer(notebook, body.question)

    @router.get("/api/notebooks/{notebook}/chats")
    def chat_list(notebook: str):
        return chats.list(notebook)

    @router.post("/api/notebooks/{notebook}/chats", status_code=201)
    def chat_create(notebook: str, body: Title):
        if not body.title.strip():
            raise ValueError("A chat title is required.")
        return chats.create(notebook, body.title.strip())

    @router.get("/api/notebooks/{notebook}/chats/{thread}")
    def chat_get(notebook: str, thread: str):
        return chats.get(notebook, thread)

    @router.put("/api/notebooks/{notebook}/chats/{thread}")
    def chat_rename(notebook: str, thread: str, body: Title):
        if not body.title.strip():
            raise ValueError("A chat title is required.")
        return chats.rename(notebook, thread, body.title.strip())

    @router.delete("/api/notebooks/{notebook}/chats/{thread}")
    def chat_delete(notebook: str, thread: str):
        chats.delete(notebook, thread)
        return {"deleted": True}

    @router.post("/api/notebooks/{notebook}/chats/{thread}/turns")
    def chat_turn(notebook: str, thread: str, body: ChatQuestion):
        question = body.question.strip()
        if not question:
            raise ValueError("A question is required.")
        turn, fresh = chats.begin(notebook, thread, body.request_id, question, body.mode)
        if not fresh:
            return turn
        try:
            result = (
                {"answer": knowledge.answer(notebook, question)}
                if body.mode == "ask"
                else {"evidence": knowledge.search(notebook, question)["evidence"]}
            )
            return chats.finish(notebook, thread, body.request_id, status="completed", **result)
        except Exception:
            # Persist the failed question without retaining provider responses or credentials.
            return chats.finish(notebook, thread, body.request_id, status="failed")

    return router
