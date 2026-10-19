from __future__ import annotations

import json
import math
import re

from .answer_language import language_instruction, question_language
from .claim_generation import AnswerLanguageError, generate_claims
from .claim_verification import verify_claims
from .evidence_references import prepare_evidence
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

    def submit(self, notebook: str, source: str):
        self.sources.submit(notebook, source)

    def ingest(self, notebook: str, source: str):
        self.sources.ingest(notebook, source)

    def recover(self):
        self.sources.recover()

    @notebook_operation
    def search(self, notebook: str, query: str, limit: int = 8) -> dict:
        self.store.notebook_path(notebook)
        terms = re.findall(r"\w+", query, re.UNICODE)[:32]
        if not terms:
            return {"evidence": [], "mode": "keyword"}
        fts_query = " OR ".join('"' + term + '"' for term in terms)
        with self.store.db() as db:
            lexical = [r["id"] for r in db.execute('''
                SELECT f.id FROM chunks_fts f JOIN chunks c ON c.id=f.id
                WHERE chunks_fts MATCH ? AND c.notebook=? ORDER BY bm25(chunks_fts) LIMIT 40
            ''', (fts_query, notebook))]
            rows = {r["id"]: dict(r) for r in db.execute("SELECT * FROM chunks WHERE notebook=?", (notebook,))}
        rankings, mode = [lexical], "keyword"
        settings = embedding_settings(self.store.settings())
        model = settings["base_url"] + "/" + settings.get("embedding_model", "")
        compatible = [r for r in rows.values() if r["model"] == model and r["embedding"] != "null"]
        if settings.get("embedding_model") and compatible:
            vector = OpenAICompatible(settings).embed([query])[0]
            scored = [(r["id"], cosine(vector, json.loads(r["embedding"]))) for r in compatible]
            rankings.append([key for key, score in sorted(scored, key=lambda t: t[1], reverse=True)[:40]
                             if score > 0.15])
            mode = "hybrid"
        sources = {s["id"]: s for s in self.store.sources(notebook)}
        evidence = []
        for key, score in rrf(rankings)[:limit]:
            row = rows[key]
            source = sources.get(row["source"])
            if not source or row["version"] != source["version"]:
                continue
            evidence.append({"id": row["id"], "source_id": row["source"], "version": row["version"],
                             "title": source["title"], "quote": row["text"], "score": score,
                             "location": json.loads(row["location"]), "url": source.get("url")})
        self.store.audit("retrieval", notebook, {"query_length": len(query), "mode": mode,
                                                "chunks": [e["id"] for e in evidence]})
        return {"evidence": evidence, "mode": mode}

    @notebook_operation
    def answer(self, notebook: str, question: str, evidence: list[dict] | None = None) -> dict:
        result = self.search(notebook, question) if evidence is None else {"evidence": evidence, "mode": "research"}
        evidence = result["evidence"]
        if not evidence:
            return {"claims": [], "citations": [], "message": "В источниках не найдено достаточно данных.",
                    "mode": result["mode"], "validated": False}
        visible_evidence, references = prepare_evidence(evidence)
        provider = completion_provider(self.store.settings())
        try:
            claims = generate_claims(provider, question, visible_evidence, question_language(question))
        except AnswerLanguageError as exc:
            return {"claims": [], "citations": [], "message": str(exc),
                    "mode": result["mode"], "validated": False}
        allowed = {e["id"]: e for e in evidence}
        if not claims:
            return {"claims": [], "citations": [], "message": "Модель не смогла обосновать ответ источниками.",
                    "mode": result["mode"], "validated": False}
        claims = verify_claims(provider, question, claims, visible_evidence)
        claims = [{**c, "evidence_ids": [references[label]["id"] for label in c["evidence_ids"]]}
                  for c in claims]
        used = list(dict.fromkeys(i for c in claims for i in c["evidence_ids"]))
        citations = [{**allowed[i], "number": n} for n, i in enumerate(used, 1)]
        self.store.audit("answer.validated", notebook, {"accepted_claims": len(claims), "citations": used})
        return {"claims": claims, "citations": citations, "mode": result["mode"],
                "validated": bool(claims), "message": "" if claims else "Проверка не подтвердила ответ. Уточните вопрос или добавьте источники."}

    @notebook_operation
    def research(self, notebook: str, question: str) -> dict:
        language = question_language(question)
        session = {"id": uid(), "question": question, "language": language,
                   "created_at": now(), "steps": [], "status": "running"}
        path = self.store.notebook_path(notebook) / "research" / (session["id"] + ".json")
        write_json(path, session)
        try:
            planner = completion_provider(self.store.settings()).complete(
                'Plan research over the user\'s documents. Return JSON {"queries": [up to 4 specific search queries]} '
                'No external knowledge or browsing. ' + language_instruction(language),
                {"question": question, "answer_language": language})
            queries = [question] + [q[:1000] for q in planner.get("queries", []) if isinstance(q, str)][:4]
            session["steps"].append({"stage": "planner", "queries": queries})
            evidence = {}
            for query in queries:
                found = self.search(notebook, query, 5)["evidence"]
                evidence.update({e["id"]: e for e in found})
                session["steps"].append({"stage": "retrieval", "query": query, "count": len(found)})
            answer = self.answer(notebook, question, list(evidence.values())[:16])
            session["steps"].append({"stage": "critic", "accepted": answer["validated"]})
            if not answer["validated"]:
                found = self.search(notebook, question, 16)["evidence"]
                answer = self.answer(notebook, question, found)
                session["steps"].append({"stage": "revision", "accepted": answer["validated"]})
            session.update(status="completed", answer=answer)
        except Exception:
            session.update(status="failed")
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
