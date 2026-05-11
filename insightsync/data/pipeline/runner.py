from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .collectors import (
    ADBCollector,
    CENSTATDCollector,
    CompanyDirectoryCollector,
    DongfangAKShareCollector,
    DongfangCSVCollector,
    GuangdongStatsCollector,
    HKGovNewsCollector,
    HKEXDisclosureCollector,
    HKMACollector,
    InvestHKNewsCollector,
    KPMGCollector,
    SZSEAnnouncementCollector,
)
from .storage import SQLiteRepository
from .utils import utc_now_iso

DEFAULT_SOURCES = ("hkma", "adb", "kpmg", "guangdong", "investhk", "company")


@dataclass(slots=True)
class PipelineConfig:
    db_path: Path = Path("insightsync/data/storage/insightsync.db")
    raw_dir: Path = Path("insightsync/data/storage/raw")
    sources: tuple[str, ...] = DEFAULT_SOURCES

    hkma_pagesize: int = 200
    hkma_max_pages: int = 4
    hkma_languages: tuple[str, ...] = ("en", "tc")

    adb_economy: str = "HKG"
    adb_start_year: int = datetime.now().year - 8
    adb_end_year: int = datetime.now().year
    adb_min_interval_seconds: float = 3.2

    censtatd_language: str = "en"
    censtatd_include_full_series: bool = True
    censtatd_request_timeout_seconds: int = 60

    guangdong_years: tuple[int, ...] = (datetime.now().year, datetime.now().year - 1)
    guangdong_max_links_per_category: int = 20
    guangdong_max_tables_per_page: int = 2
    guangdong_max_rows_per_table: int = 500

    kpmg_pdf_url: str | None = None

    investhk_language: str = "zh-cn"
    investhk_json_url: str | None = None
    investhk_include_article_text: bool = False
    investhk_max_items: int = 500
    investhk_request_timeout_seconds: int = 30
    investhk_article_delay_seconds: float = 0.3

    hkgov_language: str = "en"
    hkgov_since_months: int | None = 3
    hkgov_since_days: int | None = None
    hkgov_start_date: str | None = None
    hkgov_end_date: str | None = None
    hkgov_max_items: int = 1000
    hkgov_filter_limit: int = 50
    hkgov_require_geo_and_business: bool = True
    hkgov_request_timeout_seconds: int = 60

    hkex_list_url: str | None = None
    hkex_target_year: str | None = None
    hkex_target_month: str | None = None
    hkex_max_items: int = 200
    hkex_request_timeout_seconds: int = 30
    hkex_use_selenium_fallback: bool = True
    hkex_headless: bool = True
    hkex_download_wait_seconds: int = 30
    hkex_page_wait_seconds: float = 1.0

    szse_days_back: int = 180
    szse_start_date: str | None = None
    szse_end_date: str | None = None
    szse_max_records: int = 50000
    szse_page_size: int = 30
    szse_delay_seconds: float = 0.3
    szse_plate: str = "sz"
    szse_stock: str = ""
    szse_tab_name: str = "fulltext"
    szse_request_timeout_seconds: int = 15

    company_seed_path: Path | None = None
    company_segments: tuple[str, ...] = ("sme", "fintech", "cross_border")
    company_max_items: int = 500
    company_enable_enrichment: bool = False
    company_request_timeout_seconds: int = 15

    dongfang_csv_paths: tuple[str, ...] = ()
    dongfang_fetch_enabled: bool = False
    dongfang_fetch_markets: tuple[str, ...] = ("northbound", "shanghai_connect", "shenzhen_connect")
    dongfang_fetch_retry: int = 3
    dongfang_fetch_sleep_seconds: float = 1.0
    dongfang_snapshot_date: str | None = None
    dongfang_min_increase_value: float = 0.0
    dongfang_min_holding_ratio: float = 0.0
    dongfang_top_n_rank_signal: int = 20

    runtime_meta: dict[str, Any] = field(default_factory=dict)


def _normalize_sources(values: tuple[str, ...] | list[str] | set[str]) -> tuple[str, ...]:
    out: list[str] = []
    for src in values:
        key = src.strip().lower()
        if not key:
            continue
        if key in ("adb_kidb", "adb"):
            key = "adb"
        if key in ("censtatd", "csd", "census", "census_statistics", "hong_kong_statistics"):
            key = "censtatd"
        if key in ("guangdong_stats", "gd", "guangdong"):
            key = "guangdong"
        if key in ("investhk_news", "investhk-news", "investhk"):
            key = "investhk"
        if key in ("hkgov", "hk-gov", "hk_gov", "hkgov_news", "hk_gov_news", "newsgov"):
            key = "hkgov"
        if key in ("hkex_disclosure", "hkex-disclosure", "hkex"):
            key = "hkex"
        if key in ("szse", "szse-announcement", "szse_announcement", "cninfo", "cninfo_szse", "szse_cninfo"):
            key = "szse"
        if key in ("company", "companies", "company-directory", "company_directory", "company_master"):
            key = "company"
        if key in ("dongfang", "eastmoney", "dongfang_eastmoney", "eastmoney_connect"):
            key = "dongfang"
        if key not in out:
            out.append(key)
    return tuple(out)


def build_collectors(config: PipelineConfig) -> list[Any]:
    sources = _normalize_sources(config.sources)
    collectors: list[Any] = []
    for src in sources:
        if src == "hkma":
            collectors.append(
                HKMACollector(
                    pagesize=config.hkma_pagesize,
                    max_pages=config.hkma_max_pages,
                    languages=config.hkma_languages,
                )
            )
            continue
        if src == "adb":
            collectors.append(
                ADBCollector(
                    economy=config.adb_economy,
                    start_year=config.adb_start_year,
                    end_year=config.adb_end_year,
                    min_interval_seconds=config.adb_min_interval_seconds,
                )
            )
            continue
        if src == "censtatd":
            collectors.append(
                CENSTATDCollector(
                    raw_dir=config.raw_dir,
                    language=config.censtatd_language,
                    include_full_series=config.censtatd_include_full_series,
                    request_timeout_seconds=config.censtatd_request_timeout_seconds,
                )
            )
            continue
        if src == "kpmg":
            collectors.append(KPMGCollector(raw_dir=config.raw_dir, url=config.kpmg_pdf_url))
            continue
        if src == "investhk":
            collectors.append(
                InvestHKNewsCollector(
                    raw_dir=config.raw_dir,
                    language=config.investhk_language,
                    json_url=config.investhk_json_url,
                    include_article_text=config.investhk_include_article_text,
                    max_items=config.investhk_max_items,
                    request_timeout_seconds=config.investhk_request_timeout_seconds,
                    article_delay_seconds=config.investhk_article_delay_seconds,
                )
            )
            continue
        if src == "hkgov":
            collectors.append(
                HKGovNewsCollector(
                    raw_dir=config.raw_dir,
                    language=config.hkgov_language,
                    since_months=config.hkgov_since_months,
                    since_days=config.hkgov_since_days,
                    start_date=config.hkgov_start_date,
                    end_date=config.hkgov_end_date,
                    max_items=config.hkgov_max_items,
                    filter_limit=config.hkgov_filter_limit,
                    require_geo_and_business=config.hkgov_require_geo_and_business,
                    request_timeout_seconds=config.hkgov_request_timeout_seconds,
                )
            )
            continue
        if src == "hkex":
            collectors.append(
                HKEXDisclosureCollector(
                    raw_dir=config.raw_dir,
                    list_url=config.hkex_list_url,
                    target_year=config.hkex_target_year,
                    target_month=config.hkex_target_month,
                    max_items=config.hkex_max_items,
                    request_timeout_seconds=config.hkex_request_timeout_seconds,
                    use_selenium_fallback=config.hkex_use_selenium_fallback,
                    headless=config.hkex_headless,
                    download_wait_seconds=config.hkex_download_wait_seconds,
                    page_wait_seconds=config.hkex_page_wait_seconds,
                )
            )
            continue
        if src == "szse":
            collectors.append(
                SZSEAnnouncementCollector(
                    raw_dir=config.raw_dir,
                    days_back=config.szse_days_back,
                    start_date=config.szse_start_date,
                    end_date=config.szse_end_date,
                    max_records=config.szse_max_records,
                    page_size=config.szse_page_size,
                    delay_seconds=config.szse_delay_seconds,
                    plate=config.szse_plate,
                    stock=config.szse_stock,
                    tab_name=config.szse_tab_name,
                    request_timeout_seconds=config.szse_request_timeout_seconds,
                )
            )
            continue
        if src == "guangdong":
            collectors.append(
                GuangdongStatsCollector(
                    raw_dir=config.raw_dir,
                    years=config.guangdong_years,
                    max_links_per_category=config.guangdong_max_links_per_category,
                    max_tables_per_page=config.guangdong_max_tables_per_page,
                    max_rows_per_table=config.guangdong_max_rows_per_table,
                )
            )
            continue
        if src == "company":
            collectors.append(
                CompanyDirectoryCollector(
                    raw_dir=config.raw_dir,
                    seed_path=config.company_seed_path,
                    segments=config.company_segments,
                    max_items=config.company_max_items,
                    enable_enrichment=config.company_enable_enrichment,
                    request_timeout_seconds=config.company_request_timeout_seconds,
                )
            )
            continue
        if src == "dongfang":
            if config.dongfang_fetch_enabled:
                collectors.append(
                    DongfangAKShareCollector(
                        raw_dir=config.raw_dir,
                        snapshot_date=config.dongfang_snapshot_date,
                        min_increase_value=config.dongfang_min_increase_value,
                        min_holding_ratio=config.dongfang_min_holding_ratio,
                        top_n_rank_signal=config.dongfang_top_n_rank_signal,
                        fetch_markets=config.dongfang_fetch_markets,
                        retry=config.dongfang_fetch_retry,
                        sleep_seconds=config.dongfang_fetch_sleep_seconds,
                    )
                )
            else:
                collectors.append(
                    DongfangCSVCollector(
                        raw_dir=config.raw_dir,
                        csv_paths=config.dongfang_csv_paths,
                        snapshot_date=config.dongfang_snapshot_date,
                        min_increase_value=config.dongfang_min_increase_value,
                        min_holding_ratio=config.dongfang_min_holding_ratio,
                        top_n_rank_signal=config.dongfang_top_n_rank_signal,
                    )
                )
            continue
        raise ValueError(f"Unsupported source: {src}")
    return collectors


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ")


def run_ingestion_once(config: PipelineConfig) -> dict[str, Any]:
    cfg = replace(config)
    cfg.db_path = Path(cfg.db_path).expanduser().resolve()
    cfg.raw_dir = Path(cfg.raw_dir).expanduser().resolve()
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)

    run_id = _new_run_id()
    started_at = utc_now_iso()

    with SQLiteRepository(cfg.db_path) as repo:
        repo.start_run(run_id, started_at=started_at)
        source_results: dict[str, Any] = {}
        errors: list[str] = []

        for collector in build_collectors(cfg):
            source_name = collector.source
            t0 = time.perf_counter()
            try:
                batch = collector.collect()
                inserted = repo.persist_batch(run_id, batch)
                elapsed = round(time.perf_counter() - t0, 3)
                source_results[source_name] = {
                    "status": "ok",
                    "duration_seconds": elapsed,
                    "fetched": batch.counts(),
                    "inserted": inserted,
                    "meta": batch.meta,
                }
            except Exception as exc:  # noqa: BLE001
                elapsed = round(time.perf_counter() - t0, 3)
                msg = str(exc)
                errors.append(f"{source_name}: {msg}")
                source_results[source_name] = {
                    "status": "error",
                    "duration_seconds": elapsed,
                    "error": msg,
                }

        if not errors:
            status = "success"
            message = "all sources completed"
        elif len(errors) == len(source_results):
            status = "failed"
            message = "; ".join(errors)
        else:
            status = "partial_success"
            message = "; ".join(errors)

        summary = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": utc_now_iso(),
            "status": status,
            "db_path": str(cfg.db_path),
            "raw_dir": str(cfg.raw_dir),
            "sources": source_results,
            "runtime_meta": cfg.runtime_meta,
        }
        repo.finish_run(run_id, status=status, message=message, summary=summary)
        return summary


def run_scheduler_loop(config: PipelineConfig, *, interval_minutes: float) -> None:
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be > 0")
    sleep_seconds = max(5.0, float(interval_minutes) * 60.0)
    while True:
        started = time.monotonic()
        run_ingestion_once(config)
        elapsed = time.monotonic() - started
        wait = max(1.0, sleep_seconds - elapsed)
        time.sleep(wait)

