from __future__ import annotations

import random
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from ..connectors import (
    ADBKIDBClient,
    HKMAClient,
    KPMG_HONG_KONG_BANKING_OUTLOOK_PDF_URL,
    download_kpmg_hong_kong_banking_outlook_pdf,
    parse_kidb_sdmx_timeseries,
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

