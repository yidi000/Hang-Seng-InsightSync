from __future__ import annotations

import json
import unittest
from pathlib import Path
import shutil

from insightsync.data.pipeline.collectors import CompanyDirectoryCollector


class CompanyDirectoryCollectorTests(unittest.TestCase):
    def test_collect_filters_by_segment(self) -> None:
        runtime_dir = Path(".tmp_test_company_directory").resolve()
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir, ignore_errors=True)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        try:
            seed_path = runtime_dir / "companies.json"
            seed_payload = [
                {
                    "name": "Alpha Fintech",
                    "segments": ["fintech", "sme"],
                    "region": "Hong Kong",
                    "profile_urls": {
                        "website": "https://alpha.example.com",
                        "wikipedia": "https://en.wikipedia.org/wiki/Alpha"
                    }
                },
                {
                    "name": "Bay Logistics",
                    "segments": ["cross_border"],
                    "region": "Hong Kong"
                },
                {
                    "name": "Retail Local",
                    "segments": ["retail"],
                    "region": "Hong Kong"
                },
            ]
            seed_path.write_text(json.dumps(seed_payload, ensure_ascii=False), encoding="utf-8")

            collector = CompanyDirectoryCollector(
                raw_dir=runtime_dir,
                seed_path=seed_path,
                segments=("fintech", "cross_border"),
                enable_enrichment=False,
            )
            batch = collector.collect()

            self.assertEqual(len(batch.companies), 2)
            names = {company.canonical_name for company in batch.companies}
            self.assertEqual(names, {"Alpha Fintech", "Bay Logistics"})
            self.assertEqual(batch.counts()["companies"], 2)
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
