from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


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
