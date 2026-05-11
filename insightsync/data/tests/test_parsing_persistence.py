from __future__ import annotations

import unittest
from pathlib import Path

from insightsync.data.pipeline.models import CollectionBatch, IntelligenceRecord
from insightsync.data.pipeline.parser_runner import ParsingConfig, run_parsing_once
from insightsync.data.pipeline.storage import SQLiteRepository


class ParsingPersistenceTests(unittest.TestCase):
    def test_run_parsing_once_persists_structured_outputs(self) -> None:
        root = Path(".tmp_parsing_persistence_runtime").resolve()
        root.mkdir(parents=True, exist_ok=True)
        db_path = root / "insightsync.db"
        raw_dir = root / "raw"
        if db_path.exists():
            db_path.unlink()
        if raw_dir.exists():
            for child in raw_dir.iterdir():
                if child.is_file():
                    child.unlink()
        else:
            raw_dir.mkdir(parents=True, exist_ok=True)

        with SQLiteRepository(db_path) as repo:
            repo.start_run("run-1", started_at="2026-04-22T00:00:00Z")
            batch = CollectionBatch(
                source="hkex",
                intelligence_records=[
                    IntelligenceRecord(
                        source="hkex",
                        dataset="annual_report",
                        record_key="alpha-2025",
                        record_type="document",
                        event_time="2026-04-01",
                        company_id="alpha",
                        entity="Alpha Holdings",
                        title="Alpha Annual Report",
                        summary="Annual report",
                        region="Hong Kong",
                        industry="Financials",
                        tags=["hkex", "annual_report"],
                        payload={
                            "management_discussion": (
                                "Management discussion and analysis. Revenue grew to HK$12.5 billion in FY2025. "
                                "The group signed a partnership agreement in Shenzhen on 2026-04-01."
                            ),
                            "risk_note": "Regulatory risk increased because of capital rules.",
                        },
                        evidence_url="https://example.com/report",
                        lang="en",
                        raw=None,
                    )
                ],
            )
            repo.persist_batch("run-1", batch, fetched_at="2026-04-22T00:00:00Z")

        summary = run_parsing_once(ParsingConfig(db_path=db_path, raw_dir=raw_dir))

        self.assertEqual(summary["inserted"], 1)

        with SQLiteRepository(db_path) as repo:
            document_row = repo.conn.execute(
                """
                SELECT parser_name, backend_name, parse_status, section_count, metric_count, risk_factor_count,
                       business_event_count, management_discussion_summary
                FROM parsed_documents
                """
            ).fetchone()
            self.assertIsNotNone(document_row)
            self.assertEqual(document_row["parser_name"], "json")
            self.assertEqual(document_row["parse_status"], "success")
            self.assertGreaterEqual(int(document_row["section_count"]), 1)
            self.assertGreaterEqual(int(document_row["metric_count"]), 1)
            self.assertGreaterEqual(int(document_row["risk_factor_count"]), 1)
            self.assertGreaterEqual(int(document_row["business_event_count"]), 1)
            self.assertTrue(document_row["management_discussion_summary"])

            section_count = repo.conn.execute("SELECT COUNT(*) FROM parsed_sections").fetchone()[0]
            metric_count = repo.conn.execute("SELECT COUNT(*) FROM parsed_metrics").fetchone()[0]
            risk_count = repo.conn.execute("SELECT COUNT(*) FROM parsed_risk_factors").fetchone()[0]
            event_count = repo.conn.execute("SELECT COUNT(*) FROM parsed_business_events").fetchone()[0]
            self.assertGreaterEqual(section_count, 1)
            self.assertGreaterEqual(metric_count, 1)
            self.assertGreaterEqual(risk_count, 1)
            self.assertGreaterEqual(event_count, 1)

    def test_run_parsing_once_reports_genai_disabled_by_default(self) -> None:
        root = Path(".tmp_parsing_default_runtime").resolve()
        root.mkdir(parents=True, exist_ok=True)
        db_path = root / "insightsync.db"
        raw_dir = root / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()

        with SQLiteRepository(db_path) as repo:
            repo.start_run("run-1", started_at="2026-04-22T00:00:00Z")
            batch = CollectionBatch(
                source="news",
                intelligence_records=[
                    IntelligenceRecord(
                        source="news",
                        dataset="article",
                        record_key="alpha-news",
                        record_type="event",
                        event_time="2026-04-01",
                        company_id="alpha",
                        entity="Alpha Holdings",
                        title="Alpha update",
                        summary="Alpha update",
                        region="Hong Kong",
                        industry="Financials",
                        tags=["news"],
                        payload={"body": "Alpha launched UAE operations and faces licensing risk."},
                        evidence_url="https://example.com/news",
                        lang="en",
                        raw=None,
                    )
                ],
            )
            repo.persist_batch("run-1", batch, fetched_at="2026-04-22T00:00:00Z")

        summary = run_parsing_once(ParsingConfig(db_path=db_path, raw_dir=raw_dir))

        self.assertFalse(summary["genai_extraction_enabled"])


if __name__ == "__main__":
    unittest.main()
