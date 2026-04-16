from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .pipeline.runner import PipelineConfig, run_ingestion_once, run_scheduler_loop


def _parse_csv(raw: str) -> tuple[str, ...]:
    return tuple([item.strip() for item in raw.split(",") if item.strip()])


def _parse_years(raw: str) -> tuple[int, ...]:
    out: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if token:
            out.append(int(token))
    return tuple(out)


def build_parser() -> argparse.ArgumentParser:
    current_year = datetime.now().year
    parser = argparse.ArgumentParser(description="InsightSync data pipeline")
    parser.add_argument("--db-path", default="insightsync/data/storage/insightsync.db")
    parser.add_argument("--raw-dir", default="insightsync/data/storage/raw")
    parser.add_argument("--sources", default="hkma,adb,kpmg,guangdong,investhk")

    parser.add_argument("--hkma-pagesize", type=int, default=200)
    parser.add_argument("--hkma-max-pages", type=int, default=4)
    parser.add_argument("--hkma-languages", default="en,tc")

    parser.add_argument("--adb-economy", default="HKG")
    parser.add_argument("--adb-start-year", type=int, default=current_year - 8)
    parser.add_argument("--adb-end-year", type=int, default=current_year)
    parser.add_argument("--adb-min-interval-seconds", type=float, default=3.2)

    parser.add_argument("--guangdong-years", default=f"{current_year},{current_year - 1}")
    parser.add_argument("--guangdong-max-links-per-category", type=int, default=20)
    parser.add_argument("--guangdong-max-tables-per-page", type=int, default=2)
    parser.add_argument("--guangdong-max-rows-per-table", type=int, default=500)

    parser.add_argument("--kpmg-pdf-url", default=None)

    parser.add_argument("--investhk-language", default="zh-cn")
    parser.add_argument("--investhk-json-url", default=None)
    parser.add_argument("--investhk-include-article-text", action="store_true")
    parser.add_argument("--investhk-max-items", type=int, default=500)
    parser.add_argument("--investhk-request-timeout-seconds", type=int, default=30)
    parser.add_argument("--investhk-article-delay-seconds", type=float, default=0.3)

    parser.add_argument("--interval-minutes", type=float, default=0.0)
    parser.add_argument("--once", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = PipelineConfig(
        db_path=Path(args.db_path),
        raw_dir=Path(args.raw_dir),
        sources=_parse_csv(args.sources),
        hkma_pagesize=args.hkma_pagesize,
        hkma_max_pages=args.hkma_max_pages,
        hkma_languages=_parse_csv(args.hkma_languages),
        adb_economy=args.adb_economy,
        adb_start_year=args.adb_start_year,
        adb_end_year=args.adb_end_year,
        adb_min_interval_seconds=args.adb_min_interval_seconds,
        guangdong_years=_parse_years(args.guangdong_years),
        guangdong_max_links_per_category=args.guangdong_max_links_per_category,
        guangdong_max_tables_per_page=args.guangdong_max_tables_per_page,
        guangdong_max_rows_per_table=args.guangdong_max_rows_per_table,
        kpmg_pdf_url=args.kpmg_pdf_url,
        investhk_language=args.investhk_language,
        investhk_json_url=args.investhk_json_url,
        investhk_include_article_text=args.investhk_include_article_text,
        investhk_max_items=args.investhk_max_items,
        investhk_request_timeout_seconds=args.investhk_request_timeout_seconds,
        investhk_article_delay_seconds=args.investhk_article_delay_seconds,
    )

    if args.interval_minutes > 0:
        run_scheduler_loop(config, interval_minutes=args.interval_minutes)
        return

    summary = run_ingestion_once(config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

