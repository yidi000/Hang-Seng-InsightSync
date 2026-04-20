from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from insightsync.data.pipeline.company_mapper import run_company_mapping_once
from insightsync.data.pipeline.models import CollectionBatch, CompanyProfile, IntelligenceRecord, TriggerSignal
from insightsync.data.pipeline.storage import SQLiteRepository


class CompanyMapperTests(unittest.TestCase):
    def test_sync_market_companies_imports_hkex_and_szse_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"

            with SQLiteRepository(db_path) as repo:
                repo.start_run("run-ingest", started_at="2026-04-21T00:00:00Z")
                batch = CollectionBatch(
                    source="test_seed",
                    intelligence_records=[
                        IntelligenceRecord(
                            source="szse_cninfo",
                            dataset="announcements",
                            record_key="szse-1",
                            record_type="event",
                            event_time="2026-04-20",
                            company_id="000001",
                            entity="CN",
                            title="平安银行公告",
                            summary="年报公告",
                            region="China",
                            industry="Listed Companies",
                            tags=["szse_cninfo", "announcements"],
                            payload={"stock_code": "000001", "stock_name": "平安银行"},
                            evidence_url=None,
                            lang="zh",
                            raw=None,
                        ),
                        IntelligenceRecord(
                            source="hkex_disclosure",
                            dataset="annual_reports_pdf",
                            record_key="hkex-1",
                            record_type="document",
                            event_time="2026-04-20",
                            company_id="0005",
                            entity="HKG",
                            title="HSBC Holdings annual report",
                            summary="Annual report",
                            region="Hong Kong",
                            industry="Listed Companies",
                            tags=["hkex_disclosure", "annual_report"],
                            payload={"stock_code": "0005", "company_name": "HSBC Holdings"},
                            evidence_url=None,
                            lang="en",
                            raw=None,
                        ),
                    ],
                )
                repo.persist_batch("run-ingest", batch, fetched_at="2026-04-21T00:00:00Z")
                repo.finish_run("run-ingest", status="success", message="ok", summary={"ok": True})

            summary = run_company_mapping_once(
                db_path,
                sync_market_companies=True,
                backfill_company_ids=False,
                dry_run=False,
            )

            self.assertEqual(summary["status"], "success")
            self.assertGreaterEqual(summary["sync_market_companies"]["inserted_companies"], 2)

            with SQLiteRepository(db_path) as repo:
                row_szse = repo.conn.execute(
                    "SELECT company_id, canonical_name FROM companies WHERE company_id = ? ORDER BY id DESC LIMIT 1",
                    ("000001",),
                ).fetchone()
                row_hkex = repo.conn.execute(
                    "SELECT company_id, canonical_name FROM companies WHERE company_id = ? ORDER BY id DESC LIMIT 1",
                    ("0005",),
                ).fetchone()

                self.assertIsNotNone(row_szse)
                self.assertIsNotNone(row_hkex)
                self.assertEqual(row_szse["canonical_name"], "平安银行")
                self.assertEqual(row_hkex["canonical_name"], "HSBC Holdings")

    def test_backfill_company_ids_updates_records_and_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"

            with SQLiteRepository(db_path) as repo:
                repo.start_run("run-seed", started_at="2026-04-21T00:00:00Z")
                batch = CollectionBatch(
                    source="test_seed",
                    companies=[
                        CompanyProfile(
                            source="company_directory",
                            company_id="hkg-alpha-fintech",
                            canonical_name="Alpha Fintech",
                            display_name=None,
                            country="China",
                            region="Hong Kong",
                            city="Hong Kong",
                            segments=["fintech"],
                            industries=["Payments"],
                            website_url=None,
                            linkedin_url=None,
                            facebook_url=None,
                            x_url=None,
                            instagram_url=None,
                            wikipedia_url=None,
                            profile_summary=None,
                            description="Seed",
                            extra={},
                        )
                    ],
                    intelligence_records=[
                        IntelligenceRecord(
                            source="investhk_news",
                            dataset="news_items",
                            record_key="news-1",
                            record_type="event",
                            event_time="2026-04-20",
                            company_id=None,
                            entity="HKG",
                            title="Alpha Fintech expands into UAE",
                            summary="Alpha Fintech announced cross-border growth",
                            region="Hong Kong",
                            industry="Investment / Business Development",
                            tags=["investhk_news", "news"],
                            payload={"title": "Alpha Fintech expands into UAE"},
                            evidence_url=None,
                            lang="en",
                            raw=None,
                        )
                    ],
                    trigger_signals=[
                        TriggerSignal(
                            source="hk_gov_news",
                            dataset="finance_news_signals",
                            signal_key="signal-1",
                            signal_type="growth",
                            event_time="2026-04-20",
                            company_id=None,
                            entity="HKG",
                            indicator="headline",
                            value_num=None,
                            value_text=None,
                            unit=None,
                            signal_text="Policy support for Alpha Fintech in Hong Kong",
                            evidence_refs=[],
                            extra={},
                        )
                    ],
                )
                repo.persist_batch("run-seed", batch, fetched_at="2026-04-21T00:00:00Z")
                repo.finish_run("run-seed", status="success", message="ok", summary={"ok": True})

            summary = run_company_mapping_once(
                db_path,
                sync_market_companies=False,
                backfill_company_ids=True,
                dry_run=False,
            )

            self.assertEqual(summary["status"], "success")
            self.assertGreaterEqual(summary["backfill_company_ids"]["intelligence_records_updated"], 1)
            self.assertGreaterEqual(summary["backfill_company_ids"]["trigger_signals_updated"], 1)

            with SQLiteRepository(db_path) as repo:
                rec = repo.conn.execute(
                    "SELECT company_id FROM intelligence_records WHERE record_key = ?",
                    ("news-1",),
                ).fetchone()
                sig = repo.conn.execute(
                    "SELECT company_id FROM trigger_signals WHERE signal_key = ?",
                    ("signal-1",),
                ).fetchone()

                self.assertEqual(rec["company_id"], "hkg-alpha-fintech")
                self.assertEqual(sig["company_id"], "hkg-alpha-fintech")


if __name__ == "__main__":
    unittest.main()
