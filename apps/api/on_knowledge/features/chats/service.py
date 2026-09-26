from __future__ import annotations

import json
import os

from ...storage import ConflictError, Store, identifier, now, read_text, uid, write_json


class Chats:
    """Portable transcripts, independent of the disposable retrieval index."""

    def __init__(self, store: Store):
        self.store = store

    def path(self, notebook: str, thread: str):
        return self.store.notebook_path(notebook) / "chats" / (identifier(thread) + ".json")

    def get(self, notebook: str, thread: str) -> dict:
        with self.store.lock:
            return json.loads(read_text(self.path(notebook, thread)))

    def list(self, notebook: str) -> list[dict]:
        with self.store.lock:
            items = [
                json.loads(read_text(p))
                for p in (self.store.notebook_path(notebook) / "chats").glob("*.json")
            ]
            return sorted(
                [{k: v for k, v in item.items() if k != "turns"} for item in items],
                key=lambda item: item["updated_at"],
                reverse=True,
            )

    def create(self, notebook: str, title: str) -> dict:
        item = {"id": uid(), "title": title, "created_at": now(), "updated_at": now(), "turns": []}
        with self.store.lock:
            write_json(self.path(notebook, item["id"]), item)
        return item

    def rename(self, notebook: str, thread: str, title: str) -> dict:
        with self.store.lock:
            item = self.get(notebook, thread)
            item.update(title=title, updated_at=now())
            write_json(self.path(notebook, thread), item)
            return item

    def delete(self, notebook: str, thread: str):
        with self.store.lock:
            item = self.get(notebook, thread)
            if any(t["status"] == "running" for t in item["turns"]):
                raise ConflictError("Wait for the current answer before deleting this chat.")
            destination = (
                self.store.notebook_path(notebook) / "trash" / "chats" / (identifier(thread) + ".json")
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(self.path(notebook, thread), destination)

    def begin(
        self, notebook: str, thread: str, request_id: str, question: str, mode: str
    ) -> tuple[dict, bool]:
        request_id = identifier(request_id)
        with self.store.lock:
            item = self.get(notebook, thread)
            for turn in item["turns"]:
                if turn["id"] == request_id:
                    if turn["question"] != question or turn["mode"] != mode:
                        raise ConflictError("This request ID was already used for a different question.")
                    return turn, False
            if any(t["status"] == "running" for t in item["turns"]):
                raise ConflictError("Wait for the current answer before sending another question.")
            turn = {
                "id": identifier(request_id),
                "question": question,
                "mode": mode,
                "created_at": now(),
                "status": "running",
            }
            item["turns"].append(turn)
            item["updated_at"] = now()
            write_json(self.path(notebook, thread), item)
            return turn, True

    def finish(self, notebook: str, thread: str, request_id: str, **result) -> dict:
        with self.store.lock:
            item = self.get(notebook, thread)
            turn = next(t for t in item["turns"] if t["id"] == identifier(request_id))
            turn.update(result, finished_at=now())
            item["updated_at"] = now()
            write_json(self.path(notebook, thread), item)
            return turn

    def recover(self):
        # Called only at service startup; unfinished provider calls are never replayed.
        with self.store.lock:
            for notebook in self.store.notebooks():
                for thread in self.list(notebook["id"]):
                    item = self.get(notebook["id"], thread["id"])
                    changed = False
                    for turn in item["turns"]:
                        if turn["status"] == "running":
                            turn.update(status="interrupted", finished_at=now())
                            changed = True
                    if changed:
                        write_json(self.path(notebook["id"], thread["id"]), item)
