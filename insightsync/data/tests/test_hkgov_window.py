from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from insightsync.data.pipeline.collectors import HKGovNewsCollector


class _FakeHKGovClient:
    def __init__(self) -> None:
        self.fetch_kwargs: dict[str, object] | None = None

    def fetch_articles(self, **kwargs: object) -> list[dict[str, object]]:
        self.fetch_kwargs = kwargs
        return [
            {
                "title": "Financial services update",
                "description": "Hong Kong financial services update.",
                "link": "https://www.news.gov.hk/test",
                "pubDate": "2026-05-01",
            }
        ]

    def filter_gba_enterprise_news(self, *, articles: list[dict[str, object]], **_kwargs: object) -> list[dict[str, object]]:
        return articles


class HKGovWindowTests(unittest.TestCase):
    def test_start_end_window_does_not_send_default_since_months(self) -> None:
        runtime_dir = Path(".tmp_test_hkgov_window").resolve()
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir, ignore_errors=True)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        try:
            collector = HKGovNewsCollector(
                raw_dir=runtime_dir,
                since_months=None,
                start_date="2026-04-01",
                end_date="2026-05-01",
            )
            fake_client = _FakeHKGovClient()
            collector.client = fake_client  # type: ignore[assignment]

            batch = collector.collect()

            self.assertEqual(batch.meta["window"], "2026-04-01_2026-05-01")
            self.assertIsNone(batch.meta["since_months"])
            self.assertIsNotNone(fake_client.fetch_kwargs)
            self.assertIsNone(fake_client.fetch_kwargs["since_months"])
            self.assertEqual(fake_client.fetch_kwargs["start_date"], "2026-04-01")
            self.assertEqual(fake_client.fetch_kwargs["end_date"], "2026-05-01")
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
