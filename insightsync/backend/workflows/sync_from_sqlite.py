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
    generated_insights,
    ingestion_runs,
    intelligence_records,
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
    if since_run_id and table != "ingestion_runs":
        query += " WHERE run_id >= ?"
        params = (since_run_id,)
    elif since_run_id and table == "ingestion_runs":
        query += " WHERE run_id >= ?"
        params = (since_run_id,)
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def _upsert_rows(db: Session, table: Any, rows: list[dict[str, Any]], conflict_cols: list[str]) -> int:
    if not rows:
        return 0
    stmt = insert(table).values(rows).on_conflict_do_nothing(index_elements=conflict_cols)
    result = db.execute(stmt)
    return max(0, int(result.rowcount or 0))


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
        ("ingestion_runs", ingestion_runs, _map_ingestion_run, ["run_id"]),
        ("intelligence_records", intelligence_records, _map_intelligence_record, ["source", "dataset", "record_key", "content_hash"]),
        ("trigger_signals", trigger_signals, _map_trigger_signal, ["source", "dataset", "signal_key", "row_hash"]),
        ("client_one_view_timeline", client_one_view_timeline, _map_timeline_event, ["source", "dedup_hash"]),
        ("generated_insights", generated_insights, _map_generated_insight, ["dedup_hash"]),
    ]
    summary: dict[str, dict[str, int]] = {}
    for source_table, target_table, mapper, conflict_cols in specs:
        raw_rows = _sqlite_rows(sqlite_path, source_table, since_run_id=since_run_id)
        mapped = [mapper(row) for row in raw_rows]
        inserted = _upsert_rows(db, target_table, mapped, conflict_cols)
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
