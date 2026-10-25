"""Retrieve selected source/note evidence before any model answer is requested."""

from __future__ import annotations

import json
import re

from ..features.context.evidence import bounded_evidence, rank_note_passages
from ..features.context.service import ContextService
from ..provider_settings import embedding_settings
from ..providers import OpenAICompatible
from ..storage import Store
from .ranking import cosine, rrf


class RetrievalService:
    def __init__(self, store: Store, context: ContextService):
        self.store = store
        self.context = context

    def search(
        self,
        notebook: str,
        query: str,
        limit: int = 8,
        *,
        context: dict | None = None,
        settings: dict | None = None,
    ) -> dict:
        self.store.notebook_path(notebook)
        if context is not None:
            self.context.validate_snapshot(notebook, context)
        terms = re.findall(r"\w+", query, re.UNICODE)[:32]
        if not terms:
            return {"evidence": [], "mode": "keyword"}
        fts_query = " OR ".join('"' + term + '"' for term in terms)
        clause, parameters = "", [notebook]
        if context is not None:
            refs = context["sources"]
            clause = (
                " AND (c.source,c.version) IN (VALUES " + ",".join("(?,?)" for _ in refs) + ")"
                if refs
                else " AND 0"
            )
            parameters.extend(value for ref in refs for value in (ref["id"], ref["version"]))
        with self.store.db() as db:
            lexical = [
                r["id"]
                for r in db.execute(
                    """
                SELECT f.id FROM chunks_fts f JOIN chunks c ON c.id=f.id
                WHERE chunks_fts MATCH ? AND c.notebook=?
            """
                    + clause
                    + " ORDER BY bm25(chunks_fts) LIMIT 40",
                    [fts_query, *parameters],
                )
            ]
            rows = {
                r["id"]: dict(r)
                for r in db.execute("SELECT c.* FROM chunks c WHERE c.notebook=?" + clause, parameters)
            }
        rankings, mode = [lexical], "keyword"
        embedding = embedding_settings(self.store.settings() if settings is None else settings)
        model = embedding["base_url"] + "/" + embedding.get("embedding_model", "")
        compatible = [r for r in rows.values() if r["model"] == model and r["embedding"] != "null"]
        if embedding.get("embedding_model") and compatible:
            if context is not None:
                self.context.validate_snapshot(notebook, context)
            vector = OpenAICompatible(embedding).embed([query])[0]
            if context is not None:
                self.context.validate_snapshot(notebook, context)
            scored = [(r["id"], cosine(vector, json.loads(r["embedding"]))) for r in compatible]
            rankings.append(
                [key for key, score in sorted(scored, key=lambda t: t[1], reverse=True)[:40] if score > 0.15]
            )
            mode = "hybrid"
        sources = {s["id"]: s for s in self.store.sources(notebook)}
        notes = {}
        if context is not None and context.get("notes"):
            note_passages = rank_note_passages(self.context.note_evidence(notebook, context), query)
            notes = {item["id"]: item for item in note_passages}
            rankings.append(list(notes))
        evidence = []
        ranked = rrf(rankings)
        for key, score in ranked[:limit]:
            if key in notes:
                evidence.append({**notes[key], "score": score})
                continue
            row = rows[key]
            source = sources.get(row["source"])
            if not source or row["version"] != source["version"]:
                continue
            evidence.append(
                {
                    "id": row["id"],
                    "source_id": row["source"],
                    "version": row["version"],
                    "title": source["title"],
                    "quote": row["text"],
                    "score": score,
                    "location": json.loads(row["location"]),
                    "url": source.get("url"),
                }
            )
        self.store.audit(
            "retrieval",
            notebook,
            {"query_length": len(query), "mode": mode, "chunks": [e["id"] for e in evidence]},
        )
        if context is not None:
            self.context.validate_snapshot(notebook, context)
            evidence, truncated = bounded_evidence(evidence, limit=limit)
            return {
                "evidence": evidence,
                "mode": mode,
                "context_info": self.context.info(
                    context, evidence, truncated=truncated or len(ranked) > limit
                ),
            }
        return {"evidence": evidence, "mode": mode}
