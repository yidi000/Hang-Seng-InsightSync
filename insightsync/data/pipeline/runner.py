from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .collectors import (
    ADBCollector,
    GuangdongStatsCollector,
    HKEXDisclosureCollector,
    HKMACollector,
    InvestHKNewsCollector,
    KPMGCollector,
)
from .storage import SQLiteRepository
from .utils import utc_now_iso

DEFAULT_SOURCES = ("hkma", "adb", "kpmg", "guangdong", "investhk")


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

    hkex_list_url: str | None = None
    hkex_target_year: str | None = None
    hkex_target_month: str | None = None
    hkex_max_items: int = 200
    hkex_request_timeout_seconds: int = 30
    hkex_use_selenium_fallback: bool = True
    hkex_headless: bool = True
    hkex_download_wait_seconds: int = 30
    hkex_page_wait_seconds: float = 1.0

    runtime_meta: dict[str, Any] = field(default_factory=dict)


def _normalize_sources(values: tuple[str, ...] | list[str] | set[str]) -> tuple[str, ...]:
    out: list[str] = []
    for src in values:
        key = src.strip().lower()
        if not key:
            continue
        if key in ("adb_kidb", "adb"):
            key = "adb"
        if key in ("guangdong_stats", "gd", "guangdong"):
            key = "guangdong"
        if key in ("investhk_news", "investhk-news", "investhk"):
            key = "investhk"
        if key in ("hkex_disclosure", "hkex-disclosure", "hkex"):
            key = "hkex"
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
        raise ValueError(f"Unsupported source: {src}")
    return collectors


def run_ingestion_once(config: PipelineConfig) -> dict[str, Any]:
    cfg = replace(config)
    cfg.db_path = Path(cfg.db_path).expanduser().resolve()
    cfg.raw_dir = Path(cfg.raw_dir).expanduser().resolve()
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
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

