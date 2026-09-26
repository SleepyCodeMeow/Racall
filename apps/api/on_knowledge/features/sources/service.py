from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ...ingestion import NormalizedDocument, chunk_document
from ...providers import OpenAICompatible
from ...storage import ConflictError, Store, now, write_json
from .parser import parse_isolated
from .repository import Sources


class SourceService:
    def __init__(self, store: Store):
        self.store = store
        self.repository = Sources(store)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion")
        self.pending: set[str] = set()

    def submit(self, notebook: str, source: str, active_only: bool = False):
        with self.store.lock:
            self.store.source(notebook, source)
            if source in self.pending:
                return
            self.pending.add(source)
            self.executor.submit(self.ingest, notebook, source, active_only)

    def retry(self, notebook: str, source: str):
        with self.store.lock:
            item = self.store.source(notebook, source)
            if source in self.pending:
                raise ConflictError("This source is already being processed. Wait before updating it.")
            if item.get("pending_version"):
                item.update(refresh_status="queued", refresh_error=None)
            else:
                item.update(status="queued", error=None)
            self.store.save_source(notebook, item)
            self.submit(notebook, source)
            return item

    def ingest(self, notebook: str, source: str, active_only: bool = False):
        try:
            with self.store.notebook_operation(notebook):
                self._ingest(notebook, source, active_only)
        finally:
            with self.store.lock:
                self.pending.discard(source)

    def _ingest(self, notebook: str, source: str, active_only: bool = False):
        with self.store.lock:
            current = self.store.source(notebook, source)
            refresh = bool(current.get("pending_version")) and not active_only
            target = dict(current["pending_version"] if refresh else current)
            current.update(
                **(
                    {"refresh_status": "processing", "refresh_error": None}
                    if refresh
                    else {"status": "processing", "error": None}
                )
            )
            self.store.save_source(notebook, current)
        try:
            stored = self.repository.document(notebook, target)
            document = (
                NormalizedDocument.model_validate(stored)
                if stored
                else parse_isolated(self.repository.file(notebook, source, target["original"]))
            )
            document_path = self.repository.file(notebook, source, target.get("document", "document.json"))
            with self.store.lock:
                if not document_path.exists():
                    write_json(document_path, document.model_dump())
            chunks = chunk_document(document, source, target["version"])
            settings = self.store.settings()
            if settings.get("embedding_model"):
                vectors = OpenAICompatible(settings).embed([c["text"] for c in chunks])
                for c, v in zip(chunks, vectors):
                    c.update(embedding=v, model=settings["base_url"] + "/" + settings["embedding_model"])
            target.update(
                status="ready",
                error=None,
                chunks=len(chunks),
                parser=document.parser,
                indexed_at=now(),
                search_mode="hybrid" if settings.get("embedding_model") else "keyword",
            )
            if not active_only:
                for key in ("pending_version", "refresh_status", "refresh_error"):
                    target.pop(key, None)
            with self.store.db() as db:
                self.repository.snapshot(notebook, target)
                self.store.replace_chunks(notebook, source, target["version"], chunks, db)
                self.store.save_source(notebook, target)
        except Exception as exc:
            with self.store.lock:
                # A failed update leaves the last working source and its search index usable.
                current.update(
                    **(
                        {"refresh_status": "error", "refresh_error": str(exc)[:500]}
                        if refresh
                        else {"status": "error", "error": str(exc)[:500]}
                    )
                )
                self.store.save_source(notebook, current)
                self.store.audit("ingestion.failed", notebook, {"source": source, "type": type(exc).__name__})
            return
        self.store.audit("ingestion.completed", notebook, {"source": source, "chunks": len(chunks)})

    def recover(self):
        for notebook in self.store.notebooks():
            for source in self.store.sources(notebook["id"]):
                with self.store.db() as db:
                    indexed = db.execute(
                        "SELECT 1 FROM chunks WHERE source=? AND version=? LIMIT 1",
                        (source["id"], source["version"]),
                    ).fetchone()
                if source.get("pending_version") and source.get("refresh_status") in ("queued", "processing"):
                    self.submit(notebook["id"], source["id"])
                elif source["status"] in ("queued", "processing") or (
                    source["status"] == "ready" and not indexed
                ):
                    self.submit(notebook["id"], source["id"], active_only=bool(source.get("pending_version")))
