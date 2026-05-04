from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from insightsync.data.pipeline.collectors import CENSTATDCollector


class _FakeCENSTATDClient:
    def retail_sales(self, **_: object) -> dict:
        return {
            "header": {"title": "Retail Sales"},
            "dataSet": [
                {
                    "OUTLET_TYPE": "",
                    "OUTLET_TYPEDesc": "Total",
                    "freq": "M",
                    "period": "202602",
                    "sv": "VAL_RS",
                    "svDesc": "HK$ million",
                    "figure": 31400,
                    "sd_value": "p",
                }
            ],
        }

    def external_merchandise_trade(self, **_: object) -> dict:
        return {
            "header": {"title": "External merchandise trade"},
            "dataSet": [
                {
                    "freq": "YTM",
                    "period": "202603",
                    "sv": "VAL_TX",
                    "svDesc": "HK$ million",
                    "figure": 987654,
                    "sd_value": "",
                }
            ],
        }


class CENSTATDCollectorTests(unittest.TestCase):
    def test_collect_builds_records_and_signals(self) -> None:
        runtime_dir = Path(".tmp_test_censtatd").resolve()
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir, ignore_errors=True)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        try:
            collector = CENSTATDCollector(raw_dir=runtime_dir, language="en")
            collector.client = _FakeCENSTATDClient()

            batch = collector.collect()

            self.assertEqual(batch.source, "censtatd")
            self.assertEqual(batch.meta["language"], "en")
            self.assertEqual(len(batch.intelligence_records), 4)
            self.assertEqual(len(batch.trigger_signals), 2)

            datasets = {item.dataset for item in batch.intelligence_records}
            self.assertIn("retail_sales", datasets)
            self.assertIn("external_merchandise_trade", datasets)

            first_signal = batch.trigger_signals[0]
            self.assertEqual(first_signal.entity, "HKG")
            self.assertIn(first_signal.dataset, {"retail_sales", "external_merchandise_trade"})
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
