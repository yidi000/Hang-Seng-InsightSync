from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings
from insightsync.backend.services.copilot_retrieval import (
    RetrievalPlan,
    RetrievalRequest,
    build_retrieval_plan,
)
from insightsync.backend.services.embedding_service import vector_literal


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _extract_evidence_ids(value: Any) -> list[str]:
    parsed = _json_field(value, [])
    if not isinstance(parsed, list):
        return []
    evidence_ids: list[str] = []
    for item in parsed:
        if isinstance(item, str):
            evidence_ids.append(item)
        elif isinstance(item, dict):
            evidence_id = item.get("evidence_id") or item.get("evidenceId")
            if isinstance(evidence_id, str):
                evidence_ids.append(evidence_id)
    return evidence_ids


class CopilotService:
    """Prospect-aware Copilot backed by curated evidence and an OpenAI-compatible chat model."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = OpenAIProvider(settings)

    def chat(self, *, message: str, conversation_id: str | None, context: str, filters: dict[str, Any], top_k: int) -> dict[str, Any]:
        conversation_id = conversation_id or f"conv_{uuid4().hex}"
        prospect_id = filters.get("prospect_id")
        self._ensure_conversation(conversation_id=conversation_id, context=context, prospect_id=prospect_id, title=message[:120])
        user_message_id = f"msg_{uuid4().hex}"
        self._insert_message(
            message_id=user_message_id,
            conversation_id=conversation_id,
            role="user",
            content=message,
            status="ok",
            structured=None,
            suggested_actions=[],
        )
        evidence = self.retrieve_evidence(message=message, context=context, filters=filters, top_k=top_k)
        if not evidence:
            assistant_message_id = f"msg_{uuid4().hex}"
            answer = "Insufficient evidence was retrieved for this question."
            self._insert_message(
                message_id=assistant_message_id,
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                status="insufficient_evidence",
                structured=None,
                suggested_actions=[],
            )
            return {
                "answer": answer,
                "status": "insufficient_evidence",
                "conversation_id": conversation_id,
                "message_id": assistant_message_id,
                "citations": [],
                "suggested_actions": [],
                "structured_insight": None,
            }

        payload = {
            "message": message,
            "context": context,
            "filters": filters,
            "evidence": evidence,
            "rules": [
                "Use only supplied evidence.",
                "Every conclusion must cite at least one evidence_id.",
                "Return JSON only.",
            ],
        }
        output = self.provider.generate_structured_json(
            system="You are a commercial banking prospecting Copilot. Answer with evidence-grounded JSON for RM workflows.",
            payload=payload,
        )
        citations = self._validate_citations(output, evidence)
        status = "ok" if citations else "insufficient_evidence"
        answer = output.get("answer") or output.get("summary") or output.get("title") or ""
        if status != "ok":
            answer = "The generated output did not cite retrieved evidence."
            output = None
        suggested_actions = (output or {}).get("suggested_actions") or (output or {}).get("suggestedActions") or []
        assistant_message_id = f"msg_{uuid4().hex}"
        self._insert_message(
            message_id=assistant_message_id,
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            status=status,
            structured=output,
            suggested_actions=suggested_actions,
        )
        self._insert_citations(message_id=assistant_message_id, citations=citations)
        return {
            "answer": answer,
            "status": status,
            "conversation_id": conversation_id,
            "message_id": assistant_message_id,
            "citations": citations,
            "suggested_actions": suggested_actions,
            "structured_insight": output,
        }

    def retrieve_evidence(self, *, message: str, context: str, filters: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        plan = build_retrieval_plan(RetrievalRequest(message=message, context=context, filters=filters, top_k=top_k))
        structured = self._retrieve_structured_evidence(plan)
        vector = self._retrieve_vector_evidence(plan) if plan.use_vector else []
        return self._dedupe_evidence([*structured, *vector], limit=plan.top_k)

    def _retrieve_structured_evidence(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        source_batches: list[list[dict[str, Any]]] = []
        for source in plan.sql_sources:
            if source == "market_opportunity_snapshots":
                source_batches.append(self._retrieve_market_opportunity_snapshots(plan))
                continue
            if source == "prospect_signals":
                signal_evidence, linked_evidence_ids = self._retrieve_prospect_signals(plan)
                source_batches.append(signal_evidence)
                if linked_evidence_ids:
                    source_batches.append(self._retrieve_evidence_items_by_ids(linked_evidence_ids, plan=plan))
                continue
            if source == "prospect_scores":
                source_batches.append(self._retrieve_prospect_scores(plan))
                continue
            if source == "client_one_view_timeline":
                source_batches.append(self._retrieve_client_timeline(plan))
                continue
            if source == "prospect_evidence_items":
                source_batches.append(self._retrieve_prospect_evidence_items(plan))
        return self._merge_source_evidence(source_batches, limit=plan.top_k)

    def _merge_source_evidence(self, source_batches: list[list[dict[str, Any]]], *, limit: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        max_length = max((len(batch) for batch in source_batches), default=0)
        for idx in range(max_length):
            for batch in source_batches:
                if idx >= len(batch):
                    continue
                item = batch[idx]
                evidence_id = item.get("evidence_id")
                if not evidence_id or evidence_id in seen:
                    continue
                seen.add(evidence_id)
                out.append(item)
                if len(out) >= limit:
                    return out
        return out

    def _retrieve_prospect_evidence_items(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": plan.top_k}
        clauses = ["1=1"]
        filters = plan.required_filters
        self._add_prospect_evidence_filters(clauses=clauses, params=params, filters=filters)
        if filters.get("signal_type"):
            clauses.append("(pei.evidence_type = :signal_type OR pei.metadata_json->>'signal_type' = :signal_type)")
            params["signal_type"] = filters["signal_type"]
        if filters.get("signal_subtype"):
            clauses.append("pei.metadata_json->>'signal_subtype' = :signal_subtype")
            params["signal_subtype"] = filters["signal_subtype"]

        terms = [term.lower() for term in plan.message.split() if len(term) >= 3][:6]
        score_parts: list[str] = []
        if terms:
            term_clauses: list[str] = []
            for idx, term in enumerate(terms):
                key = f"term_{idx}"
                params[key] = f"%{term}%"
                term_clauses.append(f"LOWER(COALESCE(pei.title, '') || ' ' || COALESCE(pei.summary, '')) LIKE :{key}")
                score_parts.append(f"CASE WHEN LOWER(COALESCE(pei.title, '') || ' ' || COALESCE(pei.summary, '')) LIKE :{key} THEN 1 ELSE 0 END")
            clauses.append("(" + " OR ".join(term_clauses) + ")")
        score_sql = " + ".join(score_parts) if score_parts else "1"
        rows = self.db.execute(
            text(
                f"""
                SELECT pei.evidence_id, pei.title, pei.summary, pei.source, pei.dataset, pei.event_time,
                       pei.url, pei.prospect_id, pei.evidence_type,
                       ({score_sql})::float AS score
                FROM prospect_evidence_items pei
                LEFT JOIN prospects p ON p.prospect_id = pei.prospect_id
                WHERE {' AND '.join(clauses)}
                ORDER BY score DESC, pei.event_time DESC NULLS LAST, pei.id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [self._evidence_payload(row) for row in rows]

    def _retrieve_prospect_signals(self, plan: RetrievalPlan) -> tuple[list[dict[str, Any]], list[str]]:
        params: dict[str, Any] = {"limit": plan.top_k}
        clauses = ["1=1"]
        filters = plan.required_filters
        if filters.get("prospect_id"):
            clauses.append("ps.prospect_id = :prospect_id")
            params["prospect_id"] = filters["prospect_id"]
        if filters.get("company_id"):
            clauses.append("ps.company_id = :company_id")
            params["company_id"] = filters["company_id"]
        if filters.get("source"):
            clauses.append("ps.metadata_json->>'source' = :source")
            params["source"] = filters["source"]
        if filters.get("dataset"):
            clauses.append("ps.metadata_json->>'dataset' = :dataset")
            params["dataset"] = filters["dataset"]
        if filters.get("signal_type"):
            clauses.append("ps.signal_type = :signal_type")
            params["signal_type"] = filters["signal_type"]
        if filters.get("signal_subtype"):
            clauses.append("ps.signal_subtype = :signal_subtype")
            params["signal_subtype"] = filters["signal_subtype"]
        if filters.get("date_from"):
            clauses.append("ps.event_time >= :date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            clauses.append("ps.event_time <= :date_to")
            params["date_to"] = filters["date_to"]
        if filters.get("industry"):
            clauses.append("p.industry = :industry")
            params["industry"] = filters["industry"]
        if filters.get("region"):
            clauses.append("p.region = :region")
            params["region"] = filters["region"]
        if filters.get("size_band"):
            clauses.append("p.size_band = :size_band")
            params["size_band"] = filters["size_band"]

        rows = self.db.execute(
            text(
                f"""
                SELECT ps.signal_id, ps.prospect_id, ps.company_id, ps.signal_type, ps.signal_subtype,
                       ps.signal_level, ps.signal_score, ps.event_time, ps.signal_text,
                       ps.evidence_ids_json,
                       COALESCE(ps.signal_score, 0)::float AS score
                FROM prospect_signals ps
                LEFT JOIN prospects p ON p.prospect_id = ps.prospect_id
                WHERE {' AND '.join(clauses)}
                ORDER BY ps.signal_score DESC NULLS LAST, ps.event_time DESC NULLS LAST, ps.id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

        linked_evidence_ids: list[str] = []
        evidence: list[dict[str, Any]] = []
        for row in rows:
            linked_evidence_ids.extend(_extract_evidence_ids(row.get("evidence_ids_json")))
            evidence.append(self._signal_payload(row))
        return evidence, linked_evidence_ids

    def _retrieve_evidence_items_by_ids(self, evidence_ids: list[str], *, plan: RetrievalPlan) -> list[dict[str, Any]]:
        unique_ids = list(dict.fromkeys(evidence_ids))
        if not unique_ids:
            return []
        params: dict[str, Any] = {"evidence_ids": unique_ids, "limit": plan.top_k}
        clauses = ["pei.evidence_id = ANY(:evidence_ids)"]
        self._add_prospect_evidence_filters(clauses=clauses, params=params, filters=plan.required_filters)
        rows = self.db.execute(
            text(
                f"""
                SELECT pei.evidence_id, pei.title, pei.summary, pei.source, pei.dataset, pei.event_time,
                       pei.url, pei.prospect_id, pei.evidence_type,
                       1::float AS score
                FROM prospect_evidence_items pei
                LEFT JOIN prospects p ON p.prospect_id = pei.prospect_id
                WHERE {' AND '.join(clauses)}
                ORDER BY pei.event_time DESC NULLS LAST, pei.id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [self._evidence_payload(row) for row in rows]

    def _add_prospect_evidence_filters(
        self,
        *,
        clauses: list[str],
        params: dict[str, Any],
        filters: dict[str, Any],
    ) -> None:
        if filters.get("prospect_id"):
            clauses.append("pei.prospect_id = :prospect_id")
            params["prospect_id"] = filters["prospect_id"]
        if filters.get("company_id"):
            clauses.append("pei.company_id = :company_id")
            params["company_id"] = filters["company_id"]
        if filters.get("source"):
            clauses.append("pei.source = :source")
            params["source"] = filters["source"]
        if filters.get("dataset"):
            clauses.append("pei.dataset = :dataset")
            params["dataset"] = filters["dataset"]
        if filters.get("date_from"):
            clauses.append("pei.event_time >= :date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            clauses.append("pei.event_time <= :date_to")
            params["date_to"] = filters["date_to"]
        if filters.get("industry"):
            clauses.append("p.industry = :industry")
            params["industry"] = filters["industry"]
        if filters.get("region"):
            clauses.append("p.region = :region")
            params["region"] = filters["region"]
        if filters.get("size_band"):
            clauses.append("p.size_band = :size_band")
            params["size_band"] = filters["size_band"]

    def _retrieve_market_opportunity_snapshots(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": plan.top_k}
        clauses = ["1=1"]
        filters = plan.required_filters
        if filters.get("source") or filters.get("dataset"):
            return []
        if filters.get("region"):
            clauses.append("mos.region = :region")
            params["region"] = filters["region"]
        if filters.get("industry"):
            clauses.append("mos.industry = :industry")
            params["industry"] = filters["industry"]
        if filters.get("size_band"):
            clauses.append("mos.size_band = :size_band")
            params["size_band"] = filters["size_band"]
        if filters.get("signal_type"):
            clauses.append("mos.signal_type = :signal_type")
            params["signal_type"] = filters["signal_type"]
        if filters.get("date_from"):
            clauses.append("mos.snapshot_date >= :date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            clauses.append("mos.snapshot_date <= :date_to")
            params["date_to"] = filters["date_to"]

        rows = self.db.execute(
            text(
                f"""
                SELECT mos.id, mos.snapshot_date, mos.region, mos.industry, mos.size_band,
                       mos.signal_type, mos.lead_count, mos.signal_count, mos.avg_score,
                       mos.trend_summary,
                       COALESCE(mos.avg_score, mos.signal_count, 0)::float AS score
                FROM market_opportunity_snapshots mos
                WHERE {' AND '.join(clauses)}
                ORDER BY mos.snapshot_date DESC NULLS LAST, mos.avg_score DESC NULLS LAST, mos.id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [self._market_payload(row) for row in rows]

    def _retrieve_prospect_scores(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        filters = plan.required_filters
        if filters.get("source") or filters.get("dataset") or filters.get("date_from") or filters.get("date_to"):
            return []
        params: dict[str, Any] = {"limit": plan.top_k}
        clauses = ["1=1"]
        if filters.get("prospect_id"):
            clauses.append("ps.prospect_id = :prospect_id")
            params["prospect_id"] = filters["prospect_id"]
        if filters.get("company_id"):
            clauses.append("ps.company_id = :company_id")
            params["company_id"] = filters["company_id"]
        if filters.get("industry"):
            clauses.append("p.industry = :industry")
            params["industry"] = filters["industry"]
        if filters.get("region"):
            clauses.append("p.region = :region")
            params["region"] = filters["region"]
        if filters.get("size_band"):
            clauses.append("p.size_band = :size_band")
            params["size_band"] = filters["size_band"]

        rows = self.db.execute(
            text(
                f"""
                SELECT ps.prospect_id, ps.company_id, ps.score, ps.tier, ps.reasons_json,
                       ps.recommended_products_json, ps.recommended_entry_angle, ps.updated_at
                FROM prospect_scores ps
                LEFT JOIN prospects p ON p.prospect_id = ps.prospect_id
                WHERE {' AND '.join(clauses)}
                ORDER BY ps.score DESC, ps.updated_at DESC NULLS LAST
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [self._score_payload(row) for row in rows]

    def _retrieve_client_timeline(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        filters = plan.required_filters
        if filters.get("dataset"):
            return []
        params: dict[str, Any] = {"limit": plan.top_k}
        clauses = ["1=1"]
        if filters.get("source"):
            clauses.append("cot.source = :source")
            params["source"] = filters["source"]
        if filters.get("company_id"):
            clauses.append("cot.company_id = :company_id")
            params["company_id"] = filters["company_id"]
        if filters.get("prospect_id"):
            clauses.append("p.prospect_id = :prospect_id")
            params["prospect_id"] = filters["prospect_id"]
        if filters.get("date_from"):
            clauses.append("cot.event_time >= :date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            clauses.append("cot.event_time <= :date_to")
            params["date_to"] = filters["date_to"]
        if filters.get("industry"):
            clauses.append("p.industry = :industry")
            params["industry"] = filters["industry"]
        if filters.get("region"):
            clauses.append("p.region = :region")
            params["region"] = filters["region"]
        if filters.get("size_band"):
            clauses.append("p.size_band = :size_band")
            params["size_band"] = filters["size_band"]

        rows = self.db.execute(
            text(
                f"""
                SELECT cot.id, cot.source, cot.company_id, cot.entity, cot.event_time, cot.event_type,
                       cot.headline, cot.detail, cot.evidence_url,
                       1::float AS score
                FROM client_one_view_timeline cot
                LEFT JOIN prospects p
                  ON p.company_id = cot.company_id
                  OR p.display_name = cot.entity
                  OR p.canonical_name = cot.entity
                WHERE {' AND '.join(clauses)}
                ORDER BY cot.event_time DESC NULLS LAST, cot.id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [self._timeline_payload(row) for row in rows]

    def _retrieve_vector_evidence(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        query_embedding = OpenAIProvider(self.settings).embed_texts([plan.message])[0]
        params: dict[str, Any] = {
            "query_embedding": vector_literal(query_embedding),
            "model": self.settings.openai_embedding_model,
            "limit": plan.top_k * 5,
        }
        clauses = ["re.embedding_model = :model"]
        filters = plan.required_filters
        if filters.get("prospect_id"):
            clauses.append("pei.prospect_id = :prospect_id")
            params["prospect_id"] = filters["prospect_id"]
        if filters.get("company_id"):
            clauses.append("pei.company_id = :company_id")
            params["company_id"] = filters["company_id"]
        if filters.get("source"):
            clauses.append("pei.source = :source")
            params["source"] = filters["source"]
        if filters.get("dataset"):
            clauses.append("pei.dataset = :dataset")
            params["dataset"] = filters["dataset"]
        if filters.get("date_from"):
            clauses.append("pei.event_time >= :date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            clauses.append("pei.event_time <= :date_to")
            params["date_to"] = filters["date_to"]
        if filters.get("industry"):
            clauses.append("rd.industry = :industry")
            params["industry"] = filters["industry"]
        if filters.get("region"):
            clauses.append("rd.region = :region")
            params["region"] = filters["region"]
        if filters.get("signal_type"):
            clauses.append("(pei.evidence_type = :signal_type OR rd.signal_type = :signal_type)")
            params["signal_type"] = filters["signal_type"]
        if filters.get("signal_subtype"):
            clauses.append("rd.metadata_json->>'signal_subtype' = :signal_subtype")
            params["signal_subtype"] = filters["signal_subtype"]
        if filters.get("size_band"):
            clauses.append("rd.metadata_json->>'size_band' = :size_band")
            params["size_band"] = filters["size_band"]

        rows = self.db.execute(
            text(
                f"""
                SELECT pei.evidence_id, pei.title, pei.summary, pei.source, pei.dataset, pei.event_time,
                       pei.url, pei.prospect_id, pei.evidence_type,
                       1 - (re.embedding <=> CAST(:query_embedding AS vector)) AS score
                FROM rag_documents rd
                JOIN rag_chunks rc ON rc.document_id = rd.id
                JOIN rag_embeddings re ON re.chunk_id = rc.id
                JOIN prospect_evidence_items pei
                  ON rd.source_table = 'prospect_evidence_items'
                 AND rd.source_id = pei.id
                WHERE {' AND '.join(clauses)}
                ORDER BY re.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return self._dedupe_evidence([self._evidence_payload(row) for row in rows], limit=plan.top_k)

    def _dedupe_evidence(self, evidence: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in evidence:
            evidence_id = item.get("evidence_id")
            if not evidence_id or evidence_id in seen:
                continue
            seen.add(evidence_id)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def _evidence_payload(self, row: Any) -> dict[str, Any]:
        return {
            "evidence_id": row["evidence_id"],
            "title": row["title"],
            "text": row.get("summary") or row.get("title"),
            "summary": row.get("summary"),
            "source": row.get("source"),
            "dataset": row.get("dataset"),
            "event_time": row.get("event_time"),
            "url": row.get("url"),
            "prospect_id": row.get("prospect_id"),
            "evidence_type": row.get("evidence_type"),
            "score": float(row.get("score") or 0),
        }

    def _signal_payload(self, row: Any) -> dict[str, Any]:
        signal_subtype = row.get("signal_subtype") or row.get("signal_type") or "signal"
        signal_text = row.get("signal_text") or ""
        title = f"{signal_subtype} signal"
        summary = signal_text
        if row.get("signal_level"):
            summary = f"{signal_text} Signal level: {row.get('signal_level')}"
        return {
            "evidence_id": f"signal:{row['signal_id']}",
            "title": title,
            "text": summary,
            "summary": summary,
            "source": "prospect_signals",
            "dataset": "curated",
            "event_time": row.get("event_time"),
            "url": None,
            "prospect_id": row.get("prospect_id"),
            "evidence_type": "signal",
            "signal_subtype": row.get("signal_subtype"),
            "score": float(row.get("score") or 0),
        }

    def _market_payload(self, row: Any) -> dict[str, Any]:
        region = row.get("region") or "All regions"
        industry = row.get("industry") or "all industries"
        signal_type = row.get("signal_type") or "all signals"
        trend_summary = row.get("trend_summary") or "No trend summary available."
        summary = (
            f"{trend_summary} Leads: {row.get('lead_count') or 0}; "
            f"signals: {row.get('signal_count') or 0}; average score: {row.get('avg_score') or 0}."
        )
        return {
            "evidence_id": f"market:{row['id']}",
            "title": f"{region} {industry} opportunity snapshot",
            "text": summary,
            "summary": summary,
            "source": "market_opportunity_snapshots",
            "dataset": "curated",
            "event_time": row.get("snapshot_date"),
            "url": None,
            "prospect_id": None,
            "evidence_type": "market_opportunity_snapshot",
            "signal_subtype": signal_type,
            "score": float(row.get("score") or 0),
        }

    def _score_payload(self, row: Any) -> dict[str, Any]:
        reasons = _json_field(row.get("reasons_json"), [])
        products = _json_field(row.get("recommended_products_json"), [])
        reasons_text = ", ".join(str(item) for item in reasons) if isinstance(reasons, list) else str(reasons)
        products_text = ", ".join(str(item) for item in products) if isinstance(products, list) else str(products)
        summary = (
            f"Score: {row.get('score')}; tier: {row.get('tier')}. "
            f"Reasons: {reasons_text or 'none listed'}. "
            f"Recommended products: {products_text or 'none listed'}. "
            f"Entry angle: {row.get('recommended_entry_angle') or 'none listed'}."
        )
        return {
            "evidence_id": f"score:{row['prospect_id']}",
            "title": f"Prospect score {row.get('tier')}",
            "text": summary,
            "summary": summary,
            "source": "prospect_scores",
            "dataset": "curated",
            "event_time": row.get("updated_at"),
            "url": None,
            "prospect_id": row.get("prospect_id"),
            "evidence_type": "prospect_score",
            "score": float(row.get("score") or 0),
        }

    def _timeline_payload(self, row: Any) -> dict[str, Any]:
        summary = f"{row.get('headline')}. {row.get('detail') or ''}".strip()
        return {
            "evidence_id": f"timeline:{row['id']}",
            "title": row.get("headline"),
            "text": summary,
            "summary": summary,
            "source": row.get("source") or "client_one_view_timeline",
            "dataset": "client_one_view_timeline",
            "event_time": row.get("event_time"),
            "url": row.get("evidence_url"),
            "prospect_id": None,
            "evidence_type": row.get("event_type") or "timeline",
            "score": float(row.get("score") or 0),
        }

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        conversation = self.db.execute(
            text(
                """
                SELECT conversation_id, context, prospect_id, title
                FROM copilot_conversations
                WHERE conversation_id = :conversation_id
                """
            ),
            {"conversation_id": conversation_id},
        ).mappings().first()
        if not conversation:
            return None
        messages = self.db.execute(
            text(
                """
                SELECT message_id, role, content, status, created_at
                FROM copilot_messages
                WHERE conversation_id = :conversation_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"conversation_id": conversation_id},
        ).mappings().all()
        citations_by_message = self._citations_by_message([row["message_id"] for row in messages])
        return {
            **dict(conversation),
            "messages": [
                {**dict(row), "citations": citations_by_message.get(row["message_id"], [])}
                for row in messages
            ],
        }

    def prospect_brief(self, prospect_id: str) -> dict[str, Any]:
        return self.chat(
            message="Create a concise RM outreach brief with likely needs, product fit, and recommended entry angle.",
            conversation_id=None,
            context="prospect",
            filters={"prospect_id": prospect_id},
            top_k=8,
        )

    def suggested_questions(self, prospect_id: str) -> list[str]:
        return [
            "What recent signals make this prospect actionable?",
            "What product fit is supported by the evidence?",
            "What should the RM say in the first outreach?",
            "What risks or caveats should be reviewed before contacting this company?",
        ]

    def _validate_citations(self, output: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        allowed = {item["evidence_id"]: item for item in evidence}
        raw = output.get("citations") or output.get("evidence") or []
        citations: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            evidence_id = item.get("evidence_id") or item.get("evidenceId")
            if evidence_id not in allowed:
                continue
            source = allowed[evidence_id]
            citations.append(
                {
                    "evidence_id": evidence_id,
                    "title": source.get("title"),
                    "source": source.get("source"),
                    "dataset": source.get("dataset"),
                    "event_time": source.get("event_time"),
                    "url": source.get("url"),
                    "snippet": (source.get("summary") or source.get("text") or "")[:500],
                }
            )
        return citations

    def _ensure_conversation(self, *, conversation_id: str, context: str, prospect_id: str | None, title: str) -> None:
        now = datetime.now(timezone.utc)
        self.db.execute(
            text(
                """
                INSERT INTO copilot_conversations (conversation_id, context, prospect_id, title, created_at, updated_at)
                VALUES (:conversation_id, :context, :prospect_id, :title, :now, :now)
                ON CONFLICT (conversation_id) DO UPDATE SET updated_at = EXCLUDED.updated_at
                """
            ),
            {"conversation_id": conversation_id, "context": context, "prospect_id": prospect_id, "title": title, "now": now},
        )

    def _insert_message(
        self,
        *,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        status: str,
        structured: dict[str, Any] | None,
        suggested_actions: list[str],
    ) -> None:
        self.db.execute(
            text(
                """
                INSERT INTO copilot_messages (
                  message_id, conversation_id, role, content, status, structured_insight_json,
                  suggested_actions_json, created_at
                )
                VALUES (
                  :message_id, :conversation_id, :role, :content, :status, CAST(:structured AS jsonb),
                  CAST(:suggested_actions AS jsonb), :created_at
                )
                """
            ),
            {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "status": status,
                "structured": _json_dumps(structured) if structured is not None else "null",
                "suggested_actions": _json_dumps(suggested_actions),
                "created_at": datetime.now(timezone.utc),
            },
        )

    def _insert_citations(self, *, message_id: str, citations: list[dict[str, Any]]) -> None:
        for item in citations:
            self.db.execute(
                text(
                    """
                    INSERT INTO copilot_citations (
                      message_id, evidence_id, title, source, dataset, event_time, url, snippet, metadata_json
                    )
                    VALUES (
                      :message_id, :evidence_id, :title, :source, :dataset, :event_time, :url, :snippet,
                      CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "message_id": message_id,
                    "evidence_id": item.get("evidence_id"),
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "dataset": item.get("dataset"),
                    "event_time": item.get("event_time"),
                    "url": item.get("url"),
                    "snippet": item.get("snippet"),
                    "metadata": _json_dumps({}),
                },
            )

    def _citations_by_message(self, message_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for message_id in message_ids:
            rows = self.db.execute(
                text(
                    """
                    SELECT message_id, evidence_id, chunk_id, document_id, title, source, dataset, event_time, url, snippet
                    FROM copilot_citations
                    WHERE message_id = :message_id
                    ORDER BY id ASC
                    """
                ),
                {"message_id": message_id},
            ).mappings().all()
            out[message_id] = [dict(row) for row in rows]
        return out
