"""Application-facing facade for source ingestion, retrieval and generation.

API routes, MCP and job workers use this stable entry point. Workflow logic lives
in retrieval/ and generation/; storage formats and model policy stay in Python.
"""

from __future__ import annotations

from .features.context.service import ContextService
from .features.sources.service import SourceService
from .generation.answers import generate_answer
from .generation.research import run_research, save_research
from .operations import notebook_operation
from .retrieval.service import RetrievalService
from .storage import Store


class Knowledge:
    def __init__(self, store: Store):
        self.store = store
        self.sources = SourceService(store)
        self.executor = self.sources.executor
        self.context = ContextService(store)
        self.retrieval = RetrievalService(store, self.context)

    def submit(self, notebook: str, source: str):
        self.sources.submit(notebook, source)

    def ingest(self, notebook: str, source: str):
        self.sources.ingest(notebook, source)

    def recover(self):
        self.sources.recover()

    @notebook_operation
    def search(
        self,
        notebook: str,
        query: str,
        limit: int = 8,
        *,
        context: dict | None = None,
        settings: dict | None = None,
    ) -> dict:
        return self.retrieval.search(notebook, query, limit, context=context, settings=settings)

    @notebook_operation
    def answer(
        self,
        notebook: str,
        question: str,
        evidence: list[dict] | None = None,
        *,
        context: dict | None = None,
        history: list[dict] | None = None,
        settings: dict | None = None,
        progress=None,
        cancel=None,
    ) -> dict:
        return generate_answer(
            self.store,
            self.context,
            self.search,
            notebook,
            question,
            evidence,
            context=context,
            history=history,
            settings=settings,
            progress=progress,
            cancel=cancel,
        )

    @notebook_operation
    def research(
        self,
        notebook: str,
        question: str,
        *,
        context: dict | None = None,
        settings: dict | None = None,
        progress=None,
        cancel=None,
    ) -> dict:
        return run_research(
            self.store,
            self.context,
            self.search,
            self.answer,
            notebook,
            question,
            context=context,
            settings=settings,
            progress=progress,
            cancel=cancel,
        )

    @notebook_operation
    def save_research(self, notebook: str, session_id: str) -> dict:
        return save_research(self.store, notebook, session_id)
