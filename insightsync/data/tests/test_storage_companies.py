from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from insightsync.data.pipeline.models import CollectionBatch, CompanyProfile
from insightsync.data.pipeline.storage import SQLiteRepository


class SQLiteRepositoryCompanyTests(unittest.TestCase):
    def test_persist_batch_inserts_companies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            run_id = "run-20260420T000000Z"

            with SQLiteRepository(db_path) as repo:
                repo.start_run(run_id, started_at="2026-04-20T00:00:00Z")
                batch = CollectionBatch(
                    source="company_directory",
                    companies=[
                        CompanyProfile(
                            source="company_directory",
                            company_id="hkg-alpha-fintech",
                            canonical_name="Alpha Fintech",
                            display_name="Alpha Fintech Limited",
                            country="China",
                            region="Hong Kong",
                            city="Hong Kong",
                            segments=["fintech", "sme"],
                            industries=["Payments"],
                            website_url="https://alpha.example.com",
                            linkedin_url=None,
                            facebook_url=None,
                            x_url=None,
                            instagram_url=None,
                            wikipedia_url=None,
                            profile_summary=None,
                            description="Sample",
                            extra={"seed": True},
                        )
                    ],
                )

                inserted = repo.persist_batch(run_id, batch, fetched_at="2026-04-20T00:00:00Z")
                self.assertEqual(inserted["companies"], 1)

                row = repo.conn.execute(
                    "SELECT company_id, canonical_name, segments_json FROM companies WHERE company_id = ?",
                    ("hkg-alpha-fintech",),
                ).fetchone()

                self.assertIsNotNone(row)
                self.assertEqual(row["company_id"], "hkg-alpha-fintech")
                self.assertEqual(row["canonical_name"], "Alpha Fintech")


if __name__ == "__main__":
    unittest.main()
