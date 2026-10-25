from __future__ import annotations

import json
import math
import re

from .answer_language import language_instruction, question_language
from .claim_generation import AnswerLanguageError, generate_claims
from .claim_verification import verify_claims
from .evidence_references import prepare_evidence
from .features.context.evidence import bounded_evidence, rank_note_passages
from .features.context.history import limit_history, retrieval_query
from .features.context.service import ContextService
from .features.research.export import research_markdown
from .features.sources.service import SourceService
from .operations import notebook_operation
from .provider_factory import completion_provider
from .provider_settings import embedding_settings
from .providers import OpenAICompatible
from .storage import Store, now, uid, write_json


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] = scores.get(key, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0
    denominator = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / denominator if denominator else 0


class Knowledge:
    def __init__(self, store: Store):
        self.store = store
        self.sources = SourceService(store)
        self.executor = self.sources.executor
        self.context = ContextService(store)

    def submit(self, notebook: str, source: str):
        self.sources.submit(notebook, source)

    def ingest(self, notebook: str, source: str):
        self.sources.ingest(notebook, source)

    def recover(self):
        self.sources.recover()

    @notebook_operation
    def search(self, notebook: str, query: str, limit: int = 8, *,
               context: dict | None = None, settings: dict | None = None) -> dict:
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
            clause = (" AND (c.source,c.version) IN (VALUES " + ",".join("(?,?)" for _ in refs) + ")"
                      if refs else " AND 0")
            parameters.extend(value for ref in refs for value in (ref["id"], ref["version"]))
        with self.store.db() as db:
            lexical = [r["id"] for r in db.execute('''
                SELECT f.id FROM chunks_fts f JOIN chunks c ON c.id=f.id
                WHERE chunks_fts MATCH ? AND c.notebook=?
            ''' + clause + " ORDER BY bm25(chunks_fts) LIMIT 40", [fts_query, *parameters])]
            rows = {r["id"]: dict(r) for r in db.execute(
                "SELECT c.* FROM chunks c WHERE c.notebook=?" + clause, parameters)}
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
            rankings.append([key for key, score in sorted(scored, key=lambda t: t[1], reverse=True)[:40]
                             if score > 0.15])
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
            evidence.append({"id": row["id"], "source_id": row["source"], "version": row["version"],
                             "title": source["title"], "quote": row["text"], "score": score,
                             "location": json.loads(row["location"]), "url": source.get("url")})
        self.store.audit("retrieval", notebook, {"query_length": len(query), "mode": mode,
                                                "chunks": [e["id"] for e in evidence]})
        if context is not None:
            self.context.validate_snapshot(notebook, context)
            evidence, truncated = bounded_evidence(evidence, limit=limit)
            return {"evidence": evidence, "mode": mode, "context_info": self.context.info(
                context, evidence, truncated=truncated or len(ranked) > limit)}
        return {"evidence": evidence, "mode": mode}

    @notebook_operation
    def answer(self, notebook: str, question: str, evidence: list[dict] | None = None, *,
               context: dict | None = None, history: list[dict] | None = None,
               settings: dict | None = None, progress=None, cancel=None) -> dict:
        def checkpoint():
            if cancel:
                cancel()
            if context is not None:
                self.context.validate_snapshot(notebook, context)

        def stage(name):
            checkpoint()
            if progress:
                progress(name, None)

        checkpoint()
        history, history_trimmed = limit_history(history)
        query = retrieval_query(question, history)
        if evidence is None:
            result = (self.search(notebook, query) if context is None and settings is None
                      else self.search(notebook, query, context=context, settings=settings))
        else:
            result = {"evidence": evidence, "mode": "research"}
        evidence, truncated = bounded_evidence(result["evidence"])
        if context is not None:
            source_versions = {item["id"]: item["version"] for item in context["sources"]}
            note_revisions = {item["id"]: item["revision"] for item in context["notes"]}
            for item in evidence:
                version = (note_revisions.get(item.get("note_id")) if item.get("kind") == "note"
                           else source_versions.get(item.get("source_id")))
                if version is None or version != item.get("version"):
                    raise ValueError("Evidence is outside the selected material versions.")
        truncated = truncated or result.get("context_info", {}).get("evidence_truncated", False)
        context_info = self.context.info(context, evidence, truncated=truncated) if context is not None else None
        if context_info is not None and history_trimmed:
            context_info["history_truncated"] = True
        metadata = {"context_info": context_info} if context_info is not None else {}
        checkpoint()
        if not evidence:
            return {"claims": [], "citations": [], "message": "В источниках не найдено достаточно данных.",
                    "mode": result["mode"], "validated": False,
                    **metadata}
        visible_evidence, references = prepare_evidence(evidence)
        raw_provider = completion_provider(self.store.settings() if settings is None else settings)

        class CheckedProvider:
            def complete(self, system, data):
                checkpoint()
                response = raw_provider.complete(system, data)
                checkpoint()
                return response

        provider = CheckedProvider()
        stage("writer")
        try:
            claims = (generate_claims(provider, question, visible_evidence, question_language(question), history=history)
                      if history else generate_claims(provider, question, visible_evidence, question_language(question)))
        except AnswerLanguageError as exc:
            return {"claims": [], "citations": [], "message": str(exc),
                    "mode": result["mode"], "validated": False, **metadata}
        allowed = {e["id"]: e for e in evidence}
        if not claims:
            return {"claims": [], "citations": [], "message": "Модель не смогла обосновать ответ источниками.",
                    "mode": result["mode"], "validated": False, **metadata}
        stage("critic")
        claims = verify_claims(provider, question, claims, visible_evidence)
        claims = [{**c, "evidence_ids": [references[label]["id"] for label in c["evidence_ids"]]}
                  for c in claims]
        used = list(dict.fromkeys(i for c in claims for i in c["evidence_ids"]))
        citations = [{**allowed[i], "number": n} for n, i in enumerate(used, 1)]
        self.store.audit("answer.validated", notebook, {"accepted_claims": len(claims), "citations": used})
        checkpoint()
        return {"claims": claims, "citations": citations, "mode": result["mode"],
                "validated": bool(claims), "message": "" if claims else "Проверка не подтвердила ответ. Уточните вопрос или добавьте источники.",
                **metadata}

    @notebook_operation
    def research(self, notebook: str, question: str, *, context: dict | None = None,
                 settings: dict | None = None, progress=None, cancel=None) -> dict:
        def checkpoint():
            if cancel:
                cancel()
            if context is not None:
                self.context.validate_snapshot(notebook, context)

        def step(stage, detail):
            checkpoint()
            session["steps"].append({"stage": stage, **detail})
            write_json(path, session)
            if progress:
                progress(stage, detail)

        checkpoint()
        language = question_language(question)
        session = {"id": uid(), "question": question, "language": language,
                   "created_at": now(), "steps": [], "status": "running"}
        if context is not None:
            session.update(context_snapshot=context, context_info=self.context.info(context))
        path = self.store.notebook_path(notebook) / "research" / (session["id"] + ".json")
        write_json(path, session)
        try:
            if context is not None and not context["sources"] and not context["notes"]:
                answer = self.answer(notebook, question, [], context=context, settings=settings, cancel=cancel)
                session.update(status="completed", answer=answer)
                return session
            if progress:
                progress("planner", None)
            checkpoint()
            planner = completion_provider(self.store.settings() if settings is None else settings).complete(
                'Plan research over the user\'s documents. Return JSON {"queries": [up to 4 specific search queries]} '
                'No external knowledge or browsing. ' + language_instruction(language),
                {"question": question, "answer_language": language})
            checkpoint()
            queries = [question] + [q[:1000] for q in planner.get("queries", []) if isinstance(q, str)][:4]
            step("planner", {"queries": queries})
            evidence = {}
            for query in queries:
                checkpoint()
                found = (self.search(notebook, query, 5) if context is None and settings is None
                         else self.search(notebook, query, 5, context=context, settings=settings))["evidence"]
                evidence.update({e["id"]: e for e in found})
                step("retrieval", {"query": query, "count": len(found)})
            options = {"context": context, "settings": settings, "cancel": cancel}
            if any(value is not None for value in options.values()) or progress is not None:
                options["progress"] = lambda stage, detail: step(stage, detail or {})
            answer = (self.answer(notebook, question, list(evidence.values())[:16], **options)
                      if any(value is not None for value in options.values())
                      else self.answer(notebook, question, list(evidence.values())[:16]))
            step("critic", {"accepted": answer["validated"]})
            if not answer["validated"]:
                checkpoint()
                found = (self.search(notebook, question, 16) if context is None and settings is None
                         else self.search(notebook, question, 16, context=context, settings=settings))["evidence"]
                answer = (self.answer(notebook, question, found, **options)
                          if any(value is not None for value in options.values())
                          else self.answer(notebook, question, found))
                step("revision", {"accepted": answer["validated"]})
            checkpoint()
            session.update(status="completed", answer=answer)
        except Exception as exc:
            session.update(status="cancelled" if getattr(exc, "cancelled", False) else "failed")
            raise
        finally:
            write_json(path, session)
        return session

    @notebook_operation
    def save_research(self, notebook: str, session_id: str) -> dict:
        from .storage import identifier
        path = self.store.notebook_path(notebook) / "research" / (identifier(session_id) + ".json")
        session = json.loads(path.read_text("utf-8"))
        answer = session.get("answer", {})
        if not answer.get("validated") or not answer.get("claims"):
            raise ValueError("Нельзя сохранить неподтверждённое исследование в память")
        language = session.get("language")
        if language not in ("en", "ru"):
            language = question_language(session["question"])
        body = research_markdown(session["question"], answer, language)
        artifact = self.store.save_note(notebook, session["question"], body, session_id, "artifacts")
        write_json(self.store.notebook_path(notebook) / "memory" / (session_id + ".json"), {
            "id": session_id, "finding": answer["claims"], "supporting_citations": answer["citations"],
            "originating_session": session_id, "created_at": now(), "status": "accepted",
            "validation": "model-critic-and-provenance; not a guarantee of factual truth",
        })
        return artifact
