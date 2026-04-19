from __future__ import annotations

import json
import random
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from ..connectors import (
    ADBKIDBClient,
    HKEX_PREDEFINED_DOCS_URL,
    HKEXDisclosureClient,
    HKMAClient,
    InvestHKNewsClient,
    KPMG_HONG_KONG_BANKING_OUTLOOK_PDF_URL,
    SZSECninfoClient,
    build_cninfo_pdf_url,
    download_kpmg_hong_kong_banking_outlook_pdf,
    parse_kidb_sdmx_timeseries,
    timestamp_ms_to_date,
    timestamp_ms_to_datetime,
)
from .models import CollectionBatch, IntelligenceRecord, TimelineEvent, TriggerSignal
from .utils import (
    build_natural_key,
    coerce_float,
    detect_record_time,
    extract_time_period_from_text,
    infer_unit,
    normalize_text,
    safe_filename,
    sha256_file,
)


def _infer_signal_type(indicator: str | None, dataset: str) -> str:
    text = f"{dataset} {indicator or ''}".lower()
    if any(k in text for k in ("export", "trade", "cross", "fx", "cny", "usd")):
        return "cross_border"
    if any(k in text for k in ("unemployment", "risk", "loan", "impairment")):
        return "risk"
    if any(k in text for k in ("growth", "gdp", "output", "expansion", "industry", "agriculture")):
        return "growth"
    if any(k in text for k in ("fund", "finance", "liquidity", "consumption")):
        return "financing"
    return "market"


def _timeline_from_record(record: IntelligenceRecord, *, event_type: str) -> TimelineEvent:
    headline = record.title or f"{record.source} {record.dataset}"
    return TimelineEvent(
        source=record.source,
        company_id=record.company_id,
        entity=record.entity,
        event_time=record.event_time,
        event_type=event_type,
        headline=headline[:240],
        detail=record.summary,
        evidence_url=record.evidence_url,
        payload={
            "source": record.source,
            "dataset": record.dataset,
            "record_key": record.record_key,
        },
    )


class BaseCollector:
    source: str

    def collect(self) -> CollectionBatch:
        raise NotImplementedError


class HKMACollector(BaseCollector):
    source = "hkma"

    def __init__(self, *, pagesize: int = 200, max_pages: int = 5, languages: tuple[str, ...] = ("en", "tc")) -> None:
        self.pagesize = pagesize
        self.max_pages = max_pages
        self.languages = languages
        self.client = HKMAClient()

    def _fetch_paginated(self, fetcher: Any, **kwargs: Any) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        offset = 0
        page = 0
        while page < self.max_pages:
            payload = fetcher(pagesize=self.pagesize, offset=offset, **kwargs)
            page_records = payload.get("result", {}).get("records", [])
            if not isinstance(page_records, list) or not page_records:
                break
            records.extend([r for r in page_records if isinstance(r, dict)])
            offset += len(page_records)
            page += 1
            data_size = payload.get("result", {}).get("datasize")
            if isinstance(data_size, int) and offset >= data_size:
                break
            if len(page_records) < self.pagesize:
                break
        return records

    def _emit_metric_signals(self, batch: CollectionBatch, *, dataset: str, event_time: str, rec: dict[str, Any], lang: str | None) -> None:
        for key, value in rec.items():
            if key in {"end_of_day", "end_of_month", "date", "release_date"}:
                continue
            value_text = normalize_text(value)
            value_num = coerce_float(value_text)
            if value_num is None:
                continue
            signal_key = f"{dataset}|{event_time}|{key}|{value_text}"
            signal = TriggerSignal(
                source=self.source,
                dataset=dataset,
                signal_key=signal_key,
                signal_type=_infer_signal_type(key, dataset),
                event_time=event_time,
                company_id=None,
                entity="HKG",
                indicator=str(key),
                value_num=value_num,
                value_text=value_text or None,
                unit=infer_unit(str(key), value_text),
                signal_text=f"{key}: {value_text}",
                evidence_refs=[self.source, dataset],
                extra={"lang": lang} if lang else {},
            )
            batch.trigger_signals.append(signal)

    def _convert_records(self, batch: CollectionBatch, *, dataset: str, records: list[dict[str, Any]], lang: str | None) -> None:
        for idx, rec in enumerate(records):
            event_time = detect_record_time(rec)
            key = build_natural_key(dataset, rec, fallback=f"idx-{idx}")
            is_press = dataset.startswith("press_releases")
            title = normalize_text(rec.get("subject") or rec.get("title")) or None
            summary = normalize_text(rec.get("summary")) or title
            record_type = "event" if is_press else "metric"
            record = IntelligenceRecord(
                source=self.source,
                dataset=dataset,
                record_key=key,
                record_type=record_type,
                event_time=event_time,
                company_id=None,
                entity="HKG",
                title=title,
                summary=summary,
                region="Hong Kong",
                industry="Banking",
                tags=[dataset, self.source],
                payload=rec,
                evidence_url=normalize_text(rec.get("url")) or None,
                lang=lang,
                raw=rec,
            )
            batch.intelligence_records.append(record)
            batch.timeline_events.append(_timeline_from_record(record, event_type=record_type))
            if event_time:
                self._emit_metric_signals(batch, dataset=dataset, event_time=event_time, rec=rec, lang=lang)

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        endpoints = [
            ("exchange_rates_eeri_daily", self.client.exchange_rates_eeri_daily, "en"),
            ("hkd_interbank_rates_daily", self.client.hkd_interbank_rates_daily, "en"),
            ("composite_interest_rate_monthly", self.client.composite_interest_rate_monthly, "en"),
        ]
        for dataset, fetcher, lang in endpoints:
            records = self._fetch_paginated(fetcher)
            self._convert_records(batch, dataset=dataset, records=records, lang=lang)

        for lang in self.languages:
            dataset = f"press_releases_{lang}"
            records = self._fetch_paginated(self.client.press_releases, lang=lang)
            self._convert_records(batch, dataset=dataset, records=records, lang=lang)

        batch.meta = {"pagesize": self.pagesize, "max_pages": self.max_pages}
        return batch


class ADBCollector(BaseCollector):
    source = "adb_kidb"

    def __init__(
        self,
        *,
        economy: str = "HKG",
        start_year: int = 2018,
        end_year: int = datetime.now().year,
        min_interval_seconds: float = 3.2,
    ) -> None:
        self.economy = economy
        self.start_year = start_year
        self.end_year = end_year
        self.client = ADBKIDBClient(min_interval_seconds=min_interval_seconds)

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        queries: list[tuple[str, Any, str]] = [
            ("population_midyear", self.client.get_population_midyear, "LP_PE_NUM_MOP"),
            ("unemployment_rate", self.client.get_unemployment_rate, "LUR_PT"),
            ("merchandise_exports_fob", self.client.get_merchandise_exports_fob, "TXG_FOB_XDC"),
            (
                "general_government_final_consumption_current_prices",
                self.client.get_general_government_final_consumption_current_prices,
                "NCGG_XDC",
            ),
        ]
        errors: list[str] = []

        for dataset, method, indicator_code in queries:
            try:
                payload = method(self.economy, start_year=self.start_year, end_year=self.end_year)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{dataset}: {exc}")
                continue

            rows = parse_kidb_sdmx_timeseries(payload)
            key = f"{dataset}|{self.economy}|{self.start_year}|{self.end_year}"
            record = IntelligenceRecord(
                source=self.source,
                dataset=dataset,
                record_key=key,
                record_type="metric",
                event_time=None,
                company_id=None,
                entity=self.economy,
                title=dataset,
                summary=f"{dataset} rows={len(rows)}",
                region="Hong Kong",
                industry="Macro",
                tags=[dataset, indicator_code, self.source],
                payload={
                    "economy": self.economy,
                    "start_year": self.start_year,
                    "end_year": self.end_year,
                    "row_count": len(rows),
                    "indicator_code": indicator_code,
                },
                evidence_url=None,
                lang="en",
                raw=payload if isinstance(payload, dict) else None,
            )
            batch.intelligence_records.append(record)
            batch.timeline_events.append(_timeline_from_record(record, event_type="metric"))

            for row in rows:
                event_time = normalize_text(row.get("time_period"))
                if not event_time:
                    continue
                value_text = normalize_text(row.get("value"))
                signal_key = f"{dataset}|{indicator_code}|{self.economy}|{event_time}|{value_text}"
                signal = TriggerSignal(
                    source=self.source,
                    dataset=dataset,
                    signal_key=signal_key,
                    signal_type=_infer_signal_type(indicator_code, dataset),
                    event_time=event_time,
                    company_id=None,
                    entity=self.economy,
                    indicator=indicator_code,
                    value_num=row.get("value_num"),
                    value_text=value_text or None,
                    unit=normalize_text(row.get("unit")) or None,
                    signal_text=f"{indicator_code}: {value_text}",
                    evidence_refs=[self.source, dataset],
                    extra={
                        "unit_multiplier_pow10": row.get("unit_multiplier_pow10"),
                        "observation_index": row.get("observation_index"),
                    },
                )
                batch.trigger_signals.append(signal)

        batch.meta = {
            "economy": self.economy,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "errors": errors,
        }
        if errors and not batch.trigger_signals:
            raise RuntimeError("ADB collector failed: " + "; ".join(errors))
        return batch


class KPMGCollector(BaseCollector):
    source = "kpmg"

    def __init__(self, *, raw_dir: str | Path, url: str | None = None) -> None:
        self.raw_dir = Path(raw_dir)
        self.url = url

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "kpmg"
        out_dir.mkdir(parents=True, exist_ok=True)

        url = self.url or KPMG_HONG_KONG_BANKING_OUTLOOK_PDF_URL
        saved = download_kpmg_hong_kong_banking_outlook_pdf(out_dir / "hong-kong-banking-outlook.pdf", url=url)
        digest = sha256_file(saved)
        stat = saved.stat()

        record = IntelligenceRecord(
            source=self.source,
            dataset="hong_kong_banking_outlook_pdf",
            record_key=digest,
            record_type="document",
            event_time=str(datetime.now().year),
            company_id=None,
            entity="HKG",
            title="KPMG Hong Kong Banking Outlook",
            summary="Annual banking outlook PDF",
            region="Hong Kong",
            industry="Banking",
            tags=["kpmg", "report", "banking"],
            payload={"file_path": str(saved), "file_sha256": digest, "bytes": stat.st_size},
            evidence_url=url,
            lang="en",
            raw=None,
        )
        batch.intelligence_records.append(record)
        batch.timeline_events.append(_timeline_from_record(record, event_type="document"))
        return batch


def _infer_investhk_signal_type(news_type: str | None, text: str) -> str:
    combined = f"{news_type or ''} {text}".lower()
    if any(token in combined for token in ("cross-border", "cross border", "overseas", "mainland", "gba")):
        return "cross_border"
    if any(token in combined for token in ("fund", "financing", "capital", "fundraising", "ipo")):
        return "financing"
    if any(token in combined for token in ("risk", "warning", "volatility", "uncertainty")):
        return "risk"
    if any(token in combined for token in ("expansion", "growth", "investment", "launch")):
        return "growth"
    return "market"


def _matches_year_month(event_time: str | None, *, target_year: str | None, target_month: str | None) -> bool:
    if not target_year and not target_month:
        return True
    if not event_time:
        return False

    parts = event_time.split("-")
    year = parts[0] if parts else ""
    month = parts[1] if len(parts) > 1 else ""

    if target_year and year != target_year:
        return False
    if target_month and month != target_month:
        return False
    return True


def _infer_szse_announcement_signal_type(announcement_type: str | None, title: str) -> str:
    combined = f"{announcement_type or ''} {title}".lower()
    if any(token in combined for token in ("ipo", "上市", "招股", "首发")):
        return "financing"
    if any(token in combined for token in ("风险", "处罚", "诉讼", "减值", "亏损", "st")):
        return "risk"
    if any(token in combined for token in ("并购", "收购", "扩产", "投资", "增长", "合作")):
        return "growth"
    return "market"


class InvestHKNewsCollector(BaseCollector):
    source = "investhk_news"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        language: str = "zh-cn",
        json_url: str | None = None,
        include_article_text: bool = False,
        max_items: int = 500,
        request_timeout_seconds: int = 30,
        article_delay_seconds: float = 0.3,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.language = language
        self.json_url = json_url
        self.include_article_text = include_article_text
        self.max_items = max_items
        self.article_delay_seconds = max(0.0, float(article_delay_seconds))
        self.client = InvestHKNewsClient(timeout_seconds=request_timeout_seconds)

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "investhk_news"
        out_dir.mkdir(parents=True, exist_ok=True)

        items = self.client.fetch_news_items(language=self.language, json_url=self.json_url)
        if self.max_items > 0:
            items = items[: self.max_items]

        fetched_at = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        feed_dump_path = out_dir / f"news_{self.language}_{fetched_at}.json"
        feed_dump_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

        feed_record = IntelligenceRecord(
            source=self.source,
            dataset="news_feed_json",
            record_key=f"{self.language}|feed",
            record_type="document",
            event_time=None,
            company_id=None,
            entity="HKG",
            title=f"InvestHK news feed ({self.language})",
            summary=f"InvestHK feed snapshot with {len(items)} items",
            region="Hong Kong",
            industry="Investment / Business Development",
            tags=[self.source, "news_feed", self.language],
            payload={
                "language": self.language,
                "json_url": self.json_url,
                "item_count": len(items),
                "file_path": str(feed_dump_path.resolve()),
            },
            evidence_url=self.json_url or self.client.build_news_json_url(language=self.language),
            lang=self.language,
            raw=None,
        )
        batch.intelligence_records.append(feed_record)
        batch.timeline_events.append(_timeline_from_record(feed_record, event_type="document"))

        article_success = 0
        article_failed = 0

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            raw_url = normalize_text(item.get("url"))
            full_url = self.client.build_full_url(raw_url)
            title = normalize_text(item.get("title")) or "(untitled)"
            description = normalize_text(item.get("description"))
            news_type = normalize_text(item.get("newsContentType"))
            publish_date = normalize_text(item.get("publishDate") or item.get("date"))
            event_time = extract_time_period_from_text(publish_date)

            article_text = ""
            if self.include_article_text and full_url:
                try:
                    article_text = self.client.fetch_article_text(raw_url)
                    article_success += 1
                except Exception:
                    article_failed += 1
                if self.article_delay_seconds > 0:
                    time.sleep(self.article_delay_seconds)

            payload: dict[str, Any] = {
                "title": title,
                "description": description,
                "publish_date": publish_date,
                "news_content_type": news_type,
                "url": raw_url,
                "full_url": full_url,
            }
            if article_text:
                payload["article_text"] = article_text

            record_key = build_natural_key("investhk_news", item, fallback=f"idx-{idx}")
            record = IntelligenceRecord(
                source=self.source,
                dataset="news_items",
                record_key=record_key,
                record_type="event",
                event_time=event_time,
                company_id=None,
                entity="HKG",
                title=title,
                summary=description or title,
                region="Hong Kong",
                industry="Investment / Business Development",
                tags=[self.source, "news", news_type.lower() if news_type else "general"],
                payload=payload,
                evidence_url=full_url or None,
                lang=self.language,
                raw=item,
            )
            batch.intelligence_records.append(record)
            batch.timeline_events.append(_timeline_from_record(record, event_type="event"))

            signal_time = event_time or str(datetime.now().year)
            signal_type = _infer_investhk_signal_type(news_type, f"{title} {description} {article_text[:500]}")
            signal_key = f"investhk_news|{record_key}|headline"
            batch.trigger_signals.append(
                TriggerSignal(
                    source=self.source,
                    dataset="news_signals",
                    signal_key=signal_key,
                    signal_type=signal_type,
                    event_time=signal_time,
                    company_id=None,
                    entity="HKG",
                    indicator="headline",
                    value_num=None,
                    value_text=news_type or None,
                    unit=None,
                    signal_text=title,
                    evidence_refs=[ref for ref in [full_url] if ref],
                    extra={
                        "language": self.language,
                        "publish_date": publish_date,
                        "news_content_type": news_type,
                    },
                )
            )

        batch.meta = {
            "language": self.language,
            "json_url": self.json_url or self.client.build_news_json_url(language=self.language),
            "items_fetched": len(items),
            "include_article_text": self.include_article_text,
            "article_fetch_success": article_success,
            "article_fetch_failed": article_failed,
        }
        return batch


class SZSEAnnouncementCollector(BaseCollector):
    source = "szse_cninfo"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        days_back: int = 180,
        start_date: str | None = None,
        end_date: str | None = None,
        max_records: int = 50000,
        page_size: int = 30,
        delay_seconds: float = 0.3,
        plate: str = "sz",
        stock: str = "",
        tab_name: str = "fulltext",
        request_timeout_seconds: int = 15,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.days_back = max(1, int(days_back))
        self.start_date = normalize_text(start_date) or None
        self.end_date = normalize_text(end_date) or None
        self.max_records = max_records
        self.page_size = max(1, int(page_size))
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.plate = normalize_text(plate) or "sz"
        self.stock = normalize_text(stock)
        self.tab_name = normalize_text(tab_name) or "fulltext"
        self.client = SZSECninfoClient(timeout_seconds=request_timeout_seconds)

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "szse_cninfo"
        out_dir.mkdir(parents=True, exist_ok=True)

        end_date = self.end_date or datetime.today().strftime("%Y-%m-%d")
        start_date = self.start_date or (datetime.today() - timedelta(days=self.days_back)).strftime("%Y-%m-%d")

        result = self.client.fetch_announcements(
            start_date=start_date,
            end_date=end_date,
            plate=self.plate,
            stock=self.stock,
            tab_name=self.tab_name,
            page_size=self.page_size,
            max_records=self.max_records,
            delay_seconds=self.delay_seconds,
        )
        items = result.get("items", [])
        meta = result.get("meta", {})

        fetched_at = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dump_path = out_dir / f"announcements_{start_date}_{end_date}_{fetched_at}.json"
        dump_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

        feed_record = IntelligenceRecord(
            source=self.source,
            dataset="announcements_feed_json",
            record_key=f"feed|{start_date}|{end_date}|{self.plate}|{self.stock or 'all'}",
            record_type="document",
            event_time=None,
            company_id=None,
            entity="CN",
            title=f"CNINFO announcement feed ({self.plate})",
            summary=f"CNINFO feed snapshot with {len(items)} announcements",
            region="China",
            industry="Listed Companies",
            tags=[self.source, "feed_snapshot", self.plate],
            payload={
                "start_date": start_date,
                "end_date": end_date,
                "plate": self.plate,
                "stock": self.stock,
                "tab_name": self.tab_name,
                "items_count": len(items),
                "meta": meta,
                "file_path": str(dump_path.resolve()),
            },
            evidence_url="http://www.cninfo.com.cn/",
            lang="zh",
            raw=None,
        )
        batch.intelligence_records.append(feed_record)
        batch.timeline_events.append(_timeline_from_record(feed_record, event_type="document"))

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            announcement_id = normalize_text(item.get("announcementId"))
            stock_code = normalize_text(item.get("secCode"))
            stock_name = normalize_text(item.get("secName"))
            announcement_title = normalize_text(item.get("announcementTitle")) or "(untitled announcement)"
            announcement_type = normalize_text(item.get("announcementType"))
            announcement_time = item.get("announcementTime")

            event_time = timestamp_ms_to_date(announcement_time)
            event_datetime = timestamp_ms_to_datetime(announcement_time)
            pdf_url = build_cninfo_pdf_url(item.get("adjunctUrl"))

            record_key = announcement_id or build_natural_key("szse_cninfo", item, fallback=f"idx-{idx}")
            company_id = stock_code or None

            payload: dict[str, Any] = {
                "announcement_id": announcement_id,
                "announcement_type": announcement_type,
                "announcement_time": announcement_time,
                "announcement_datetime": event_datetime,
                "stock_code": stock_code,
                "stock_name": stock_name,
                "adjunct_type": normalize_text(item.get("adjunctType")),
                "adjunct_size_kb": item.get("adjunctSize"),
                "pdf_url": pdf_url,
            }

            record = IntelligenceRecord(
                source=self.source,
                dataset="announcements",
                record_key=record_key,
                record_type="event",
                event_time=event_time or None,
                company_id=company_id,
                entity="CN",
                title=announcement_title,
                summary=announcement_type or announcement_title,
                region="China",
                industry="Listed Companies",
                tags=[self.source, self.plate, announcement_type.lower() if announcement_type else "general"],
                payload=payload,
                evidence_url=pdf_url or None,
                lang="zh",
                raw=item,
            )
            batch.intelligence_records.append(record)
            batch.timeline_events.append(_timeline_from_record(record, event_type="event"))

            signal_time = event_time or str(datetime.now().year)
            signal_key = f"{self.source}|{record_key}|announcement"
            signal_type = _infer_szse_announcement_signal_type(announcement_type, announcement_title)
            batch.trigger_signals.append(
                TriggerSignal(
                    source=self.source,
                    dataset="announcement_signals",
                    signal_key=signal_key,
                    signal_type=signal_type,
                    event_time=signal_time,
                    company_id=company_id,
                    entity="CN",
                    indicator="announcement",
                    value_num=None,
                    value_text=announcement_type or None,
                    unit=None,
                    signal_text=announcement_title,
                    evidence_refs=[ref for ref in [pdf_url] if ref],
                    extra={
                        "announcement_id": announcement_id,
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "announcement_datetime": event_datetime,
                    },
                )
            )

        batch.meta = {
            "start_date": start_date,
            "end_date": end_date,
            "plate": self.plate,
            "stock": self.stock,
            "tab_name": self.tab_name,
            "items_fetched": len(items),
            "source_meta": meta,
        }
        return batch


class HKEXDisclosureCollector(BaseCollector):
    source = "hkex_disclosure"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        list_url: str | None = None,
        target_year: str | None = None,
        target_month: str | None = None,
        max_items: int = 200,
        request_timeout_seconds: int = 30,
        use_selenium_fallback: bool = True,
        headless: bool = True,
        download_wait_seconds: int = 30,
        page_wait_seconds: float = 1.0,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.list_url = normalize_text(list_url) or HKEX_PREDEFINED_DOCS_URL
        self.target_year = normalize_text(target_year) or None

        month_raw = normalize_text(target_month)
        if month_raw and month_raw.isdigit():
            month_raw = f"{int(month_raw):02d}"
        self.target_month = month_raw or None

        self.max_items = max_items
        self.use_selenium_fallback = use_selenium_fallback
        self.headless = headless
        self.download_wait_seconds = max(5, int(download_wait_seconds))
        self.page_wait_seconds = max(0.1, float(page_wait_seconds))
        self.client = HKEXDisclosureClient(timeout_seconds=request_timeout_seconds)

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "hkex_disclosure"
        pdf_dir = out_dir / "pdfs"
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_dir.mkdir(parents=True, exist_ok=True)

        items = self.client.fetch_predefined_items(list_url=self.list_url)
        fetched_count = len(items)

        filtered_items: list[dict[str, str]] = []
        for item in items:
            publish_date = normalize_text(item.get("publish_date"))
            event_time = extract_time_period_from_text(publish_date)
            if _matches_year_month(event_time, target_year=self.target_year, target_month=self.target_month):
                filtered_items.append(item)

        if self.max_items > 0:
            filtered_items = filtered_items[: self.max_items]

        fetched_at = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        snapshot_path = out_dir / f"hkex_predefined_docs_{fetched_at}.json"
        snapshot_path.write_text(json.dumps(filtered_items, ensure_ascii=False, indent=2), encoding="utf-8")

        feed_record = IntelligenceRecord(
            source=self.source,
            dataset="predefined_documents_feed",
            record_key=f"feed|{self.target_year or 'all'}|{self.target_month or 'all'}",
            record_type="document",
            event_time=None,
            company_id=None,
            entity="HKG",
            title="HKEX predefined disclosure feed",
            summary=f"HKEX feed snapshot with {len(filtered_items)} filtered rows",
            region="Hong Kong",
            industry="Listed Companies",
            tags=[self.source, "feed_snapshot"],
            payload={
                "list_url": self.list_url,
                "items_fetched": fetched_count,
                "items_after_filter": len(filtered_items),
                "target_year": self.target_year,
                "target_month": self.target_month,
                "file_path": str(snapshot_path.resolve()),
            },
            evidence_url=self.list_url,
            lang="zh",
            raw=None,
        )
        batch.intelligence_records.append(feed_record)
        batch.timeline_events.append(_timeline_from_record(feed_record, event_type="document"))

        download_success = 0
        download_failed = 0

        for idx, item in enumerate(filtered_items):
            publish_date = normalize_text(item.get("publish_date"))
            stock_code = normalize_text(item.get("stock_code"))
            company_name = normalize_text(item.get("company_name")) or "listed company"
            detail_url = normalize_text(item.get("detail_url"))
            row_title = normalize_text(item.get("title")) or f"{company_name} annual report"
            event_time = extract_time_period_from_text(publish_date)

            base_name = safe_filename(f"{publish_date}_{stock_code}_{company_name}")
            target_pdf_path = pdf_dir / f"{base_name}.pdf"

            pdf_url: str | None = None
            file_path: str | None = None
            file_sha256: str | None = None
            download_method: str | None = None
            download_error: str | None = None

            try:
                pdf_url = self.client.resolve_pdf_url(detail_url)
                if pdf_url:
                    saved = self.client.download_pdf(pdf_url, target_pdf_path)
                    file_path = str(saved.resolve())
                    file_sha256 = sha256_file(saved)
                    download_method = "requests"
                    download_success += 1
                elif self.use_selenium_fallback and detail_url:
                    saved = self.client.download_with_selenium(
                        detail_url,
                        download_dir=pdf_dir,
                        headless=self.headless,
                        wait_seconds=self.download_wait_seconds,
                        page_wait_seconds=self.page_wait_seconds,
                    )
                    if saved is not None:
                        renamed = pdf_dir / f"{base_name}.pdf"
                        if saved.resolve() != renamed.resolve():
                            if renamed.exists():
                                renamed.unlink()
                            saved.replace(renamed)
                            saved = renamed
                        file_path = str(saved.resolve())
                        file_sha256 = sha256_file(saved)
                        download_method = "selenium"
                        download_success += 1
                    else:
                        download_failed += 1
                else:
                    download_failed += 1
            except Exception as exc:  # noqa: BLE001
                download_error = str(exc)
                download_failed += 1

            record_key = build_natural_key("hkex_annual_reports", item, fallback=f"idx-{idx}")
            company_id = stock_code or None

            code_suffix = f" ({stock_code})" if stock_code else ""
            summary_text = f"HKEX annual report disclosure for {company_name}{code_suffix}"
            signal_text = f"{company_name}{code_suffix} annual report published"

            payload: dict[str, Any] = {
                "publish_date": publish_date,
                "stock_code": stock_code,
                "company_name": company_name,
                "title": row_title,
                "detail_url": detail_url,
                "pdf_url": pdf_url,
                "file_path": file_path,
                "file_sha256": file_sha256,
                "download_method": download_method,
                "download_error": download_error,
            }

            record = IntelligenceRecord(
                source=self.source,
                dataset="annual_reports_pdf",
                record_key=record_key,
                record_type="document",
                event_time=event_time,
                company_id=company_id,
                entity="HKG",
                title=row_title,
                summary=summary_text,
                region="Hong Kong",
                industry="Listed Companies",
                tags=[self.source, "annual_report", stock_code or "unknown_code"],
                payload=payload,
                evidence_url=pdf_url or detail_url or None,
                lang="zh",
                raw=item,
            )
            batch.intelligence_records.append(record)
            batch.timeline_events.append(_timeline_from_record(record, event_type="document"))

            signal_time = event_time or str(datetime.now().year)
            signal_key = f"{self.source}|{record_key}|publication"
            batch.trigger_signals.append(
                TriggerSignal(
                    source=self.source,
                    dataset="annual_report_publication",
                    signal_key=signal_key,
                    signal_type="market",
                    event_time=signal_time,
                    company_id=company_id,
                    entity="HKG",
                    indicator="annual_report_published",
                    value_num=None,
                    value_text=publish_date or None,
                    unit=None,
                    signal_text=signal_text,
                    evidence_refs=[ref for ref in [pdf_url, detail_url] if ref],
                    extra={
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "download_method": download_method,
                        "download_error": download_error,
                    },
                )
            )

        batch.meta = {
            "list_url": self.list_url,
            "items_fetched": fetched_count,
            "items_after_filter": len(filtered_items),
            "target_year": self.target_year,
            "target_month": self.target_month,
            "use_selenium_fallback": self.use_selenium_fallback,
            "headless": self.headless,
            "download_success": download_success,
            "download_failed": download_failed,
        }
        return batch


class GuangdongStatsCollector(BaseCollector):
    source = "guangdong_stats"

    categories: dict[str, str] = {
        "macro": "/gmjjzyzb/index.html",
        "national_accounts": "/jdgnsczz/index.html",
        "industry": "/gyzjz/index.html",
        "agriculture": "/nyzcz/index.html",
    }

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        base_domain: str = "https://stats.gd.gov.cn",
        years: tuple[int, ...] | None = None,
        max_links_per_category: int = 20,
        max_tables_per_page: int = 2,
        max_rows_per_table: int = 500,
        request_timeout_seconds: int = 20,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.base_domain = base_domain.rstrip("/")
        current_year = datetime.now().year
        self.years = years or (current_year, current_year - 1)
        self.max_links_per_category = max_links_per_category
        self.max_tables_per_page = max_tables_per_page
        self.max_rows_per_table = max_rows_per_table
        self.request_timeout_seconds = request_timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
            }
        )

    def _find_target_links(self, category_path: str) -> list[tuple[str, str]]:
        from bs4 import BeautifulSoup

        url = urljoin(self.base_domain, category_path)
        resp = self.session.get(url, timeout=self.request_timeout_seconds)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        links: list[tuple[str, str]] = []
        year_tokens = [str(y) for y in self.years]
        for a in soup.find_all("a", href=True):
            href = normalize_text(a.get("href"))
            text = normalize_text(a.get_text())
            if not href or "post_" not in href:
                continue
            if not any(token in text for token in year_tokens):
                continue
            links.append((text or href, urljoin(self.base_domain, href)))

        deduped: list[tuple[str, str]] = []
        seen = set()
        for title, detail_url in links:
            if detail_url in seen:
                continue
            seen.add(detail_url)
            deduped.append((title, detail_url))
        return deduped[: self.max_links_per_category]

    def collect(self) -> CollectionBatch:
        import pandas as pd
        from bs4 import BeautifulSoup

        batch = CollectionBatch(source=self.source)
        root = self.raw_dir / "guangdong_stats"
        root.mkdir(parents=True, exist_ok=True)

        page_count = 0
        table_count = 0
        row_count = 0

        for category, path in self.categories.items():
            category_dir = root / category
            category_dir.mkdir(parents=True, exist_ok=True)
            links = self._find_target_links(path)

            for list_title, detail_url in links:
                page_count += 1
                resp = self.session.get(detail_url, timeout=self.request_timeout_seconds)
                resp.raise_for_status()
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "html.parser")
                title_node = soup.find("div", class_="title") or soup.find("h1")
                detail_title = normalize_text(title_node.get_text() if title_node else list_title) or list_title
                event_time = extract_time_period_from_text(detail_title)

                page_record = IntelligenceRecord(
                    source=self.source,
                    dataset="detail_pages",
                    record_key=f"detail|{detail_url}",
                    record_type="event",
                    event_time=event_time,
                    company_id=None,
                    entity=category,
                    title=detail_title,
                    summary=f"Guangdong statistics page: {detail_title}",
                    region="Guangdong",
                    industry=category,
                    tags=[self.source, category, "detail_page"],
                    payload={"category": category, "title": detail_title, "detail_url": detail_url},
                    evidence_url=detail_url,
                    lang="zh",
                    raw=None,
                )
                batch.intelligence_records.append(page_record)
                batch.timeline_events.append(_timeline_from_record(page_record, event_type="event"))

                try:
                    tables = pd.read_html(StringIO(resp.text))
                except ValueError:
                    tables = []
                if not tables:
                    continue

                for table_index, table in enumerate(tables[: self.max_tables_per_page]):
                    df = table.copy()
                    if df.empty:
                        continue
                    df.columns = [normalize_text(c) or f"col_{i}" for i, c in enumerate(df.columns)]
                    df = df.dropna(how="all").head(self.max_rows_per_table)
                    if df.empty:
                        continue

                    table_count += 1
                    table_path = category_dir / f"{safe_filename(detail_title)}_t{table_index + 1}.csv"
                    df.to_csv(table_path, index=False, encoding="utf-8-sig")
                    digest = sha256_file(table_path)

                    file_record = IntelligenceRecord(
                        source=self.source,
                        dataset="tables_csv",
                        record_key=digest,
                        record_type="document",
                        event_time=event_time,
                        company_id=None,
                        entity=category,
                        title=f"{detail_title} table {table_index + 1}",
                        summary="Guangdong statistics extracted table CSV",
                        region="Guangdong",
                        industry=category,
                        tags=[self.source, category, "csv"],
                        payload={
                            "file_path": str(table_path.resolve()),
                            "file_sha256": digest,
                            "category": category,
                            "table_index": table_index,
                            "rows": len(df),
                            "columns": len(df.columns),
                        },
                        evidence_url=detail_url,
                        lang="zh",
                        raw=None,
                    )
                    batch.intelligence_records.append(file_record)
                    batch.timeline_events.append(_timeline_from_record(file_record, event_type="document"))

                    for row_idx, row in df.iterrows():
                        row_count += 1
                        row_data = {str(col): normalize_text(row[col]) for col in df.columns}
                        row_key = f"{detail_url}|t{table_index}|r{row_idx}"
                        row_record = IntelligenceRecord(
                            source=self.source,
                            dataset="table_rows",
                            record_key=row_key,
                            record_type="metric",
                            event_time=event_time,
                            company_id=None,
                            entity=category,
                            title=detail_title,
                            summary=f"{category} row {int(row_idx)}",
                            region="Guangdong",
                            industry=category,
                            tags=[self.source, category, "table_row"],
                            payload={
                                "category": category,
                                "title": detail_title,
                                "table_index": table_index,
                                "row_index": int(row_idx),
                                "row_data": row_data,
                            },
                            evidence_url=detail_url,
                            lang="zh",
                            raw=None,
                        )
                        batch.intelligence_records.append(row_record)

                        signal_time = event_time or str(self.years[0])
                        if not signal_time:
                            continue
                        for col, text in row_data.items():
                            num = coerce_float(text)
                            if num is None:
                                continue
                            signal_key = f"{category}|{detail_title}|{table_index}|{row_idx}|{col}|{text}"
                            batch.trigger_signals.append(
                                TriggerSignal(
                                    source=self.source,
                                    dataset="statistics_table",
                                    signal_key=signal_key,
                                    signal_type=_infer_signal_type(col, "statistics_table"),
                                    event_time=signal_time,
                                    company_id=None,
                                    entity=category,
                                    indicator=col,
                                    value_num=num,
                                    value_text=text or None,
                                    unit=infer_unit(col, text),
                                    signal_text=f"{col}: {text}",
                                    evidence_refs=[detail_url, str(table_path.resolve())],
                                    extra={
                                        "title": detail_title,
                                        "detail_url": detail_url,
                                        "table_index": table_index,
                                        "row_index": int(row_idx),
                                    },
                                )
                            )
                time.sleep(random.uniform(0.2, 0.8))

        batch.meta = {
            "categories": list(self.categories.keys()),
            "years": list(self.years),
            "pages_processed": page_count,
            "tables_processed": table_count,
            "rows_processed": row_count,
        }
        return batch

