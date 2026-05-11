from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from insightsync.backend.services.genai_extraction_view import build_genai_extraction_view


def _date_filter(column: str, date_from: str | None, date_to: str | None, params: dict[str, Any]) -> list[str]:
    clauses: list[str] = []
    if date_from:
        clauses.append(f"{column} >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append(f"{column} <= :date_to")
        params["date_to"] = date_to
    return clauses


class ReadRepository:
    """Read-only repository for dashboard and core API queries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _json_field(value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, (list, dict)):
            return value
        if not isinstance(value, str):
            return default
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return default
        return parsed

    @staticmethod
    def _int_field(value: Any) -> int:
        if value is None:
            return 0
        return int(value)

    def _hydrate_company_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "segments": self._json_field(row.get("segments_json"), []),
            "industries": self._json_field(row.get("industries_json"), []),
            "extra": self._json_field(row.get("extra_json"), {}),
        }

    def list_signals(
        self,
        *,
        limit: int,
        offset: int,
        company_id: str | None = None,
        entity: str | None = None,
        signal_type: str | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        clauses: list[str] = []
        if company_id:
            clauses.append("company_id = :company_id")
            params["company_id"] = company_id
        if entity:
            clauses.append("entity = :entity")
            params["entity"] = entity
        if signal_type:
            clauses.append("signal_type = :signal_type")
            params["signal_type"] = signal_type
        if source:
            clauses.append("source = :source")
            params["source"] = source
        clauses.extend(_date_filter("event_time", date_from, date_to, params))
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.execute(
            text(
                f"""
                SELECT id, source, dataset, signal_key, signal_type, company_id, entity, event_time,
                       indicator, value_num, value_text, unit, signal_text, signal_score, signal_level,
                       evidence_refs_json, extra_json
                FROM trigger_signals
                {where_sql}
                ORDER BY event_time DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings()
        return [dict(row) for row in rows]

    def list_companies(
        self,
        *,
        limit: int,
        offset: int,
        q: str | None = None,
        region: str | None = None,
        segment: str | None = None,
        industry: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        clauses: list[str] = []
        if q:
            params["q"] = f"%{q.lower()}%"
            clauses.append(
                """
                (
                  LOWER(lc.company_id) LIKE :q
                  OR LOWER(lc.canonical_name) LIKE :q
                  OR LOWER(COALESCE(lc.display_name, '')) LIKE :q
                )
                """
            )
        if region:
            clauses.append("LOWER(COALESCE(lc.region, '')) = :region")
            params["region"] = region.lower()
        if segment:
            clauses.append("LOWER(CAST(lc.segments_json AS TEXT)) LIKE :segment")
            params["segment"] = f"%{segment.lower()}%"
        if industry:
            clauses.append("LOWER(CAST(lc.industries_json AS TEXT)) LIKE :industry")
            params["industry"] = f"%{industry.lower()}%"

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.execute(
            text(
                f"""
                WITH ranked_companies AS (
                  SELECT c.*,
                         ROW_NUMBER() OVER (PARTITION BY c.company_id ORDER BY c.updated_at DESC, c.id DESC) AS rn
                  FROM companies c
                ),
                latest_companies AS (
                  SELECT *
                  FROM ranked_companies
                  WHERE rn = 1
                ),
                signal_counts AS (
                  SELECT company_id,
                         COUNT(*) AS signal_count,
                         MAX(event_time) AS last_signal_at
                  FROM trigger_signals
                  WHERE company_id IS NOT NULL AND TRIM(company_id) <> ''
                  GROUP BY company_id
                ),
                timeline_counts AS (
                  SELECT company_id,
                         COUNT(*) AS timeline_event_count,
                         MAX(event_time) AS last_event_at
                  FROM client_one_view_timeline
                  WHERE company_id IS NOT NULL AND TRIM(company_id) <> ''
                  GROUP BY company_id
                ),
                insight_counts AS (
                  SELECT company_id,
                         COUNT(*) AS generated_insight_count,
                         MAX(generated_at) AS last_insight_at
                  FROM generated_insights
                  WHERE company_id IS NOT NULL AND TRIM(company_id) <> ''
                  GROUP BY company_id
                )
                SELECT lc.source, lc.company_id, lc.canonical_name, lc.display_name,
                       lc.country, lc.region, lc.city, lc.segments_json, lc.industries_json,
                       lc.website_url, lc.linkedin_url, lc.facebook_url, lc.x_url,
                       lc.instagram_url, lc.wikipedia_url, lc.profile_summary,
                       lc.description, lc.extra_json, lc.updated_at,
                       COALESCE(sc.signal_count, 0) AS signal_count,
                       COALESCE(tc.timeline_event_count, 0) AS timeline_event_count,
                       COALESCE(ic.generated_insight_count, 0) AS generated_insight_count,
                       sc.last_signal_at, tc.last_event_at, ic.last_insight_at,
                       COALESCE(sc.last_signal_at, tc.last_event_at, ic.last_insight_at, lc.updated_at) AS activity_at
                FROM latest_companies lc
                LEFT JOIN signal_counts sc ON sc.company_id = lc.company_id
                LEFT JOIN timeline_counts tc ON tc.company_id = lc.company_id
                LEFT JOIN insight_counts ic ON ic.company_id = lc.company_id
                {where_sql}
                ORDER BY
                  (COALESCE(sc.last_signal_at, tc.last_event_at, ic.last_insight_at, lc.updated_at) IS NULL),
                  COALESCE(sc.last_signal_at, tc.last_event_at, ic.last_insight_at, lc.updated_at) DESC,
                  lc.updated_at DESC,
                  lc.company_id ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings()
        return [self._hydrate_company_row(dict(row)) for row in rows]

    def get_company_detail(
        self,
        company_id: str,
        *,
        signal_limit: int = 10,
        timeline_limit: int = 10,
        insight_limit: int = 5,
        document_limit: int = 5,
        metric_limit: int = 8,
        risk_limit: int = 8,
        business_event_limit: int = 8,
    ) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                WITH ranked_companies AS (
                  SELECT c.*,
                         ROW_NUMBER() OVER (PARTITION BY c.company_id ORDER BY c.updated_at DESC, c.id DESC) AS rn
                  FROM companies c
                )
                SELECT source, company_id, canonical_name, display_name, country, region, city,
                       segments_json, industries_json, website_url, linkedin_url, facebook_url,
                       x_url, instagram_url, wikipedia_url, profile_summary, description,
                       extra_json, updated_at
                FROM ranked_companies
                WHERE rn = 1 AND company_id = :company_id
                """
            ),
            {"company_id": company_id},
        ).mappings().first()
        if not row:
            return None

        signal_stats = self.db.execute(
            text(
                """
                SELECT COUNT(*) AS signal_count, MAX(event_time) AS last_signal_at
                FROM trigger_signals
                WHERE company_id = :company_id
                """
            ),
            {"company_id": company_id},
        ).mappings().first()
        timeline_stats = self.db.execute(
            text(
                """
                SELECT COUNT(*) AS timeline_event_count, MAX(event_time) AS last_event_at
                FROM client_one_view_timeline
                WHERE company_id = :company_id
                """
            ),
            {"company_id": company_id},
        ).mappings().first()
        insight_stats = self.db.execute(
            text(
                """
                SELECT COUNT(*) AS generated_insight_count, MAX(generated_at) AS last_insight_at
                FROM generated_insights
                WHERE company_id = :company_id
                """
            ),
            {"company_id": company_id},
        ).mappings().first()
        signal_distribution = self.db.execute(
            text(
                """
                SELECT signal_type AS name, COUNT(*) AS count
                FROM trigger_signals
                WHERE company_id = :company_id
                GROUP BY signal_type
                ORDER BY count DESC, signal_type ASC
                """
            ),
            {"company_id": company_id},
        ).mappings().all()
        evidence_summary = self.db.execute(
            text(
                """
                SELECT
                  COUNT(*) AS parsed_document_count,
                  SUM(CASE WHEN LOWER(parse_status) = 'success' THEN 1 ELSE 0 END) AS parsed_document_success_count,
                  SUM(CASE WHEN LOWER(parse_status) = 'partial' THEN 1 ELSE 0 END) AS parsed_document_partial_count,
                  SUM(CASE WHEN LOWER(parse_status) = 'failed' THEN 1 ELSE 0 END) AS parsed_document_failed_count,
                  SUM(CASE WHEN LOWER(COALESCE(ocr_status, '')) IN ('used', 'success', 'completed', 'hit') THEN 1 ELSE 0 END) AS ocr_hit_count,
                  SUM(CASE WHEN LOWER(COALESCE(xbrl_status, '')) IN ('used', 'success', 'completed', 'hit') THEN 1 ELSE 0 END) AS xbrl_hit_count,
                  SUM(CASE WHEN management_discussion_summary IS NOT NULL AND TRIM(management_discussion_summary) <> '' THEN 1 ELSE 0 END) AS management_discussion_count,
                  COALESCE(SUM(metric_count), 0) AS metric_count,
                  COALESCE(SUM(risk_factor_count), 0) AS risk_factor_count,
                  COALESCE(SUM(business_event_count), 0) AS business_event_count,
                  MAX(parsed_at) AS last_parsed_at
                FROM parsed_documents
                WHERE company_id = :company_id
                """
            ),
            {"company_id": company_id},
        ).mappings().first()

        recent_signals = self.list_signals(limit=signal_limit, offset=0, company_id=company_id)
        recent_timeline = self.list_timeline(limit=timeline_limit, offset=0, company_id=company_id)
        recent_insights = self.db.execute(
            text(
                """
                SELECT id, source, insight_type, title, summary, confidence, model_name,
                       prompt_version, generated_at
                FROM generated_insights
                WHERE company_id = :company_id
                ORDER BY generated_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"company_id": company_id, "limit": insight_limit},
        ).mappings().all()
        recent_documents = self.db.execute(
            text(
                """
                SELECT id, source, dataset, title, summary, media_type, lang, parser_name, backend_name,
                       parse_status, ocr_status, xbrl_status, management_discussion_summary,
                       section_count, table_count, metric_count, risk_factor_count, business_event_count,
                       evidence_url, parsed_at, metadata_json
                FROM parsed_documents
                WHERE company_id = :company_id
                ORDER BY parsed_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"company_id": company_id, "limit": document_limit},
        ).mappings().all()
        key_metrics = self.db.execute(
            text(
                """
                SELECT pm.document_id, pd.title, pm.name, pm.value, pm.unit, pm.period, pm.context,
                       pm.confidence, pd.parsed_at
                FROM parsed_metrics pm
                JOIN parsed_documents pd ON pd.id = pm.document_id
                WHERE pd.company_id = :company_id
                ORDER BY pd.parsed_at DESC, COALESCE(pm.confidence, 0) DESC, pm.metric_index ASC
                LIMIT :limit
                """
            ),
            {"company_id": company_id, "limit": metric_limit},
        ).mappings().all()
        key_risk_factors = self.db.execute(
            text(
                """
                SELECT pr.document_id, pd.title, pr.category, pr.description, pr.severity,
                       pr.confidence, pd.parsed_at
                FROM parsed_risk_factors pr
                JOIN parsed_documents pd ON pd.id = pr.document_id
                WHERE pd.company_id = :company_id
                ORDER BY pd.parsed_at DESC, COALESCE(pr.confidence, 0) DESC, pr.risk_index ASC
                LIMIT :limit
                """
            ),
            {"company_id": company_id, "limit": risk_limit},
        ).mappings().all()
        key_business_events = self.db.execute(
            text(
                """
                SELECT pbe.document_id, pd.title, pbe.event_type, pbe.summary, pbe.event_date,
                       pbe.parties_json, pbe.confidence, pd.parsed_at
                FROM parsed_business_events pbe
                JOIN parsed_documents pd ON pd.id = pbe.document_id
                WHERE pd.company_id = :company_id
                ORDER BY pd.parsed_at DESC, COALESCE(pbe.confidence, 0) DESC, pbe.event_index ASC
                LIMIT :limit
                """
            ),
            {"company_id": company_id, "limit": business_event_limit},
        ).mappings().all()

        return {
            "company": self._hydrate_company_row(dict(row)),
            "stats": {
                "signal_count": int(signal_stats["signal_count"] if signal_stats else 0),
                "timeline_event_count": int(timeline_stats["timeline_event_count"] if timeline_stats else 0),
                "generated_insight_count": int(insight_stats["generated_insight_count"] if insight_stats else 0),
                "last_signal_at": signal_stats["last_signal_at"] if signal_stats else None,
                "last_event_at": timeline_stats["last_event_at"] if timeline_stats else None,
                "last_insight_at": insight_stats["last_insight_at"] if insight_stats else None,
                "signal_type_distribution": [dict(item) for item in signal_distribution],
            },
            "evidence_summary": {
                "parsed_document_count": self._int_field(
                    evidence_summary["parsed_document_count"] if evidence_summary else 0
                ),
                "parsed_document_success_count": self._int_field(
                    evidence_summary["parsed_document_success_count"] if evidence_summary else 0
                ),
                "parsed_document_partial_count": self._int_field(
                    evidence_summary["parsed_document_partial_count"] if evidence_summary else 0
                ),
                "parsed_document_failed_count": self._int_field(
                    evidence_summary["parsed_document_failed_count"] if evidence_summary else 0
                ),
                "ocr_hit_count": self._int_field(evidence_summary["ocr_hit_count"] if evidence_summary else 0),
                "xbrl_hit_count": self._int_field(evidence_summary["xbrl_hit_count"] if evidence_summary else 0),
                "management_discussion_count": self._int_field(
                    evidence_summary["management_discussion_count"] if evidence_summary else 0
                ),
                "metric_count": self._int_field(evidence_summary["metric_count"] if evidence_summary else 0),
                "risk_factor_count": self._int_field(
                    evidence_summary["risk_factor_count"] if evidence_summary else 0
                ),
                "business_event_count": self._int_field(
                    evidence_summary["business_event_count"] if evidence_summary else 0
                ),
                "last_parsed_at": evidence_summary["last_parsed_at"] if evidence_summary else None,
            },
            "recent_signals": [
                {
                    **item,
                    "evidence_refs": self._json_field(item.get("evidence_refs_json"), []),
                    "extra": self._json_field(item.get("extra_json"), {}),
                }
                for item in recent_signals
            ],
            "recent_timeline": [
                {
                    **item,
                    "payload": self._json_field(item.get("payload_json"), {}),
                }
                for item in recent_timeline
            ],
            "recent_insights": [dict(item) for item in recent_insights],
            "recent_documents": [
                {
                    **{key: value for key, value in dict(item).items() if key != "metadata_json"},
                    "genai_extraction": build_genai_extraction_view(item.get("metadata_json")),
                }
                for item in recent_documents
            ],
            "key_metrics": [dict(item) for item in key_metrics],
            "key_risk_factors": [dict(item) for item in key_risk_factors],
            "key_business_events": [
                {
                    **dict(item),
                    "parties": self._json_field(item.get("parties_json"), []),
                }
                for item in key_business_events
            ],
        }

    def list_timeline(
        self,
        *,
        limit: int,
        offset: int,
        company_id: str | None = None,
        entity: str | None = None,
        event_type: str | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        clauses: list[str] = []
        if company_id:
            clauses.append("company_id = :company_id")
            params["company_id"] = company_id
        if entity:
            clauses.append("entity = :entity")
            params["entity"] = entity
        if event_type:
            clauses.append("event_type = :event_type")
            params["event_type"] = event_type
        if source:
            clauses.append("source = :source")
            params["source"] = source
        clauses.extend(_date_filter("event_time", date_from, date_to, params))
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.execute(
            text(
                f"""
                SELECT id, source, company_id, entity, event_time, event_type, headline, detail,
                       evidence_url, payload_json
                FROM client_one_view_timeline
                {where_sql}
                ORDER BY event_time DESC NULLS LAST, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings()
        return [dict(row) for row in rows]

    def list_generated_insights(
        self,
        *,
        limit: int,
        offset: int,
        company_id: str | None = None,
        entity: str | None = None,
        insight_type: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        clauses: list[str] = []
        if company_id:
            clauses.append("company_id = :company_id")
            params["company_id"] = company_id
        if entity:
            clauses.append("entity = :entity")
            params["entity"] = entity
        if insight_type:
            clauses.append("insight_type = :insight_type")
            params["insight_type"] = insight_type
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.execute(
            text(
                f"""
                SELECT id, source, company_id, entity, insight_type, title, summary, confidence,
                       model_name, prompt_version, generated_at
                FROM generated_insights
                {where_sql}
                ORDER BY generated_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings()
        return [dict(row) for row in rows]

    @staticmethod
    def default_workflow_state(*, prospect_id: str, company_id: str) -> dict[str, Any]:
        return {
            "prospect_id": prospect_id,
            "company_id": company_id,
            "owner": None,
            "stage": "new",
            "status": "open",
            "last_action": None,
            "next_action": None,
            "review_status": "not_reviewed",
            "notes": None,
            "updated_at": None,
        }

    def get_prospect_workflow_state(self, *, prospect_id: str, company_id: str) -> dict[str, Any]:
        try:
            row = self.db.execute(
                text(
                    """
                    SELECT prospect_id, company_id, owner, stage, status, last_action, next_action,
                           review_status, notes, updated_at
                    FROM prospect_workflow_states
                    WHERE prospect_id = :prospect_id
                    """
                ),
                {"prospect_id": prospect_id},
            ).mappings().first()
        except OperationalError:
            return self.default_workflow_state(prospect_id=prospect_id, company_id=company_id)
        if not row:
            return self.default_workflow_state(prospect_id=prospect_id, company_id=company_id)
        return dict(row)

    def upsert_prospect_workflow_state(
        self,
        *,
        prospect_id: str,
        company_id: str,
        owner: str | None,
        stage: str,
        status: str,
        last_action: str | None,
        next_action: str | None,
        review_status: str,
        notes: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        self.db.execute(
            text(
                """
                INSERT INTO prospect_workflow_states (
                  prospect_id, company_id, owner, stage, status, last_action, next_action,
                  review_status, notes, updated_at
                )
                VALUES (
                  :prospect_id, :company_id, :owner, :stage, :status, :last_action, :next_action,
                  :review_status, :notes, :updated_at
                )
                ON CONFLICT (prospect_id) DO UPDATE SET
                  company_id = EXCLUDED.company_id,
                  owner = EXCLUDED.owner,
                  stage = EXCLUDED.stage,
                  status = EXCLUDED.status,
                  last_action = EXCLUDED.last_action,
                  next_action = EXCLUDED.next_action,
                  review_status = EXCLUDED.review_status,
                  notes = EXCLUDED.notes,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "prospect_id": prospect_id,
                "company_id": company_id,
                "owner": owner,
                "stage": stage,
                "status": status,
                "last_action": last_action,
                "next_action": next_action,
                "review_status": review_status,
                "notes": notes,
                "updated_at": now,
            },
        )
        return self.get_prospect_workflow_state(prospect_id=prospect_id, company_id=company_id)

    def metadata_filters(self) -> dict[str, list[dict[str, Any]]]:
        def sorted_counts(values: list[str]) -> list[dict[str, Any]]:
            counts: dict[str, int] = {}
            for value in values:
                if not value:
                    continue
                counts[value] = counts.get(value, 0) + 1
            return [
                {"name": name, "count": count}
                for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ]

        def count_query(sql: str) -> list[dict[str, Any]]:
            rows = self.db.execute(text(sql)).mappings()
            return [dict(row) for row in rows if row["name"]]

        existing_tables = set(inspect(self.db.get_bind()).get_table_names())
        companies = self.list_companies(limit=1000, offset=0)
        source_values: list[str] = []
        dataset_values: list[str] = []
        if "trigger_signals" in existing_tables:
            signal_sources = count_query(
                """
                SELECT source AS name, COUNT(*) AS count
                FROM trigger_signals
                WHERE source IS NOT NULL AND TRIM(source) <> ''
                GROUP BY source
                """
            )
            signal_datasets = count_query(
                """
                SELECT dataset AS name, COUNT(*) AS count
                FROM trigger_signals
                WHERE dataset IS NOT NULL AND TRIM(dataset) <> ''
                GROUP BY dataset
                """
            )
            for item in signal_sources:
                source_values.extend([item["name"]] * int(item["count"]))
            for item in signal_datasets:
                dataset_values.extend([item["name"]] * int(item["count"]))
        if "intelligence_records" in existing_tables:
            record_sources = count_query(
                """
                SELECT source AS name, COUNT(*) AS count
                FROM intelligence_records
                WHERE source IS NOT NULL AND TRIM(source) <> ''
                GROUP BY source
                """
            )
            record_datasets = count_query(
                """
                SELECT dataset AS name, COUNT(*) AS count
                FROM intelligence_records
                WHERE dataset IS NOT NULL AND TRIM(dataset) <> ''
                GROUP BY dataset
                """
            )
            for item in record_sources:
                source_values.extend([item["name"]] * int(item["count"]))
            for item in record_datasets:
                dataset_values.extend([item["name"]] * int(item["count"]))

        return {
            "regions": sorted_counts([item.get("region") for item in companies if item.get("region")]),
            "segments": sorted_counts(
                [segment for item in companies for segment in item.get("segments", []) if segment]
            ),
            "industries": sorted_counts(
                [industry for item in companies for industry in item.get("industries", []) if industry]
            ),
            "signal_types": count_query(
                """
                SELECT signal_type AS name, COUNT(*) AS count
                FROM trigger_signals
                WHERE signal_type IS NOT NULL AND TRIM(signal_type) <> ''
                GROUP BY signal_type
                ORDER BY count DESC, signal_type ASC
                """
            )
            if "trigger_signals" in existing_tables
            else [],
            "sources": sorted_counts(source_values),
            "datasets": sorted_counts(dataset_values),
        }

    def overview(self) -> dict[str, Any]:
        counts = {}
        for table_name, key in (
            ("ingestion_runs", "ingestion_runs"),
            ("intelligence_records", "intelligence_records"),
            ("trigger_signals", "trigger_signals"),
            ("client_one_view_timeline", "timeline_events"),
            ("generated_insights", "generated_insights"),
        ):
            counts[key] = int(self.db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())

        latest = self.db.execute(
            text(
                """
                SELECT run_id, status
                FROM ingestion_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
        ).mappings().first()

        signal_dist = self.db.execute(
            text(
                """
                SELECT signal_type AS name, COUNT(*) AS count
                FROM trigger_signals
                GROUP BY signal_type
                ORDER BY count DESC
                """
            )
        ).mappings()
        source_dist = self.db.execute(
            text(
                """
                SELECT source AS name, COUNT(*) AS count
                FROM intelligence_records
                GROUP BY source
                ORDER BY count DESC
                """
            )
        ).mappings()

        return {
            **counts,
            "latest_run_id": latest["run_id"] if latest else None,
            "latest_run_status": latest["status"] if latest else None,
            "signal_type_distribution": [dict(row) for row in signal_dist],
            "source_distribution": [dict(row) for row in source_dist],
        }
