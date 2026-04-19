from __future__ import annotations

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

    def list_signals(
        self,
        *,
        limit: int,
        offset: int,
        entity: str | None = None,
        signal_type: str | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        clauses: list[str] = []
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
