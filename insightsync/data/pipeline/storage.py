from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from insightsync.parsing import DEFAULT_PARSE_VERSION
from insightsync.parsing.models import ParsedDocument

from .models import CollectionBatch, CompanyProfile, IntelligenceRecord, TimelineEvent, TriggerSignal
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
        self.conn.execute("PRAGMA foreign_keys=ON;")
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

                        CREATE TABLE IF NOT EXISTS companies (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source TEXT NOT NULL,
                            company_id TEXT NOT NULL,
                            canonical_name TEXT NOT NULL,
                            display_name TEXT,
                            country TEXT,
                            region TEXT,
                            city TEXT,
                            segments_json TEXT,
                            industries_json TEXT,
                            website_url TEXT,
                            linkedin_url TEXT,
                            facebook_url TEXT,
                            x_url TEXT,
                            instagram_url TEXT,
                            wikipedia_url TEXT,
                            profile_summary TEXT,
                            description TEXT,
                            extra_json TEXT,
                            row_hash TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            run_id TEXT NOT NULL,
                            UNIQUE(company_id, row_hash)
                        );

                        CREATE INDEX IF NOT EXISTS idx_companies_lookup
                            ON companies(company_id, canonical_name, country, region);

                        CREATE TABLE IF NOT EXISTS company_mapping_audit (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            run_id TEXT NOT NULL,
                            target_table TEXT NOT NULL,
                            target_row_id INTEGER NOT NULL,
                            old_company_id TEXT,
                            new_company_id TEXT NOT NULL,
                            mapping_method TEXT NOT NULL,
                            confidence REAL,
                            matched_alias TEXT,
                            matched_context TEXT,
                            mapped_at TEXT NOT NULL,
                            UNIQUE(run_id, target_table, target_row_id, new_company_id, mapping_method)
                        );

                        CREATE INDEX IF NOT EXISTS idx_company_mapping_audit_lookup
                            ON company_mapping_audit(target_table, target_row_id, mapped_at);

            CREATE TABLE IF NOT EXISTS parsing_runs (
              run_id TEXT PRIMARY KEY,
              parse_version TEXT NOT NULL,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              status TEXT NOT NULL,
              message TEXT,
              summary_json TEXT
            );

            CREATE TABLE IF NOT EXISTS parsed_documents (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_table TEXT NOT NULL,
              source_id INTEGER NOT NULL,
              source_content_hash TEXT NOT NULL,
              source_record_key TEXT,
              source TEXT NOT NULL,
              dataset TEXT,
              company_id TEXT,
              entity TEXT,
              title TEXT,
              summary TEXT,
              media_type TEXT,
              lang TEXT,
              file_path TEXT,
              evidence_url TEXT,
              parser_name TEXT NOT NULL,
              backend_name TEXT,
              parse_version TEXT NOT NULL,
              parse_status TEXT NOT NULL,
              ocr_status TEXT,
              xbrl_status TEXT,
              content_text TEXT,
              search_text TEXT,
              warnings_json TEXT,
              metadata_json TEXT,
              management_discussion_summary TEXT,
              management_discussion_highlights_json TEXT,
              management_discussion_source_sections_json TEXT,
              section_count INTEGER NOT NULL DEFAULT 0,
              table_count INTEGER NOT NULL DEFAULT 0,
              metric_count INTEGER NOT NULL DEFAULT 0,
              risk_factor_count INTEGER NOT NULL DEFAULT 0,
              business_event_count INTEGER NOT NULL DEFAULT 0,
              parsed_at TEXT NOT NULL,
              run_id TEXT NOT NULL,
              UNIQUE(source_table, source_id, source_content_hash, parse_version)
            );

            CREATE INDEX IF NOT EXISTS idx_parsed_documents_lookup
              ON parsed_documents(source_table, source_id, parsed_at);

            CREATE INDEX IF NOT EXISTS idx_parsed_documents_company
              ON parsed_documents(company_id, source, dataset, parsed_at);

            CREATE TABLE IF NOT EXISTS parsed_sections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              section_index INTEGER NOT NULL,
              heading TEXT NOT NULL,
              text TEXT NOT NULL,
              level INTEGER NOT NULL DEFAULT 1,
              section_type TEXT,
              page_number INTEGER,
              UNIQUE(document_id, section_index),
              FOREIGN KEY(document_id) REFERENCES parsed_documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS parsed_tables (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              table_index INTEGER NOT NULL,
              title TEXT,
              headers_json TEXT,
              rows_json TEXT,
              page_number INTEGER,
              UNIQUE(document_id, table_index),
              FOREIGN KEY(document_id) REFERENCES parsed_documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS parsed_metrics (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              metric_index INTEGER NOT NULL,
              name TEXT NOT NULL,
              value TEXT NOT NULL,
              unit TEXT,
              period TEXT,
              context TEXT,
              confidence REAL,
              UNIQUE(document_id, metric_index),
              FOREIGN KEY(document_id) REFERENCES parsed_documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS parsed_risk_factors (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              risk_index INTEGER NOT NULL,
              category TEXT NOT NULL,
              description TEXT NOT NULL,
              severity TEXT NOT NULL,
              confidence REAL,
              UNIQUE(document_id, risk_index),
              FOREIGN KEY(document_id) REFERENCES parsed_documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS parsed_business_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              event_index INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              summary TEXT NOT NULL,
              event_date TEXT,
              parties_json TEXT,
              confidence REAL,
              UNIQUE(document_id, event_index),
              FOREIGN KEY(document_id) REFERENCES parsed_documents(id) ON DELETE CASCADE
            );
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

    def start_parsing_run(
        self,
        run_id: str,
        *,
        parse_version: str = DEFAULT_PARSE_VERSION,
        started_at: str | None = None,
    ) -> None:
        ts = started_at or utc_now_iso()
        self.conn.execute(
            """
            INSERT INTO parsing_runs(run_id, parse_version, started_at, status)
            VALUES(?, ?, ?, ?)
            """,
            (run_id, parse_version, ts, "running"),
        )
        self.conn.commit()

    def finish_parsing_run(
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
            UPDATE parsing_runs
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

    def _insert_company(self, company: CompanyProfile, *, fetched_at: str, run_id: str) -> int:
        row_hash = stable_json_hash(
            {
                "source": company.source,
                "company_id": company.company_id,
                "canonical_name": company.canonical_name,
                "display_name": company.display_name,
                "country": company.country,
                "region": company.region,
                "city": company.city,
                "segments": company.segments,
                "industries": company.industries,
                "website_url": company.website_url,
                "linkedin_url": company.linkedin_url,
                "facebook_url": company.facebook_url,
                "x_url": company.x_url,
                "instagram_url": company.instagram_url,
                "wikipedia_url": company.wikipedia_url,
                "profile_summary": company.profile_summary,
                "description": company.description,
                "extra": company.extra,
            }
        )
        row = self.conn.execute(
            """
            INSERT OR IGNORE INTO companies(
              source, company_id, canonical_name, display_name, country, region, city,
              segments_json, industries_json, website_url, linkedin_url, facebook_url,
              x_url, instagram_url, wikipedia_url, profile_summary, description, extra_json,
              row_hash, updated_at, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company.source,
                company.company_id,
                company.canonical_name,
                company.display_name,
                company.country,
                company.region,
                company.city,
                canonical_json(company.segments),
                canonical_json(company.industries),
                company.website_url,
                company.linkedin_url,
                company.facebook_url,
                company.x_url,
                company.instagram_url,
                company.wikipedia_url,
                company.profile_summary,
                company.description,
                canonical_json(company.extra),
                row_hash,
                fetched_at,
                run_id,
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
        inserted_companies = 0

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

            for company in batch.companies:
                inserted_companies += self._insert_company(company, fetched_at=ts, run_id=run_id)

        return {
            "intelligence_records": inserted_records,
            "trigger_signals": inserted_signals,
            "timeline_events": inserted_timeline,
            "prospect_scores": inserted_scores,
            "generated_insights": inserted_insights,
            "companies": inserted_companies,
        }

    def parsing_candidates(
        self,
        *,
        parse_version: str = DEFAULT_PARSE_VERSION,
        limit: int = 0,
        force: bool = False,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT ir.id AS source_id,
                   ir.source,
                   ir.dataset,
                   ir.record_key,
                   ir.record_type,
                   ir.company_id,
                   ir.entity,
                   ir.event_time,
                   ir.title,
                   ir.summary,
                   ir.region,
                   ir.industry,
                   ir.lang,
                   ir.evidence_url,
                   ir.payload_json,
                   ir.content_hash,
                   ir.run_id
            FROM intelligence_records ir
        """
        params: list[Any] = []
        if not force:
            sql += """
            LEFT JOIN parsed_documents pd
              ON pd.source_table = 'intelligence_records'
             AND pd.source_id = ir.id
             AND pd.source_content_hash = ir.content_hash
             AND pd.parse_version = ?
            WHERE pd.id IS NULL
            """
            params.append(parse_version)
        sql += " ORDER BY ir.id"
        if limit > 0:
            sql += " LIMIT ?"
            params.append(limit)

        rows = self.conn.execute(sql, tuple(params)).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["payload_json"] = json.loads(item["payload_json"]) if item.get("payload_json") else {}
            item["source_table"] = "intelligence_records"
            out.append(item)
        return out

    def persist_parsed_document(
        self,
        *,
        source_row: dict[str, Any],
        parsed: ParsedDocument,
        parse_version: str = DEFAULT_PARSE_VERSION,
        run_id: str,
        parsed_at: str | None = None,
        extra_warnings: list[str] | None = None,
        replace: bool = False,
    ) -> int:
        parsed_ts = parsed_at or utc_now_iso()
        existing = self.conn.execute(
            """
            SELECT id
            FROM parsed_documents
            WHERE source_table = ? AND source_id = ? AND source_content_hash = ? AND parse_version = ?
            """,
            (
                source_row["source_table"],
                source_row["source_id"],
                source_row["content_hash"],
                parse_version,
            ),
        ).fetchone()
        if existing is not None and not replace:
            return 0

        management = parsed.management_discussion
        warnings = list(extra_warnings or []) + list(parsed.warnings)
        metadata = dict(parsed.metadata or {})
        values = (
            source_row["source_table"],
            source_row["source_id"],
            source_row["content_hash"],
            source_row.get("record_key"),
            source_row.get("source"),
            source_row.get("dataset"),
            source_row.get("company_id"),
            source_row.get("entity"),
            parsed.title,
            parsed.summary,
            parsed.media_type,
            source_row.get("lang"),
            metadata.get("resolved_file_path") or metadata.get("file_path"),
            source_row.get("evidence_url"),
            parsed.parser_name,
            parsed.backend_name,
            parse_version,
            parsed.parse_status,
            metadata.get("ocr_status"),
            metadata.get("xbrl_status"),
            parsed.text,
            parsed.to_rag_text(),
            canonical_json(warnings),
            canonical_json(metadata),
            management.summary if management else None,
            canonical_json(management.highlights if management else []),
            canonical_json(management.source_sections if management else []),
            len(parsed.sections),
            len(parsed.tables),
            len(parsed.metrics),
            len(parsed.risk_factors),
            len(parsed.business_events),
            parsed_ts,
            run_id,
        )
        if existing is None:
            row = self.conn.execute(
                """
                INSERT INTO parsed_documents(
                  source_table, source_id, source_content_hash, source_record_key, source, dataset,
                  company_id, entity, title, summary, media_type, lang, file_path, evidence_url,
                  parser_name, backend_name, parse_version, parse_status, ocr_status, xbrl_status,
                  content_text, search_text, warnings_json, metadata_json,
                  management_discussion_summary, management_discussion_highlights_json,
                  management_discussion_source_sections_json,
                  section_count, table_count, metric_count, risk_factor_count, business_event_count,
                  parsed_at, run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            document_id = int(row.lastrowid)
        else:
            document_id = int(existing["id"])
            with self.conn:
                self.conn.execute("DELETE FROM parsed_sections WHERE document_id = ?", (document_id,))
                self.conn.execute("DELETE FROM parsed_tables WHERE document_id = ?", (document_id,))
                self.conn.execute("DELETE FROM parsed_metrics WHERE document_id = ?", (document_id,))
                self.conn.execute("DELETE FROM parsed_risk_factors WHERE document_id = ?", (document_id,))
                self.conn.execute("DELETE FROM parsed_business_events WHERE document_id = ?", (document_id,))
                self.conn.execute(
                    """
                    UPDATE parsed_documents
                    SET source_record_key = ?, source = ?, dataset = ?, company_id = ?, entity = ?, title = ?, summary = ?,
                        media_type = ?, lang = ?, file_path = ?, evidence_url = ?, parser_name = ?, backend_name = ?,
                        parse_status = ?, ocr_status = ?, xbrl_status = ?, content_text = ?, search_text = ?,
                        warnings_json = ?, metadata_json = ?, management_discussion_summary = ?,
                        management_discussion_highlights_json = ?, management_discussion_source_sections_json = ?,
                        section_count = ?, table_count = ?, metric_count = ?, risk_factor_count = ?, business_event_count = ?,
                        parsed_at = ?, run_id = ?
                    WHERE id = ?
                    """,
                    (
                        source_row.get("record_key"),
                        source_row.get("source"),
                        source_row.get("dataset"),
                        source_row.get("company_id"),
                        source_row.get("entity"),
                        parsed.title,
                        parsed.summary,
                        parsed.media_type,
                        source_row.get("lang"),
                        metadata.get("resolved_file_path") or metadata.get("file_path"),
                        source_row.get("evidence_url"),
                        parsed.parser_name,
                        parsed.backend_name,
                        parsed.parse_status,
                        metadata.get("ocr_status"),
                        metadata.get("xbrl_status"),
                        parsed.text,
                        parsed.to_rag_text(),
                        canonical_json(warnings),
                        canonical_json(metadata),
                        management.summary if management else None,
                        canonical_json(management.highlights if management else []),
                        canonical_json(management.source_sections if management else []),
                        len(parsed.sections),
                        len(parsed.tables),
                        len(parsed.metrics),
                        len(parsed.risk_factors),
                        len(parsed.business_events),
                        parsed_ts,
                        run_id,
                        document_id,
                    ),
                )
        for index, section in enumerate(parsed.sections):
            self.conn.execute(
                """
                INSERT INTO parsed_sections(document_id, section_index, heading, text, level, section_type, page_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    index,
                    section.heading,
                    section.text,
                    section.level,
                    section.section_type,
                    section.page_number,
                ),
            )
        for index, table in enumerate(parsed.tables):
            self.conn.execute(
                """
                INSERT INTO parsed_tables(document_id, table_index, title, headers_json, rows_json, page_number)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    index,
                    table.title,
                    canonical_json(table.headers),
                    canonical_json(table.rows),
                    table.page_number,
                ),
            )
        for index, metric in enumerate(parsed.metrics):
            self.conn.execute(
                """
                INSERT INTO parsed_metrics(document_id, metric_index, name, value, unit, period, context, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    index,
                    metric.name,
                    metric.value,
                    metric.unit,
                    metric.period,
                    metric.context,
                    metric.confidence,
                ),
            )
        for index, risk in enumerate(parsed.risk_factors):
            self.conn.execute(
                """
                INSERT INTO parsed_risk_factors(document_id, risk_index, category, description, severity, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    index,
                    risk.category,
                    risk.description,
                    risk.severity,
                    risk.confidence,
                ),
            )
        for index, event in enumerate(parsed.business_events):
            self.conn.execute(
                """
                INSERT INTO parsed_business_events(document_id, event_index, event_type, summary, event_date, parties_json, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    index,
                    event.event_type,
                    event.summary,
                    event.event_date,
                    canonical_json(event.parties),
                    event.confidence,
                ),
            )
        self.conn.commit()
        return 1
