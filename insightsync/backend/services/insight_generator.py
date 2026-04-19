from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings
from insightsync.backend.services.retrieval_service import RetrievalService
from datetime import datetime, timezone

from insightsync.backend.utils import stable_hash

PROMPT_VERSION = "rag-trusted-v1"


class InsightGenerator:
    """Generate evidence-grounded insights from retrieved RAG chunks."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.retrieval = RetrievalService(db, settings)
        self.provider = OpenAIProvider(settings)

    def answer_question(
        self,
        *,
        question: str,
        filters: dict[str, Any],
        top_k: int | None = None,
        insight_type: str = "explanation",
    ) -> dict[str, Any]:
        """Retrieve evidence and generate a trusted response."""

        retrieval = self.retrieval.retrieve(question=question, filters=filters, top_k=top_k)
        evidence = retrieval["evidence"]
        if not evidence:
            return {
                "status": "insufficient_evidence",
                "answer": "Insufficient evidence was retrieved for this question.",
                "retrieval_run_id": retrieval["retrieval_run_id"],
                "citations": [],
                "structured_insight": None,
            }

        evidence_payload = [
            {
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "source": item["source"],
                "dataset": item["dataset"],
                "record_key": item["record_key"],
                "signal_key": item["signal_key"],
                "score": float(item["score"]),
                "text": item["chunk_text"],
            }
            for item in evidence
        ]
        output = self.provider.generate_json(question=question, evidence=evidence_payload, insight_type=insight_type)
        citations = self._validate_citations(output, evidence)
        status = "ok" if citations else "insufficient_evidence"
        self._record_generation(
            retrieval_run_id=retrieval["retrieval_run_id"],
            status=status,
            question=question,
            evidence=evidence_payload,
            output=output,
        )
        if status != "ok":
            return {
                "status": status,
                "answer": "The generated output did not cite retrieved evidence.",
                "retrieval_run_id": retrieval["retrieval_run_id"],
                "citations": [],
                "structured_insight": None,
            }
        return {
            "status": "ok",
            "answer": output.get("summary") or output.get("answer") or output.get("title") or "",
            "retrieval_run_id": retrieval["retrieval_run_id"],
            "citations": citations,
            "structured_insight": output,
        }

    def persist_generated_insight(self, result: dict[str, Any], *, entity: str | None = None, company_id: str | None = None) -> None:
        """Persist a generated insight when it has validated citations."""

        insight = result.get("structured_insight")
        citations = result.get("citations") or []
        if result.get("status") != "ok" or not insight or not citations:
            return
        record_keys = [item.get("record_key") for item in citations if item.get("record_key")]
        signal_keys = [item.get("signal_key") for item in citations if item.get("signal_key")]
        dedup_hash = stable_hash({"insight": insight, "citations": citations})
        self.db.execute(
            text(
                """
                INSERT INTO generated_insights (
                  source, company_id, entity, insight_type, title, summary, confidence,
                  evidence_record_keys_json, evidence_signal_keys_json, model_name, model_version,
                  prompt_version, meta_json, generated_at, run_id, dedup_hash
                )
                VALUES (
                  'rag', :company_id, :entity, :insight_type, :title, :summary, :confidence,
                  CAST(:record_keys AS jsonb), CAST(:signal_keys AS jsonb), :model_name, :model_version,
                  :prompt_version, CAST(:meta AS jsonb), :generated_at, :run_id, :dedup_hash
                )
                ON CONFLICT (dedup_hash) DO NOTHING
                """
            ),
            {
                "company_id": company_id,
                "entity": entity,
                "insight_type": insight.get("insight_type", "explanation"),
                "title": insight.get("title", "Generated insight"),
                "summary": insight.get("summary", ""),
                "confidence": insight.get("confidence"),
                "record_keys": json.dumps(record_keys, ensure_ascii=False),
                "signal_keys": json.dumps(signal_keys, ensure_ascii=False),
                "model_name": self.settings.openai_chat_model,
                "model_version": None,
                "prompt_version": PROMPT_VERSION,
                "meta": json.dumps({"citations": citations, "retrieval_run_id": result.get("retrieval_run_id")}, ensure_ascii=False),
                "generated_at": datetime.now(timezone.utc),
                "run_id": f"rag-{result.get('retrieval_run_id')}",
                "dedup_hash": dedup_hash,
            },
        )

    def _validate_citations(self, output: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        allowed = {int(item["chunk_id"]): item for item in evidence}
        raw_citations = output.get("citations") or output.get("evidence") or []
        citations: list[dict[str, Any]] = []
        for citation in raw_citations:
            chunk_id = citation.get("chunk_id") if isinstance(citation, dict) else None
            if chunk_id is None:
                continue
            try:
                chunk_id_int = int(chunk_id)
            except (TypeError, ValueError):
                continue
            source = allowed.get(chunk_id_int)
            if not source:
                continue
            citations.append(
                {
                    "chunk_id": chunk_id_int,
                    "document_id": source["document_id"],
                    "score": float(source["score"]),
                    "source": source["source"],
                    "dataset": source.get("dataset"),
                    "record_key": source.get("record_key"),
                    "signal_key": source.get("signal_key"),
                    "evidence_url": source.get("evidence_url"),
                    "text": source.get("chunk_text"),
                }
            )
        return citations

    def _record_generation(
        self,
        *,
        retrieval_run_id: int,
        status: str,
        question: str,
        evidence: list[dict[str, Any]],
        output: dict[str, Any],
    ) -> None:
        self.db.execute(
            text(
                """
                INSERT INTO llm_generation_runs (
                  retrieval_run_id, prompt_version, model_name, input_json, output_json, status
                )
                VALUES (:retrieval_run_id, :prompt_version, :model_name, CAST(:input AS jsonb), CAST(:output AS jsonb), :status)
                """
            ),
            {
                "retrieval_run_id": retrieval_run_id,
                "prompt_version": PROMPT_VERSION,
                "model_name": self.settings.openai_chat_model,
                "input": json.dumps({"question": question, "evidence": evidence}, ensure_ascii=False, default=str),
                "output": json.dumps(output, ensure_ascii=False, default=str),
                "status": status,
            },
        )
