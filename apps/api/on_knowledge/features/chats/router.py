from __future__ import annotations

from fastapi import APIRouter

from ...knowledge import Knowledge
from ...schemas import Question, Title
from ...storage import ConflictError, identifier
from ..context.history import bounded_history, retrieval_query
from ..context.schemas import ContextSelection, normalize_selection
from ..context.service import ContextService
from .schemas import ChatCreate, ChatQuestion
from .service import Chats


def create_router(chats: Chats, knowledge: Knowledge) -> APIRouter:
    router = APIRouter()
    contexts = ContextService(chats.store)

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
    def chat_create(notebook: str, body: ChatCreate):
        if not body.title.strip():
            raise ValueError("A chat title is required.")
        return chats.create(notebook, body.title.strip(), context=body.context)

    @router.get("/api/notebooks/{notebook}/chats/{thread}")
    def chat_get(notebook: str, thread: str):
        return chats.get(notebook, thread)

    @router.put("/api/notebooks/{notebook}/chats/{thread}/context")
    def chat_context(notebook: str, thread: str, body: ContextSelection):
        return chats.set_context(notebook, thread, body)

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
        with chats.store.notebook_operation(notebook):
            question = body.question.strip()
            if not question:
                raise ValueError("A question is required.")
            with chats.store.lock:
                current = chats.get(notebook, thread)
                selection = normalize_selection(
                    body.context if body.context is not None else current.get("context")
                )
                if any(turn["id"] == identifier(body.request_id) for turn in current["turns"]):
                    return chats.begin(
                        notebook, thread, body.request_id, question, body.mode, context=selection
                    )[0]
                snapshot = contexts.snapshot(notebook, selection)
                history, trimmed = bounded_history(current["turns"], snapshot)
                turn, fresh = chats.begin(
                    notebook,
                    thread,
                    body.request_id,
                    question,
                    body.mode,
                    context=selection,
                    snapshot=snapshot,
                )
                if not fresh:
                    return turn
            info = {**contexts.info(snapshot), "history_turns": len(history), "history_truncated": trimmed}
            try:
                if body.mode == "ask":
                    result = {
                        "answer": knowledge.answer(notebook, question, context=snapshot, history=history)
                    }
                    info.update(result["answer"].get("context_info", {}))
                else:
                    found = knowledge.search(notebook, retrieval_query(question, history), context=snapshot)
                    result = {"evidence": found["evidence"]}
                    info.update(found.get("context_info", contexts.info(snapshot, result["evidence"])))
                with chats.store.lock:
                    contexts.validate_snapshot(notebook, snapshot)
                    return chats.finish(
                        notebook, thread, body.request_id, status="completed", context_info=info, **result
                    )
            except ConflictError:
                return chats.finish(
                    notebook,
                    thread,
                    body.request_id,
                    status="failed",
                    error_code="context_changed",
                    context_info=info,
                )
            except Exception:
                # Persist the failed question without retaining provider responses or credentials.
                return chats.finish(notebook, thread, body.request_id, status="failed", context_info=info)

    return router
