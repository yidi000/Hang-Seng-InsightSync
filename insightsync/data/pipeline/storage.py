from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import CollectionBatch, IntelligenceRecord, TimelineEvent, TriggerSignal
from .utils import canonical_json, stable_json_hash, utc_now_iso


def _infer_record_type(source: str, dataset: str) -> str:
    ds = dataset.lower()
    if "pdf" in ds or "csv" in ds or source == "kpmg":
        return "document"
    if "press_release" in ds or "detail_page" in ds:
        return "event"
    return "metric"


def _infer_signal_type(indicator: str | None, dataset: str) -> str:
    text = f"{dataset} {indicator or ''}".lower()
    if any(k in text for k in ("export", "trade", "cross", "fx", "cny", "usd")):
        return "cross_border"
    if any(k in text for k in ("unemployment", "risk", "loan", "impairment")):
        return "risk"
    if any(k in text for k in ("growth", "gdp", "output", "expansion", "industry", "agriculture")):
        return "growth"
    if any(k in text for k in ("fund", "finance", "liquidity", "consumption")):
        return "financing"
    return "market"


class SQLiteRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._create_schema()
        self._maybe_migrate_legacy()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteRepository":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _table_exists(self, name: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
            (name,),
        ).fetchone()
        return row is not None

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ingestion_runs (
              run_id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              status TEXT NOT NULL,
              message TEXT,
              summary_json TEXT
            );

            CREATE TABLE IF NOT EXISTS intelligence_records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT NOT NULL,
              dataset TEXT NOT NULL,
              record_key TEXT NOT NULL,
              record_type TEXT NOT NULL,
              company_id TEXT,
              entity TEXT,
              event_time TEXT,
              title TEXT,
              summary TEXT,
              region TEXT,
              industry TEXT,
              lang TEXT,
              evidence_url TEXT,
              tags_json TEXT,
              payload_json TEXT NOT NULL,
              raw_json TEXT,
              content_hash TEXT NOT NULL,
              fetched_at TEXT NOT NULL,
              run_id TEXT NOT NULL,
              UNIQUE(source, dataset, record_key, content_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_intelligence_lookup
              ON intelligence_records(source, dataset, event_time);

            CREATE TABLE IF NOT EXISTS trigger_signals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT NOT NULL,
              dataset TEXT NOT NULL,
              signal_key TEXT NOT NULL,
              signal_type TEXT NOT NULL,
              company_id TEXT,
              entity TEXT,
              event_time TEXT NOT NULL,
              indicator TEXT,
              value_num REAL,
              value_text TEXT,
              unit TEXT,
              signal_text TEXT,
              signal_score REAL,
              signal_level TEXT,
              evidence_refs_json TEXT,
              extra_json TEXT,
              row_hash TEXT NOT NULL,
              fetched_at TEXT NOT NULL,
              run_id TEXT NOT NULL,
              UNIQUE(source, dataset, signal_key, row_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_trigger_lookup
              ON trigger_signals(source, signal_type, event_time);

            CREATE TABLE IF NOT EXISTS client_one_view_timeline (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT NOT NULL,
              company_id TEXT,
              entity TEXT,
              event_time TEXT,
              event_type TEXT NOT NULL,
              headline TEXT NOT NULL,
              detail TEXT,
              evidence_url TEXT,
              payload_json TEXT,
              dedup_hash TEXT NOT NULL,
              fetched_at TEXT NOT NULL,
              run_id TEXT NOT NULL,
              UNIQUE(source, dedup_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_timeline_lookup
              ON client_one_view_timeline(company_id, entity, event_time);

            CREATE TABLE IF NOT EXISTS prospect_scores (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              company_id TEXT NOT NULL,
              score REAL,
              tier TEXT,
              reasons_json TEXT,
              recommended_products_json TEXT,
              recommended_entry_angle TEXT,
              updated_at TEXT NOT NULL,
              run_id TEXT NOT NULL,
              UNIQUE(company_id, run_id)
            );

            CREATE TABLE IF NOT EXISTS generated_insights (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT NOT NULL,
              company_id TEXT,
              entity TEXT,
              insight_type TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT NOT NULL,
              confidence REAL,
              evidence_record_keys_json TEXT,
              evidence_signal_keys_json TEXT,
              model_name TEXT,
              model_version TEXT,
              prompt_version TEXT,
              meta_json TEXT,
              generated_at TEXT NOT NULL,
              run_id TEXT NOT NULL,
              dedup_hash TEXT NOT NULL,
              UNIQUE(dedup_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_generated_insights_lookup
              ON generated_insights(company_id, entity, insight_type, generated_at);
            """
        )
        self.conn.commit()

    def _new_tables_empty(self) -> bool:
        names = ("intelligence_records", "trigger_signals", "client_one_view_timeline")
        for table in names:
            row = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            if row and int(row[0]) > 0:
                return False
        return True

    def _legacy_tables_exist(self) -> bool:
        return all(self._table_exists(name) for name in ("snapshot_records", "signal_points", "artifacts"))

    def _maybe_migrate_legacy(self) -> None:
        if not self._legacy_tables_exist():
            return
        if not self._new_tables_empty():
            return

        with self.conn:
            for row in self.conn.execute(
                """
                SELECT source, dataset, natural_key, record_time, lang, url, content_json, raw_json, fetched_at, run_id
                FROM snapshot_records
                """
            ):
                source = row["source"]
                dataset = row["dataset"]
                content = json.loads(row["content_json"]) if row["content_json"] else {}
                raw = json.loads(row["raw_json"]) if row["raw_json"] else None
                title = content.get("title") or content.get("subject") or content.get("name") or dataset
                summary = content.get("summary") or content.get("subject") or str(title)
                entity = content.get("economy") or content.get("category") or "HKG"
                region = "Guangdong" if source == "guangdong_stats" else "Hong Kong"
                industry = content.get("category") if isinstance(content.get("category"), str) else None

                rec = IntelligenceRecord(
                    source=source,
                    dataset=dataset,
                    record_key=row["natural_key"],
                    record_type=_infer_record_type(source, dataset),
                    company_id=None,
                    entity=str(entity) if entity is not None else None,
                    event_time=row["record_time"],
                    title=str(title) if title is not None else None,
                    summary=str(summary) if summary is not None else None,
                    region=region,
                    industry=industry,
                    lang=row["lang"],
                    evidence_url=row["url"],
                    tags=[source, dataset],
                    payload=content if isinstance(content, dict) else {"value": content},
                    raw=raw if isinstance(raw, dict) else None,
                )
                self._insert_intelligence_record(rec, fetched_at=row["fetched_at"], run_id=row["run_id"])
                self._insert_timeline_event(
                    TimelineEvent(
                        source=rec.source,
                        company_id=rec.company_id,
                        entity=rec.entity,
                        event_time=rec.event_time,
                        event_type=rec.record_type,
                        headline=(rec.title or f"{rec.source} {rec.dataset}")[:240],
                        detail=rec.summary,
                        evidence_url=rec.evidence_url,
                        payload={"source": rec.source, "dataset": rec.dataset, "record_key": rec.record_key},
                    ),
                    fetched_at=row["fetched_at"],
                    run_id=row["run_id"],
                )

            for row in self.conn.execute(
                """
                SELECT source, dataset, entity, indicator, time_period, value_num, value_text, unit, extra_json, fetched_at, run_id
                FROM signal_points
                """
            ):
                extra = json.loads(row["extra_json"]) if row["extra_json"] else {}
                value_text = row["value_text"]
                signal = TriggerSignal(
                    source=row["source"],
                    dataset=row["dataset"],
                    signal_key=f"{row['dataset']}|{row['entity']}|{row['indicator']}|{row['time_period']}|{value_text}",
                    signal_type=_infer_signal_type(row["indicator"], row["dataset"]),
                    company_id=None,
                    entity=row["entity"],
                    event_time=row["time_period"],
                    indicator=row["indicator"],
                    value_num=row["value_num"],
                    value_text=value_text,
                    unit=row["unit"],
                    signal_text=f"{row['indicator']}: {value_text or row['value_num']}",
                    evidence_refs=[row["source"], row["dataset"]],
                    extra=extra if isinstance(extra, dict) else {},
                )
                self._insert_trigger_signal(signal, fetched_at=row["fetched_at"], run_id=row["run_id"])

            for row in self.conn.execute(
                """
                SELECT source, dataset, url, file_path, file_sha256, meta_json, fetched_at, run_id
                FROM artifacts
                """
            ):
                meta = json.loads(row["meta_json"]) if row["meta_json"] else {}
                rec = IntelligenceRecord(
                    source=row["source"],
                    dataset=row["dataset"],
                    record_key=row["file_sha256"],
                    record_type="document",
                    company_id=None,
                    entity=None,
                    event_time=None,
                    title=Path(row["file_path"]).name,
                    summary="Legacy migrated file artifact",
                    region="Hong Kong",
                    industry=None,
                    lang=None,
                    evidence_url=row["url"],
                    tags=[row["source"], row["dataset"], "artifact"],
                    payload={
                        "file_path": row["file_path"],
                        "file_sha256": row["file_sha256"],
                        "meta": meta if isinstance(meta, dict) else {},
                    },
                    raw=None,
                )
                self._insert_intelligence_record(rec, fetched_at=row["fetched_at"], run_id=row["run_id"])
                self._insert_timeline_event(
                    TimelineEvent(
                        source=rec.source,
                        company_id=rec.company_id,
                        entity=rec.entity,
                        event_time=rec.event_time,
                        event_type="document",
                        headline=(rec.title or f"{rec.source} document")[:240],
                        detail=rec.summary,
                        evidence_url=rec.evidence_url,
                        payload={"source": rec.source, "dataset": rec.dataset, "record_key": rec.record_key},
                    ),
                    fetched_at=row["fetched_at"],
                    run_id=row["run_id"],
                )

    def start_run(self, run_id: str, *, started_at: str | None = None) -> None:
        ts = started_at or utc_now_iso()
        self.conn.execute(
            "INSERT INTO ingestion_runs(run_id, started_at, status) VALUES(?, ?, ?)",
            (run_id, ts, "running"),
        )
        self.conn.commit()

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        message: str | None = None,
        summary: dict[str, Any] | None = None,
        finished_at: str | None = None,
    ) -> None:
        ts = finished_at or utc_now_iso()
        self.conn.execute(
            """
            UPDATE ingestion_runs
            SET finished_at = ?, status = ?, message = ?, summary_json = ?
            WHERE run_id = ?
            """,
            (ts, status, message, canonical_json(summary or {}), run_id),
        )
        self.conn.commit()

    def _insert_intelligence_record(self, rec: IntelligenceRecord, *, fetched_at: str, run_id: str) -> int:
        payload = rec.payload if isinstance(rec.payload, dict) else {"value": rec.payload}
        content_hash = stable_json_hash(payload)
        row = self.conn.execute(
            """
            INSERT OR IGNORE INTO intelligence_records(
              source, dataset, record_key, record_type, company_id, entity, event_time,
              title, summary, region, industry, lang, evidence_url, tags_json, payload_json,
              raw_json, content_hash, fetched_at, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.source,
                rec.dataset,
                rec.record_key,
                rec.record_type,
                rec.company_id,
                rec.entity,
                rec.event_time,
                rec.title,
                rec.summary,
                rec.region,
                rec.industry,
                rec.lang,
                rec.evidence_url,
                canonical_json(rec.tags),
                canonical_json(payload),
                canonical_json(rec.raw) if rec.raw is not None else None,
                content_hash,
                fetched_at,
                run_id,
            ),
        )
        return 1 if row.rowcount > 0 else 0

    def _insert_trigger_signal(self, sig: TriggerSignal, *, fetched_at: str, run_id: str) -> int:
        row_hash = stable_json_hash(
            {
                "company_id": sig.company_id,
                "entity": sig.entity,
                "indicator": sig.indicator,
                "event_time": sig.event_time,
                "value_num": sig.value_num,
                "value_text": sig.value_text,
                "extra": sig.extra,
            }
        )
        row = self.conn.execute(
            """
            INSERT OR IGNORE INTO trigger_signals(
              source, dataset, signal_key, signal_type, company_id, entity, event_time, indicator,
              value_num, value_text, unit, signal_text, signal_score, signal_level, evidence_refs_json,
              extra_json, row_hash, fetched_at, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sig.source,
                sig.dataset,
                sig.signal_key,
                sig.signal_type,
                sig.company_id,
                sig.entity,
                sig.event_time,
                sig.indicator,
                sig.value_num,
                sig.value_text,
                sig.unit,
                sig.signal_text,
                sig.signal_score,
                sig.signal_level,
                canonical_json(sig.evidence_refs),
                canonical_json(sig.extra),
                row_hash,
                fetched_at,
                run_id,
            ),
        )
        return 1 if row.rowcount > 0 else 0

    def _insert_timeline_event(self, event: TimelineEvent, *, fetched_at: str, run_id: str) -> int:
        dedup_hash = stable_json_hash(
            {
                "company_id": event.company_id,
                "entity": event.entity,
                "event_time": event.event_time,
                "event_type": event.event_type,
                "headline": event.headline,
                "source": event.source,
            }
        )
        row = self.conn.execute(
            """
            INSERT OR IGNORE INTO client_one_view_timeline(
              source, company_id, entity, event_time, event_type, headline, detail, evidence_url,
              payload_json, dedup_hash, fetched_at, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.source,
                event.company_id,
                event.entity,
                event.event_time,
                event.event_type,
                event.headline,
                event.detail,
                event.evidence_url,
                canonical_json(event.payload),
                dedup_hash,
                fetched_at,
                run_id,
            ),
        )
        return 1 if row.rowcount > 0 else 0

    def _insert_prospect_score(self, score: Any, *, fetched_at: str, run_id: str) -> int:
        row = self.conn.execute(
            """
            INSERT OR IGNORE INTO prospect_scores(
              company_id, score, tier, reasons_json, recommended_products_json,
              recommended_entry_angle, updated_at, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                score.company_id,
                score.score,
                score.tier,
                canonical_json(score.reasons),
                canonical_json(score.recommended_products),
                score.recommended_entry_angle,
                fetched_at,
                run_id,
            ),
        )
        return 1 if row.rowcount > 0 else 0

    def _insert_generated_insight(self, insight: Any, *, fetched_at: str, run_id: str) -> int:
        dedup_hash = stable_json_hash(
            {
                "source": insight.source,
                "company_id": insight.company_id,
                "entity": insight.entity,
                "insight_type": insight.insight_type,
                "title": insight.title,
                "summary": insight.summary,
                "evidence_record_keys": insight.evidence_record_keys,
                "evidence_signal_keys": insight.evidence_signal_keys,
            }
        )
        row = self.conn.execute(
            """
            INSERT OR IGNORE INTO generated_insights(
              source, company_id, entity, insight_type, title, summary, confidence,
              evidence_record_keys_json, evidence_signal_keys_json, model_name, model_version,
              prompt_version, meta_json, generated_at, run_id, dedup_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                insight.source,
                insight.company_id,
                insight.entity,
                insight.insight_type,
                insight.title,
                insight.summary,
                insight.confidence,
                canonical_json(insight.evidence_record_keys),
                canonical_json(insight.evidence_signal_keys),
                insight.model_name,
                insight.model_version,
                insight.prompt_version,
                canonical_json(insight.meta),
                fetched_at,
                run_id,
                dedup_hash,
            ),
        )
        return 1 if row.rowcount > 0 else 0

    def persist_batch(self, run_id: str, batch: CollectionBatch, *, fetched_at: str | None = None) -> dict[str, int]:
        ts = fetched_at or utc_now_iso()
        inserted_records = 0
        inserted_signals = 0
        inserted_timeline = 0
        inserted_scores = 0
        inserted_insights = 0

        with self.conn:
            for rec in batch.intelligence_records:
                inserted_records += self._insert_intelligence_record(rec, fetched_at=ts, run_id=run_id)

            for sig in batch.trigger_signals:
                inserted_signals += self._insert_trigger_signal(sig, fetched_at=ts, run_id=run_id)

            for event in batch.timeline_events:
                inserted_timeline += self._insert_timeline_event(event, fetched_at=ts, run_id=run_id)

            for score in batch.prospect_scores:
                inserted_scores += self._insert_prospect_score(score, fetched_at=ts, run_id=run_id)

            for insight in batch.generated_insights:
                inserted_insights += self._insert_generated_insight(insight, fetched_at=ts, run_id=run_id)

        return {
            "intelligence_records": inserted_records,
            "trigger_signals": inserted_signals,
            "timeline_events": inserted_timeline,
            "prospect_scores": inserted_scores,
            "generated_insights": inserted_insights,
        }
