from __future__ import annotations

import unittest
from pathlib import Path
import shutil

from insightsync.data.pipeline.collectors import DongfangAKShareCollector, DongfangCSVCollector


class DongfangCSVCollectorTests(unittest.TestCase):
    def test_collect_builds_company_records_and_signals_from_csv(self) -> None:
        runtime_dir = Path(".tmp_test_dongfang").resolve()
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir, ignore_errors=True)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        try:
            csv_path = runtime_dir / "北向资金持股排行.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "序号,代码,名称,今日收盘价,今日涨跌幅,今日持股-股数,今日持股-市值,今日持股-占流通股比,今日持股-占总股本比,今日增持估计-股数,今日增持估计-市值,今日增持估计-市值增幅,今日增持估计-占流通股比,今日增持估计-占总股本比,所属板块,日期",
                        "1,000001,平安银行,12.34,3.21,1000000,12340000,2.10,1.20,120000,1480800,12.50,0.25,0.12,银行,2026-05-01",
                        "25,300750,宁德时代,220.10,-0.50,500000,110050000,0.90,0.60,0,0,0,0,0,新能源,2026-05-01",
                    ]
                ),
                encoding="utf-8-sig",
            )

            collector = DongfangCSVCollector(
                raw_dir=runtime_dir,
                csv_paths=(str(csv_path),),
                snapshot_date="2026-05-01",
                min_increase_value=1000000,
                min_holding_ratio=1.0,
                top_n_rank_signal=20,
            )
            batch = collector.collect()

            self.assertEqual(batch.source, "dongfang_eastmoney")
            self.assertEqual(batch.meta["files_imported"], 1)
            self.assertEqual(batch.meta["rows_imported"], 2)
            self.assertEqual(len(batch.companies), 2)

            company_ids = {company.company_id for company in batch.companies}
            self.assertEqual(company_ids, {"000001", "300750"})

            snapshot_records = [item for item in batch.intelligence_records if item.dataset == "holdings_csv_snapshot"]
            row_records = [item for item in batch.intelligence_records if item.dataset == "holdings_rank_rows"]
            self.assertEqual(len(snapshot_records), 1)
            self.assertEqual(len(row_records), 2)

            signals = [item for item in batch.trigger_signals if item.company_id == "000001"]
            signal_indicators = {item.indicator for item in signals}
            self.assertIn("ranking", signal_indicators)
            self.assertIn("estimated_increase_value", signal_indicators)
            self.assertIn("holding_float_ratio_pct", signal_indicators)
            self.assertIn("price_and_flow_resonance", signal_indicators)
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)

    def test_southbound_statistics_conversion_matches_csv_schema(self) -> None:
        collector = DongfangAKShareCollector(
            raw_dir=Path(".").resolve(),
            fetch_markets=("southbound",),
        )
        converted = collector._southbound_dataframe_from_statistics(
            [
                {
                    "持股日期": "2026-04-30",
                    "股票代码": "01398",
                    "股票简称": "工商银行",
                    "当日收盘价": 5.32,
                    "当日涨跌幅": -2.9197,
                    "持股数量": 32272785260,
                    "持股市值": 171691217583.2,
                    "持股数量占发行股百分比": 37.17,
                    "持股市值变化-1日": 12345.0,
                }
            ]
        )
        self.assertEqual(
            list(converted.columns),
            [
                "序号",
                "代码",
                "名称",
                "今日收盘价",
                "今日涨跌幅",
                "今日持股-股数",
                "今日持股-市值",
                "今日持股-占流通股比",
                "今日持股-占总股本比",
                "今日增持估计-股数",
                "今日增持估计-市值",
                "今日增持估计-市值增幅",
                "今日增持估计-占流通股比",
                "今日增持估计-占总股本比",
                "所属板块",
                "日期",
            ],
        )
        row = converted.iloc[0].to_dict()
        self.assertEqual(row["代码"], "01398")
        self.assertEqual(row["名称"], "工商银行")
        self.assertEqual(row["今日持股-市值"], 171691217583.2)
        self.assertEqual(row["今日增持估计-市值"], 12345.0)
        self.assertEqual(row["所属板块"], "Hong Kong Connect")
        self.assertEqual(row["日期"], "2026-04-30")


if __name__ == "__main__":
    unittest.main()
