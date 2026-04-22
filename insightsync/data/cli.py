from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from insightsync.parsing import DEFAULT_PARSE_VERSION

from .pipeline.company_mapper import run_company_mapping_once
from .pipeline.parser_runner import ParsingConfig, run_parsing_once
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
    parser.add_argument("--sources", default="hkma,adb,kpmg,guangdong,investhk,company")

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

    parser.add_argument("--hkgov-language", default="en")
    parser.add_argument("--hkgov-since-months", type=int, default=3)
    parser.add_argument("--hkgov-since-days", type=int, default=None)
    parser.add_argument("--hkgov-start-date", default=None)
    parser.add_argument("--hkgov-end-date", default=None)
    parser.add_argument("--hkgov-max-items", type=int, default=1000)
    parser.add_argument("--hkgov-filter-limit", type=int, default=50)
    parser.add_argument("--hkgov-no-require-geo-and-business", action="store_true")
    parser.add_argument("--hkgov-request-timeout-seconds", type=int, default=60)

    parser.add_argument("--hkex-list-url", default=None)
    parser.add_argument("--hkex-target-year", default=None)
    parser.add_argument("--hkex-target-month", default=None)
    parser.add_argument("--hkex-max-items", type=int, default=200)
    parser.add_argument("--hkex-request-timeout-seconds", type=int, default=30)
    parser.add_argument("--hkex-use-selenium-fallback", action="store_true")
    parser.add_argument("--hkex-no-headless", action="store_true")
    parser.add_argument("--hkex-download-wait-seconds", type=int, default=30)
    parser.add_argument("--hkex-page-wait-seconds", type=float, default=1.0)

    parser.add_argument("--szse-days-back", type=int, default=180)
    parser.add_argument("--szse-start-date", default=None)
    parser.add_argument("--szse-end-date", default=None)
    parser.add_argument("--szse-max-records", type=int, default=50000)
    parser.add_argument("--szse-page-size", type=int, default=30)
    parser.add_argument("--szse-delay-seconds", type=float, default=0.3)
    parser.add_argument("--szse-plate", default="sz")
    parser.add_argument("--szse-stock", default="")
    parser.add_argument("--szse-tab-name", default="fulltext")
    parser.add_argument("--szse-request-timeout-seconds", type=int, default=15)

    parser.add_argument("--company-seed-path", default=None)
    parser.add_argument("--company-segments", default="sme,fintech,cross_border")
    parser.add_argument("--company-max-items", type=int, default=500)
    parser.add_argument("--company-enable-enrichment", action="store_true")
    parser.add_argument("--company-request-timeout-seconds", type=int, default=15)

    parser.add_argument("--sync-market-companies", action="store_true")
    parser.add_argument("--backfill-company-ids", action="store_true")
    parser.add_argument("--mapping-dry-run", action="store_true")
    parser.add_argument("--mapping-limit", type=int, default=0)
    parser.add_argument("--run-parsing", action="store_true")
    parser.add_argument("--parse-force", action="store_true")
    parser.add_argument("--parse-limit", type=int, default=0)
    parser.add_argument("--parse-version", default=DEFAULT_PARSE_VERSION)
    parser.add_argument("--skip-ingestion", action="store_true")

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
        hkgov_language=args.hkgov_language,
        hkgov_since_months=args.hkgov_since_months,
        hkgov_since_days=args.hkgov_since_days,
        hkgov_start_date=args.hkgov_start_date,
        hkgov_end_date=args.hkgov_end_date,
        hkgov_max_items=args.hkgov_max_items,
        hkgov_filter_limit=args.hkgov_filter_limit,
        hkgov_require_geo_and_business=not args.hkgov_no_require_geo_and_business,
        hkgov_request_timeout_seconds=args.hkgov_request_timeout_seconds,
        hkex_list_url=args.hkex_list_url,
        hkex_target_year=args.hkex_target_year,
        hkex_target_month=args.hkex_target_month,
        hkex_max_items=args.hkex_max_items,
        hkex_request_timeout_seconds=args.hkex_request_timeout_seconds,
        hkex_use_selenium_fallback=args.hkex_use_selenium_fallback,
        hkex_headless=not args.hkex_no_headless,
        hkex_download_wait_seconds=args.hkex_download_wait_seconds,
        hkex_page_wait_seconds=args.hkex_page_wait_seconds,
        szse_days_back=args.szse_days_back,
        szse_start_date=args.szse_start_date,
        szse_end_date=args.szse_end_date,
        szse_max_records=args.szse_max_records,
        szse_page_size=args.szse_page_size,
        szse_delay_seconds=args.szse_delay_seconds,
        szse_plate=args.szse_plate,
        szse_stock=args.szse_stock,
        szse_tab_name=args.szse_tab_name,
        szse_request_timeout_seconds=args.szse_request_timeout_seconds,
        company_seed_path=Path(args.company_seed_path) if args.company_seed_path else None,
        company_segments=_parse_csv(args.company_segments),
        company_max_items=args.company_max_items,
        company_enable_enrichment=args.company_enable_enrichment,
        company_request_timeout_seconds=args.company_request_timeout_seconds,
    )

    if args.interval_minutes > 0:
        run_scheduler_loop(config, interval_minutes=args.interval_minutes)
        return

    mapping_summary: dict[str, object] | None = None
    if args.sync_market_companies or args.backfill_company_ids:
        mapping_summary = run_company_mapping_once(
            Path(args.db_path),
            sync_market_companies=args.sync_market_companies,
            backfill_company_ids=args.backfill_company_ids,
            dry_run=args.mapping_dry_run,
            limit=max(0, int(args.mapping_limit)),
        )

    if args.skip_ingestion:
        if mapping_summary is None and not args.run_parsing:
            print(
                json.dumps(
                    {
                        "status": "no_op",
                        "message": "skip-ingestion is enabled and no mapping operation is requested",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        output: dict[str, object] = {}
        if mapping_summary is not None:
            output["company_mapping"] = mapping_summary
        if args.run_parsing:
            output["parsing"] = run_parsing_once(
                ParsingConfig(
                    db_path=Path(args.db_path),
                    raw_dir=Path(args.raw_dir),
                    parse_version=args.parse_version,
                    limit=args.parse_limit,
                    force=args.parse_force,
                )
            )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    summary = run_ingestion_once(config)
    parsing_summary: dict[str, object] | None = None
    if args.run_parsing:
        parsing_summary = run_parsing_once(
            ParsingConfig(
                db_path=Path(args.db_path),
                raw_dir=Path(args.raw_dir),
                parse_version=args.parse_version,
                limit=args.parse_limit,
                force=args.parse_force,
            )
        )
    if mapping_summary is not None:
        output = {
            "ingestion": summary,
            "company_mapping": mapping_summary,
        }
        if parsing_summary is not None:
            output["parsing"] = parsing_summary
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    if parsing_summary is not None:
        print(json.dumps({"ingestion": summary, "parsing": parsing_summary}, ensure_ascii=False, indent=2))
        return

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

