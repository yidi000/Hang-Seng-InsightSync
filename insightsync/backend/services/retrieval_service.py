from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings
from insightsync.backend.services.chunker import extract_query_terms
from insightsync.backend.services.embedding_service import vector_literal


class RetrievalService:
    """Retrieve evidence chunks using metadata filters and pgvector similarity."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = OpenAIProvider(settings)

    def retrieve(self, *, question: str, filters: dict[str, Any], top_k: int | None = None) -> dict[str, Any]:
        """Return ranked evidence chunks for a question."""

        limit = top_k or self.settings.rag_top_k
        if self.settings.embedding_provider == "fallback" or not self.settings.openai_api_key:
            evidence = self._retrieve_lexical(question=question, filters=filters, limit=limit)
            run_id = self._record_retrieval(question=question, filters=filters, top_k=limit, evidence=evidence)
            return {"retrieval_run_id": run_id, "evidence": evidence}

        query_embedding = self.provider.embed_texts([question])[0]
        params: dict[str, Any] = {
            "query_embedding": vector_literal(query_embedding),
            "model": self.settings.openai_embedding_model,
            "limit": limit,
        }
        clauses = ["e.embedding_model = :model"]
        for key in ("entity", "company_id", "signal_type", "source", "dataset"):
            value = filters.get(key)
            if value:
                clauses.append(f"d.{key} = :{key}")
                params[key] = value
        if filters.get("date_from"):
            clauses.append("d.event_time >= :date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            clauses.append("d.event_time <= :date_to")
            params["date_to"] = filters["date_to"]

        where_sql = " AND ".join(clauses)
        rows = self.db.execute(
            text(
                f"""
                SELECT c.id AS chunk_id, c.document_id, c.chunk_text, d.source, d.dataset, d.record_key,
                       d.signal_key, d.entity, d.company_id, d.event_time, d.evidence_url,
                       1 - (e.embedding <=> CAST(:query_embedding AS vector)) AS score
                FROM rag_embeddings e
                JOIN rag_chunks c ON c.id = e.chunk_id
                JOIN rag_documents d ON d.id = c.document_id
                WHERE {where_sql}
                ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        evidence = [dict(row) for row in rows if float(row["score"]) >= self.settings.rag_min_score]
        run_id = self._record_retrieval(question=question, filters=filters, top_k=limit, evidence=evidence)
        return {"retrieval_run_id": run_id, "evidence": evidence}

    def _retrieve_lexical(self, *, question: str, filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        terms = extract_query_terms(question)
        if not terms:
            return []

        params: dict[str, Any] = {"limit": limit}
        clauses = ["1=1"]
        for key in ("entity", "company_id", "signal_type", "source", "dataset"):
            value = filters.get(key)
            if value:
                clauses.append(f"d.{key} = :{key}")
                params[key] = value
        if filters.get("date_from"):
            clauses.append("d.event_time >= :date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            clauses.append("d.event_time <= :date_to")
            params["date_to"] = filters["date_to"]

        term_clauses: list[str] = []
        score_parts: list[str] = []
        for idx, term in enumerate(terms):
            key = f"term_{idx}"
            params[key] = f"%{term}%"
            term_clauses.append(f"LOWER(c.chunk_text) LIKE :{key}")
            score_parts.append(f"CASE WHEN LOWER(c.chunk_text) LIKE :{key} THEN 1 ELSE 0 END")
        clauses.append("(" + " OR ".join(term_clauses) + ")")
        score_sql = " + ".join(score_parts)

        rows = self.db.execute(
            text(
                f"""
                SELECT c.id AS chunk_id, c.document_id, c.chunk_text, d.source, d.dataset, d.record_key,
                       d.signal_key, d.entity, d.company_id, d.event_time, d.evidence_url,
                       ({score_sql})::float / :term_count AS score
                FROM rag_chunks c
                JOIN rag_documents d ON d.id = c.document_id
                WHERE {' AND '.join(clauses)}
                ORDER BY score DESC, c.id DESC
                LIMIT :limit
                """
            ),
            {**params, "term_count": max(1, len(terms))},
        ).mappings().all()
        return [dict(row) for row in rows if float(row["score"]) > 0]

    def _record_retrieval(self, *, question: str, filters: dict[str, Any], top_k: int, evidence: list[dict[str, Any]]) -> int:
        result = self.db.execute(
            text(
                """
                INSERT INTO rag_retrieval_runs (question, filters_json, top_k, results_json)
                VALUES (:question, CAST(:filters AS jsonb), :top_k, CAST(:results AS jsonb))
                RETURNING id
                """
            ),
            {
                "question": question,
                "filters": _json_dumps(filters),
                "top_k": top_k,
                "results": _json_dumps(_json_safe(evidence)),
            },
        )
        return int(result.scalar_one())


def _json_safe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in row.items() if key != "chunk_text"} for row in rows]


def _json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)
