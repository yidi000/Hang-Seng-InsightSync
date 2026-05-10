from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from insightsync.backend.core.config import get_settings
from insightsync.backend.db.session import SessionLocal
from insightsync.backend.db.tables import (
    client_one_view_timeline,
    companies,
    company_mapping_audit,
    generated_insights,
    ingestion_runs,
    intelligence_records,
    parsed_business_events,
    parsed_documents,
    parsed_metrics,
    parsed_risk_factors,
    parsed_sections,
    parsed_tables,
    parsing_runs,
    trigger_signals,
)
from insightsync.backend.utils import parse_timestamp


def _json_loads(raw: str | None, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _sqlite_rows(sqlite_path: Path, table: str, since_run_id: str | None = None) -> list[dict[str, Any]]:
    query = f"SELECT * FROM {table}"
    params: tuple[Any, ...] = ()
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
            (table,),
        ).fetchone()
        if not exists:
            return []
        if since_run_id:
            columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if "run_id" in columns:
                query += " WHERE run_id >= ?"
                params = (since_run_id,)
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def _upsert_rows(
    db: Session,
    table: Any,
    rows: list[dict[str, Any]],
    conflict_cols: list[str],
    update_cols: list[str] | None = None,
    batch_size: int = 500,
) -> int:
    if not rows:
        return 0
    total = 0
    for idx in range(0, len(rows), batch_size):
        batch = rows[idx : idx + batch_size]
        stmt = insert(table).values(batch)
        if update_cols:
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_cols,
                set_={column: getattr(stmt.excluded, column) for column in update_cols},
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
        result = db.execute(stmt)
        total += max(0, int(result.rowcount or 0))
    return total


def _map_ingestion_run(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "started_at": parse_timestamp(row["started_at"]),
        "finished_at": parse_timestamp(row.get("finished_at")),
        "status": row["status"],
        "message": row.get("message"),
        "summary_json": _json_loads(row.get("summary_json"), {}),
    }


def _map_intelligence_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row["source"],
        "dataset": row["dataset"],
        "record_key": row["record_key"],
        "record_type": row["record_type"],
        "company_id": row.get("company_id"),
        "entity": row.get("entity"),
        "event_time": parse_timestamp(row.get("event_time")),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "region": row.get("region"),
        "industry": row.get("industry"),
        "lang": row.get("lang"),
        "evidence_url": row.get("evidence_url"),
        "tags_json": _json_loads(row.get("tags_json"), []),
        "payload_json": _json_loads(row.get("payload_json"), {}),
        "raw_json": _json_loads(row.get("raw_json"), None),
        "content_hash": row["content_hash"],
        "fetched_at": parse_timestamp(row["fetched_at"]),
        "run_id": row["run_id"],
    }


def _map_trigger_signal(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row["source"],
        "dataset": row["dataset"],
        "signal_key": row["signal_key"],
        "signal_type": row["signal_type"],
        "company_id": row.get("company_id"),
        "entity": row.get("entity"),
        "event_time": parse_timestamp(row["event_time"]),
        "indicator": row.get("indicator"),
        "value_num": row.get("value_num"),
        "value_text": row.get("value_text"),
        "unit": row.get("unit"),
        "signal_text": row.get("signal_text"),
        "signal_score": row.get("signal_score"),
        "signal_level": row.get("signal_level"),
        "evidence_refs_json": _json_loads(row.get("evidence_refs_json"), []),
        "extra_json": _json_loads(row.get("extra_json"), {}),
        "row_hash": row["row_hash"],
        "fetched_at": parse_timestamp(row["fetched_at"]),
        "run_id": row["run_id"],
    }


def _map_timeline_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row["source"],
        "company_id": row.get("company_id"),
        "entity": row.get("entity"),
        "event_time": parse_timestamp(row.get("event_time")),
        "event_type": row["event_type"],
        "headline": row["headline"],
        "detail": row.get("detail"),
        "evidence_url": row.get("evidence_url"),
        "payload_json": _json_loads(row.get("payload_json"), {}),
        "dedup_hash": row["dedup_hash"],
        "fetched_at": parse_timestamp(row["fetched_at"]),
        "run_id": row["run_id"],
    }


def _map_generated_insight(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row["source"],
        "company_id": row.get("company_id"),
        "entity": row.get("entity"),
        "insight_type": row["insight_type"],
        "title": row["title"],
        "summary": row["summary"],
        "confidence": row.get("confidence"),
        "evidence_record_keys_json": _json_loads(row.get("evidence_record_keys_json"), []),
        "evidence_signal_keys_json": _json_loads(row.get("evidence_signal_keys_json"), []),
        "model_name": row.get("model_name"),
        "model_version": row.get("model_version"),
        "prompt_version": row.get("prompt_version"),
        "meta_json": _json_loads(row.get("meta_json"), {}),
        "generated_at": parse_timestamp(row["generated_at"]),
        "run_id": row["run_id"],
        "dedup_hash": row["dedup_hash"],
    }


def _map_parsing_run(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "parse_version": row["parse_version"],
        "started_at": parse_timestamp(row["started_at"]),
        "finished_at": parse_timestamp(row.get("finished_at")),
        "status": row["status"],
        "message": row.get("message"),
        "summary_json": _json_loads(row.get("summary_json"), {}),
    }


def _map_parsed_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_table": row["source_table"],
        "source_id": row["source_id"],
        "source_content_hash": row["source_content_hash"],
        "source_record_key": row.get("source_record_key"),
        "source": row["source"],
        "dataset": row.get("dataset"),
        "company_id": row.get("company_id"),
        "entity": row.get("entity"),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "media_type": row.get("media_type"),
        "lang": row.get("lang"),
        "file_path": row.get("file_path"),
        "evidence_url": row.get("evidence_url"),
        "parser_name": row["parser_name"],
        "backend_name": row.get("backend_name"),
        "parse_version": row["parse_version"],
        "parse_status": row["parse_status"],
        "ocr_status": row.get("ocr_status"),
        "xbrl_status": row.get("xbrl_status"),
        "content_text": row.get("content_text"),
        "search_text": row.get("search_text"),
        "warnings_json": _json_loads(row.get("warnings_json"), []),
        "metadata_json": _json_loads(row.get("metadata_json"), {}),
        "management_discussion_summary": row.get("management_discussion_summary"),
        "management_discussion_highlights_json": _json_loads(row.get("management_discussion_highlights_json"), []),
        "management_discussion_source_sections_json": _json_loads(row.get("management_discussion_source_sections_json"), []),
        "section_count": row.get("section_count") or 0,
        "table_count": row.get("table_count") or 0,
        "metric_count": row.get("metric_count") or 0,
        "risk_factor_count": row.get("risk_factor_count") or 0,
        "business_event_count": row.get("business_event_count") or 0,
        "parsed_at": parse_timestamp(row["parsed_at"]),
        "run_id": row["run_id"],
    }


def _map_parsed_section(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row["document_id"],
        "section_index": row["section_index"],
        "heading": row["heading"],
        "text": row["text"],
        "level": row["level"],
        "section_type": row.get("section_type"),
        "page_number": row.get("page_number"),
    }


def _map_parsed_table(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row["document_id"],
        "table_index": row["table_index"],
        "title": row.get("title"),
        "headers_json": _json_loads(row.get("headers_json"), []),
        "rows_json": _json_loads(row.get("rows_json"), []),
        "page_number": row.get("page_number"),
    }


def _map_parsed_metric(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row["document_id"],
        "metric_index": row["metric_index"],
        "name": row["name"],
        "value": row["value"],
        "unit": row.get("unit"),
        "period": row.get("period"),
        "context": row.get("context"),
        "confidence": row.get("confidence"),
    }


def _map_parsed_risk_factor(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row["document_id"],
        "risk_index": row["risk_index"],
        "category": row["category"],
        "description": row["description"],
        "severity": row["severity"],
        "confidence": row.get("confidence"),
    }


def _map_parsed_business_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row["document_id"],
        "event_index": row["event_index"],
        "event_type": row["event_type"],
        "summary": row["summary"],
        "event_date": row.get("event_date"),
        "parties_json": _json_loads(row.get("parties_json"), []),
        "confidence": row.get("confidence"),
    }


def _map_company(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row["source"],
        "company_id": row["company_id"],
        "canonical_name": row["canonical_name"],
        "display_name": row.get("display_name"),
        "country": row.get("country"),
        "region": row.get("region"),
        "city": row.get("city"),
        "segments_json": _json_loads(row.get("segments_json"), []),
        "industries_json": _json_loads(row.get("industries_json"), []),
        "website_url": row.get("website_url"),
        "linkedin_url": row.get("linkedin_url"),
        "facebook_url": row.get("facebook_url"),
        "x_url": row.get("x_url"),
        "instagram_url": row.get("instagram_url"),
        "wikipedia_url": row.get("wikipedia_url"),
        "profile_summary": row.get("profile_summary"),
        "description": row.get("description"),
        "extra_json": _json_loads(row.get("extra_json"), {}),
        "row_hash": row["row_hash"],
        "updated_at": parse_timestamp(row["updated_at"]),
        "run_id": row["run_id"],
    }


def _map_company_mapping_audit(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "target_table": row["target_table"],
        "target_row_id": row["target_row_id"],
        "old_company_id": row.get("old_company_id"),
        "new_company_id": row["new_company_id"],
        "mapping_method": row["mapping_method"],
        "confidence": row.get("confidence"),
        "matched_alias": row.get("matched_alias"),
        "matched_context": row.get("matched_context"),
        "mapped_at": parse_timestamp(row["mapped_at"]),
    }


def sync_from_sqlite(sqlite_path: Path, db: Session, *, since_run_id: str | None = None) -> dict[str, dict[str, int]]:
    """Sync SQLite data module outputs into PostgreSQL.

    Semantics: the intelligence/signal/timeline/insight tables are append-only
    version histories — the uniqueness constraint includes ``content_hash`` /
    ``row_hash`` / ``dedup_hash``, so an update to the source produces a new row
    (new hash → no conflict → inserted). The latest version can be recovered
    by ordering on ``fetched_at`` or ``generated_at``. If the caller needs
    true replacement semantics, use ``rag_documents`` (handled in
    ``RagDocumentBuilder.build_documents``) or emit an explicit delete.
    """

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite source not found: {sqlite_path}")

    specs = [
        ("ingestion_runs", ingestion_runs, _map_ingestion_run, ["run_id"], None),
        ("intelligence_records", intelligence_records, _map_intelligence_record, ["source", "dataset", "record_key", "content_hash"], None),
        ("trigger_signals", trigger_signals, _map_trigger_signal, ["source", "dataset", "signal_key", "row_hash"], None),
        ("client_one_view_timeline", client_one_view_timeline, _map_timeline_event, ["source", "dedup_hash"], None),
        ("parsing_runs", parsing_runs, _map_parsing_run, ["run_id"], ["parse_version", "started_at", "finished_at", "status", "message", "summary_json"]),
        (
            "parsed_documents",
            parsed_documents,
            _map_parsed_document,
            ["id"],
            [
                "source_table",
                "source_id",
                "source_content_hash",
                "source_record_key",
                "source",
                "dataset",
                "company_id",
                "entity",
                "title",
                "summary",
                "media_type",
                "lang",
                "file_path",
                "evidence_url",
                "parser_name",
                "backend_name",
                "parse_version",
                "parse_status",
                "ocr_status",
                "xbrl_status",
                "content_text",
                "search_text",
                "warnings_json",
                "metadata_json",
                "management_discussion_summary",
                "management_discussion_highlights_json",
                "management_discussion_source_sections_json",
                "section_count",
                "table_count",
                "metric_count",
                "risk_factor_count",
                "business_event_count",
                "parsed_at",
                "run_id",
            ],
        ),
        (
            "parsed_sections",
            parsed_sections,
            _map_parsed_section,
            ["document_id", "section_index"],
            ["heading", "text", "level", "section_type", "page_number"],
        ),
        (
            "parsed_tables",
            parsed_tables,
            _map_parsed_table,
            ["document_id", "table_index"],
            ["title", "headers_json", "rows_json", "page_number"],
        ),
        (
            "parsed_metrics",
            parsed_metrics,
            _map_parsed_metric,
            ["document_id", "metric_index"],
            ["name", "value", "unit", "period", "context", "confidence"],
        ),
        (
            "parsed_risk_factors",
            parsed_risk_factors,
            _map_parsed_risk_factor,
            ["document_id", "risk_index"],
            ["category", "description", "severity", "confidence"],
        ),
        (
            "parsed_business_events",
            parsed_business_events,
            _map_parsed_business_event,
            ["document_id", "event_index"],
            ["event_type", "summary", "event_date", "parties_json", "confidence"],
        ),
        ("companies", companies, _map_company, ["company_id", "row_hash"], None),
        (
            "company_mapping_audit",
            company_mapping_audit,
            _map_company_mapping_audit,
            ["run_id", "target_table", "target_row_id", "new_company_id", "mapping_method"],
            None,
        ),
        ("generated_insights", generated_insights, _map_generated_insight, ["dedup_hash"], None),
    ]
    summary: dict[str, dict[str, int]] = {}
    for source_table, target_table, mapper, conflict_cols, update_cols in specs:
        raw_rows = _sqlite_rows(sqlite_path, source_table, since_run_id=since_run_id)
        mapped = [mapper(row) for row in raw_rows]
        inserted = _upsert_rows(db, target_table, mapped, conflict_cols, update_cols=update_cols)
        summary[source_table] = {
            "scanned": len(raw_rows),
            "inserted": inserted,
            "skipped": max(0, len(raw_rows) - inserted),
        }
    db.commit()
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync InsightSync SQLite outputs into PostgreSQL.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--since-run-id")
    parser.add_argument("--sqlite-source-path", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    sqlite_path = Path(args.sqlite_source_path or settings.sqlite_source_path)
    with SessionLocal() as db:
        summary = sync_from_sqlite(sqlite_path, db, since_run_id=args.since_run_id)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
