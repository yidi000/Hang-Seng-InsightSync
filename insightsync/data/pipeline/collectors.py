from __future__ import annotations

import csv
import json
import random
import shutil
import time
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from ..connectors import (
    ADBKIDBClient,
    CENSTATDClient,
    CompanyProfileClient,
    EXTERNAL_TRADE_TABLE_ID,
    HKGovNewsClient,
    HKEX_PREDEFINED_DOCS_URL,
    HKEXDisclosureClient,
    HKMAClient,
    InvestHKNewsClient,
    KPMG_HONG_KONG_BANKING_OUTLOOK_PDF_URL,
    RETAIL_SALES_TABLE_ID,
    SZSECninfoClient,
    build_cninfo_pdf_url,
    download_kpmg_hong_kong_banking_outlook_pdf,
    extract_censtatd_rows,
    extract_hk_gov_news_id,
    normalize_public_url,
    parse_kidb_sdmx_timeseries,
    slugify_company_id,
    timestamp_ms_to_date,
    timestamp_ms_to_datetime,
)
from .models import CollectionBatch, CompanyProfile, IntelligenceRecord, TimelineEvent, TriggerSignal
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


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = normalize_text(item)
            if text:
                out.append(text)
        return out
    return []


def _coerce_code_text(value: Any) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or text


def _coerce_percent(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = normalize_text(value).replace("%", "")
    return coerce_float(text)


class CompanyDirectoryCollector(BaseCollector):
    source = "company_directory"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        seed_path: str | Path | None = None,
        segments: tuple[str, ...] = ("sme", "fintech", "cross_border"),
        max_items: int = 500,
        enable_enrichment: bool = False,
        request_timeout_seconds: int = 15,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        default_seed = Path(__file__).resolve().parents[1] / "seeds" / "company_candidates.json"
        self.seed_path = Path(seed_path).expanduser().resolve() if seed_path else default_seed
        self.segments = tuple([normalize_text(x).lower() for x in segments if normalize_text(x)])
        self.max_items = max(1, int(max_items))
        self.enable_enrichment = bool(enable_enrichment)
        self.client = CompanyProfileClient(timeout_seconds=request_timeout_seconds)

    def _load_seed_candidates(self) -> list[dict[str, Any]]:
        if not self.seed_path.exists():
            return []
        text = self.seed_path.read_text(encoding="utf-8")
        payload = json.loads(text)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "company_directory"
        out_dir.mkdir(parents=True, exist_ok=True)

        candidates = self._load_seed_candidates()
        selected_segments = set(self.segments)
        snapshot_rows: list[dict[str, Any]] = []
        skipped = 0

        for item in candidates:
            name = normalize_text(item.get("name") or item.get("canonical_name") or item.get("company_name"))
            if not name:
                skipped += 1
                continue

            segments = [seg.lower() for seg in _normalize_list(item.get("segments"))]
            if selected_segments and not any(seg in selected_segments for seg in segments):
                skipped += 1
                continue

            industries = _normalize_list(item.get("industries"))
            region = normalize_text(item.get("region")) or "Hong Kong"
            country = normalize_text(item.get("country")) or "China"
            city = normalize_text(item.get("city")) or None
            display_name = normalize_text(item.get("display_name") or item.get("legal_name")) or None
            description = normalize_text(item.get("description")) or None

            namespace = normalize_text(item.get("namespace") or item.get("entity") or "hkg")
            company_id = normalize_text(item.get("company_id")) or slugify_company_id(name, namespace=namespace)

            profile_urls = item.get("profile_urls") if isinstance(item.get("profile_urls"), dict) else {}
            if self.enable_enrichment:
                profile_out = self.client.enrich_public_profile(profile_urls)
                normalized_urls = profile_out.get("profile_urls") if isinstance(profile_out, dict) else {}
                enrichment = profile_out.get("enrichment") if isinstance(profile_out, dict) else {}
            else:
                normalized_urls = {
                    "website": normalize_public_url(profile_urls.get("website")),
                    "linkedin": normalize_public_url(profile_urls.get("linkedin")),
                    "facebook": normalize_public_url(profile_urls.get("facebook")),
                    "x": normalize_public_url(profile_urls.get("x")),
                    "instagram": normalize_public_url(profile_urls.get("instagram")),
                    "wikipedia": normalize_public_url(profile_urls.get("wikipedia")),
                }
                enrichment = {}

            profile_summary = normalize_text(item.get("profile_summary")) or None
            if not profile_summary:
                wiki_summary = normalize_text(enrichment.get("wikipedia_summary"))
                profile_summary = wiki_summary or None

            company = CompanyProfile(
                source=self.source,
                company_id=company_id,
                canonical_name=name,
                display_name=display_name,
                country=country,
                region=region,
                city=city,
                segments=segments,
                industries=industries,
                website_url=normalize_text(normalized_urls.get("website")) or None,
                linkedin_url=normalize_text(normalized_urls.get("linkedin")) or None,
                facebook_url=normalize_text(normalized_urls.get("facebook")) or None,
                x_url=normalize_text(normalized_urls.get("x")) or None,
                instagram_url=normalize_text(normalized_urls.get("instagram")) or None,
                wikipedia_url=normalize_text(normalized_urls.get("wikipedia")) or None,
                profile_summary=profile_summary,
                description=description,
                extra={
                    "website_title": enrichment.get("website_title") if isinstance(enrichment, dict) else None,
                    "source_tags": _normalize_list(item.get("source_tags")),
                    "seed_source": normalize_text(item.get("seed_source")) or "manual_seed",
                },
            )
            batch.companies.append(company)

            record = IntelligenceRecord(
                source=self.source,
                dataset="company_profiles",
                record_key=company_id,
                record_type="entity",
                event_time=str(datetime.now().year),
                company_id=company_id,
                entity=country,
                title=name,
                summary=description or profile_summary or f"{name} profile",
                region=region,
                industry=(industries[0] if industries else None),
                tags=[self.source, "company_profile", *segments],
                payload={
                    "company_id": company_id,
                    "canonical_name": name,
                    "segments": segments,
                    "industries": industries,
                    "profile_urls": normalized_urls,
                },
                evidence_url=(company.website_url or company.wikipedia_url),
                lang="en",
                raw=item,
            )
            batch.intelligence_records.append(record)
            batch.timeline_events.append(_timeline_from_record(record, event_type="entity"))

            snapshot_rows.append(
                {
                    "company_id": company.company_id,
                    "canonical_name": company.canonical_name,
                    "display_name": company.display_name,
                    "country": company.country,
                    "region": company.region,
                    "city": company.city,
                    "segments": company.segments,
                    "industries": company.industries,
                    "website_url": company.website_url,
                    "linkedin_url": company.linkedin_url,
                    "facebook_url": company.facebook_url,
                    "x_url": company.x_url,
                    "instagram_url": company.instagram_url,
                    "wikipedia_url": company.wikipedia_url,
                    "profile_summary": company.profile_summary,
                    "description": company.description,
                    "extra": company.extra,
                }
            )

            if len(batch.companies) >= self.max_items:
                break

        fetched_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snapshot_path = out_dir / f"companies_{fetched_at}.json"
        snapshot_path.write_text(json.dumps(snapshot_rows, ensure_ascii=False, indent=2), encoding="utf-8")

        batch.meta = {
            "seed_path": str(self.seed_path),
            "segments": list(self.segments),
            "max_items": self.max_items,
            "enable_enrichment": self.enable_enrichment,
            "seed_candidates": len(candidates),
            "companies_selected": len(batch.companies),
            "companies_skipped": skipped,
            "snapshot_path": str(snapshot_path.resolve()),
        }
        return batch


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


class CENSTATDCollector(BaseCollector):
    source = "censtatd"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        language: str = "en",
        include_full_series: bool = True,
        request_timeout_seconds: int = 60,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.language = normalize_text(language).lower() or "en"
        self.include_full_series = bool(include_full_series)
        self.request_timeout_seconds = int(request_timeout_seconds)
        self.client = CENSTATDClient()

    @staticmethod
    def _row_entity(row: dict[str, Any]) -> str:
        outlet_desc = normalize_text(row.get("OUTLET_TYPEDesc"))
        return outlet_desc or "HKG"

    @staticmethod
    def _row_title(dataset: str, row: dict[str, Any]) -> str:
        label = normalize_text(row.get("OUTLET_TYPEDesc")) or "Total"
        period = normalize_text(row.get("period"))
        return f"{dataset} {label} {period}".strip()

    @staticmethod
    def _row_summary(dataset: str, row: dict[str, Any]) -> str:
        label = normalize_text(row.get("OUTLET_TYPEDesc")) or "Total"
        sv = normalize_text(row.get("sv"))
        figure = normalize_text(row.get("figure")) or normalize_text(row.get("sd_value"))
        period = normalize_text(row.get("period"))
        return f"{dataset}; {label}; {sv}; {period}; {figure}".strip()

    @staticmethod
    def _normalize_figure(value: Any) -> tuple[float | None, str | None]:
        value_num = coerce_float(value)
        value_text = normalize_text(value)
        return value_num, value_text or None

    def _iter_dataset_rows(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = extract_censtatd_rows(payload)
        return rows

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "censtatd"
        out_dir.mkdir(parents=True, exist_ok=True)

        datasets = [
            ("retail_sales", RETAIL_SALES_TABLE_ID, self.client.retail_sales),
            ("external_merchandise_trade", EXTERNAL_TRADE_TABLE_ID, self.client.external_merchandise_trade),
        ]
        meta_rows: list[dict[str, Any]] = []

        for dataset, table_id, fetcher in datasets:
            payload = fetcher(
                lang=self.language,
                full_series=self.include_full_series,
                timeout=self.request_timeout_seconds,
            )
            fetched_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            raw_path = out_dir / f"{dataset}_{fetched_at}.json"
            raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            rows = self._iter_dataset_rows(payload)
            header = payload.get("header") if isinstance(payload, dict) else {}
            title = normalize_text((header or {}).get("title")) or dataset

            feed_record = IntelligenceRecord(
                source=self.source,
                dataset=f"{dataset}_feed_json",
                record_key=f"{dataset}|{table_id}|{fetched_at}",
                record_type="document",
                event_time=None,
                company_id=None,
                entity="HKG",
                title=title,
                summary=f"{dataset} snapshot rows={len(rows)}",
                region="Hong Kong",
                industry="Macro",
                tags=[self.source, dataset, "feed_snapshot"],
                payload={
                    "table_id": table_id,
                    "rows": len(rows),
                    "language": self.language,
                    "full_series": self.include_full_series,
                    "file_path": str(raw_path.resolve()),
                },
                evidence_url=f"https://www.censtatd.gov.hk/en/web_table.html?id={table_id}",
                lang=self.language,
                raw=None,
            )
            batch.intelligence_records.append(feed_record)
            batch.timeline_events.append(_timeline_from_record(feed_record, event_type="document"))

            meta_rows.append(
                {
                    "dataset": dataset,
                    "table_id": table_id,
                    "rows": len(rows),
                    "file_path": str(raw_path.resolve()),
                }
            )

            for idx, row in enumerate(rows):
                event_time = extract_time_period_from_text(normalize_text(row.get("period")))
                if not event_time:
                    continue

                value_num, value_text = self._normalize_figure(row.get("figure"))
                sd_value = normalize_text(row.get("sd_value")) or None
                indicator = normalize_text(row.get("sv")) or None
                entity = self._row_entity(row)
                label = normalize_text(row.get("OUTLET_TYPEDesc")) or None
                record_key = build_natural_key(dataset, row, fallback=f"idx-{idx}")

                record = IntelligenceRecord(
                    source=self.source,
                    dataset=dataset,
                    record_key=record_key,
                    record_type="metric",
                    event_time=event_time,
                    company_id=None,
                    entity=entity,
                    title=self._row_title(dataset, row),
                    summary=self._row_summary(dataset, row),
                    region="Hong Kong",
                    industry="Macro",
                    tags=[self.source, dataset, indicator or "unknown_indicator"],
                    payload=row,
                    evidence_url=f"https://www.censtatd.gov.hk/en/web_table.html?id={table_id}",
                    lang=self.language,
                    raw=row,
                )
                batch.intelligence_records.append(record)
                batch.timeline_events.append(_timeline_from_record(record, event_type="metric"))

                signal_key = f"{dataset}|{entity}|{indicator}|{event_time}|{value_text or sd_value or idx}"
                batch.trigger_signals.append(
                    TriggerSignal(
                        source=self.source,
                        dataset=dataset,
                        signal_key=signal_key,
                        signal_type=_infer_signal_type(indicator, dataset),
                        event_time=event_time,
                        company_id=None,
                        entity="HKG",
                        indicator=indicator,
                        value_num=value_num,
                        value_text=value_text or sd_value,
                        unit=normalize_text(row.get("svDesc")) or None,
                        signal_text=f"{label or 'Total'} {indicator or dataset}: {value_text or sd_value or ''}".strip(),
                        evidence_refs=[f"https://www.censtatd.gov.hk/en/web_table.html?id={table_id}"],
                        extra={
                            "freq": normalize_text(row.get("freq")) or None,
                            "period": normalize_text(row.get("period")) or None,
                            "special_value_flag": sd_value,
                            "outlet_type": row.get("OUTLET_TYPE"),
                            "outlet_desc": label,
                            "table_id": table_id,
                        },
                    )
                )

        batch.meta = {
            "language": self.language,
            "include_full_series": self.include_full_series,
            "datasets": meta_rows,
        }
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


def _infer_hkgov_news_signal_type(title: str, description: str, *, matched_gba_enterprise: bool) -> str:
    combined = f"{title} {description}".lower()
    if matched_gba_enterprise and any(
        token in combined
        for token in (
            "greater bay area",
            "cross-boundary",
            "cross border",
            "guangdong",
            "shenzhen",
            "guangzhou",
            "粤港澳大湾区",
            "跨境",
            "广东",
            "深圳",
            "广州",
        )
    ):
        return "cross_border"
    if any(token in combined for token in ("fund", "financing", "capital", "investment", "finance", "贷款", "融资", "投资", "金融")):
        return "financing"
    if any(token in combined for token in ("risk", "warning", "fraud", "penalty", "uncertainty", "风险", "警告", "处罚")):
        return "risk"
    if any(token in combined for token in ("innovation", "technology", "manufacturing", "startup", "growth", "创新", "科技", "制造", "增长")):
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


class HKGovNewsCollector(BaseCollector):
    source = "hk_gov_news"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        language: str = "en",
        since_months: int = 3,
        since_days: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        max_items: int = 1000,
        filter_limit: int = 50,
        require_geo_and_business: bool = True,
        request_timeout_seconds: int = 60,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.language = normalize_text(language).lower() or "en"
        if self.language not in {"en", "tc"}:
            raise ValueError("hkgov language must be 'en' or 'tc'")

        self.since_months = int(since_months)
        self.since_days = None if since_days is None else int(since_days)
        self.start_date = normalize_text(start_date) or None
        self.end_date = normalize_text(end_date) or None
        self.max_items = int(max_items)
        self.filter_limit = int(filter_limit)
        self.require_geo_and_business = require_geo_and_business
        self.request_timeout_seconds = int(request_timeout_seconds)
        self.client = HKGovNewsClient()

    @staticmethod
    def _normalize_csv_date_time(row: dict[str, Any]) -> tuple[str, str]:
        published_at = normalize_text(row.get("published_at"))
        if published_at:
            text = published_at.replace("T", " ")
            if "+" in text:
                text = text.split("+", 1)[0]
            if text.endswith("Z"):
                text = text[:-1]
            parts = text.split(" ")
            if len(parts) >= 2:
                return parts[0], f"{parts[0]} {parts[1]}"
            return text, text

        pub_date = normalize_text(row.get("pubDate"))
        return pub_date, pub_date

    def _write_csv(
        self,
        *,
        raw_articles: list[dict[str, Any]],
        filtered_links: set[str],
        output_path: Path,
        window_label: str,
    ) -> None:
        headers = [
            "news_date",
            "news_time",
            "language",
            "window",
            "title",
            "description",
            "link",
            "news_id",
            "is_gba_enterprise_match",
        ]
        with output_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in raw_articles:
                link = normalize_text(row.get("link"))
                date_text, time_text = self._normalize_csv_date_time(row)
                writer.writerow(
                    [
                        date_text,
                        time_text,
                        self.language,
                        window_label,
                        normalize_text(row.get("title")),
                        normalize_text(row.get("description")),
                        link,
                        extract_hk_gov_news_id(link),
                        "yes" if link in filtered_links else "no",
                    ]
                )

    def collect(self) -> CollectionBatch:
        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "hk_gov_news"
        out_dir.mkdir(parents=True, exist_ok=True)

        raw_articles = self.client.fetch_articles(
            language=self.language,
            since_months=self.since_months,
            since_days=self.since_days,
            start_date=self.start_date,
            end_date=self.end_date,
            timeout=self.request_timeout_seconds,
            max_items=self.max_items,
        )
        filtered_articles = self.client.filter_gba_enterprise_news(
            articles=raw_articles,
            language=self.language,
            require_geo_and_business=self.require_geo_and_business,
            limit=self.filter_limit,
        )
        filtered_links = {
            normalize_text(item.get("link")) for item in filtered_articles if normalize_text(item.get("link"))
        }

        if self.start_date and self.end_date:
            window_label = f"{self.start_date}_{self.end_date}"
        elif self.since_days is not None:
            window_label = f"last_{self.since_days}_days"
        elif self.since_months > 0:
            window_label = f"last_{self.since_months}_months"
        else:
            window_label = "latest_rss"

        fetched_at = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        json_path = out_dir / f"news_{self.language}_{window_label}_{fetched_at}.json"
        csv_path = out_dir / f"news_{self.language}_{window_label}_{fetched_at}.csv"

        snapshot = {
            "meta": {
                "fetched_at": fetched_at,
                "language": self.language,
                "window": window_label,
                "since_months": self.since_months,
                "since_days": self.since_days,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "max_items": self.max_items,
                "filter_limit": self.filter_limit,
                "require_geo_and_business": self.require_geo_and_business,
                "raw_count": len(raw_articles),
                "filtered_count": len(filtered_articles),
            },
            "raw_articles": raw_articles,
            "filtered_articles": filtered_articles,
        }
        json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(raw_articles=raw_articles, filtered_links=filtered_links, output_path=csv_path, window_label=window_label)

        feed_record = IntelligenceRecord(
            source=self.source,
            dataset="finance_news_feed_json",
            record_key=f"feed|{self.language}|{window_label}",
            record_type="document",
            event_time=None,
            company_id=None,
            entity="HKG",
            title=f"HK Gov Business & Finance news feed ({self.language})",
            summary=f"HK Gov finance feed snapshot with {len(raw_articles)} items",
            region="Hong Kong",
            industry="Public Policy / Finance",
            tags=[self.source, "feed_snapshot", self.language],
            payload={
                "language": self.language,
                "window": window_label,
                "raw_count": len(raw_articles),
                "filtered_count": len(filtered_articles),
                "json_path": str(json_path.resolve()),
                "csv_path": str(csv_path.resolve()),
            },
            evidence_url="https://www.news.gov.hk/",
            lang=self.language,
            raw=None,
        )
        batch.intelligence_records.append(feed_record)
        batch.timeline_events.append(_timeline_from_record(feed_record, event_type="document"))

        for idx, item in enumerate(raw_articles):
            if not isinstance(item, dict):
                continue

            title = normalize_text(item.get("title")) or "(untitled news item)"
            description = normalize_text(item.get("description"))
            link = normalize_text(item.get("link"))
            pub_date = normalize_text(item.get("pubDate"))
            published_at = normalize_text(item.get("published_at"))
            event_time = extract_time_period_from_text(published_at or pub_date)
            news_id = extract_hk_gov_news_id(link)
            is_match = link in filtered_links if link else False

            payload: dict[str, Any] = {
                "title": title,
                "description": description,
                "link": link,
                "news_id": news_id,
                "pub_date": pub_date,
                "published_at": published_at,
                "is_gba_enterprise_match": is_match,
            }

            record_key = build_natural_key("hk_gov_news", item, fallback=f"idx-{idx}")
            record = IntelligenceRecord(
                source=self.source,
                dataset="finance_news_items",
                record_key=record_key,
                record_type="event",
                event_time=event_time,
                company_id=None,
                entity="HKG",
                title=title,
                summary=description or title,
                region="Hong Kong",
                industry="Public Policy / Finance",
                tags=[
                    self.source,
                    self.language,
                    "finance_news",
                    "gba_match" if is_match else "general",
                ],
                payload=payload,
                evidence_url=link or None,
                lang=self.language,
                raw=item,
            )
            batch.intelligence_records.append(record)
            batch.timeline_events.append(_timeline_from_record(record, event_type="event"))

            signal_time = event_time or str(datetime.now().year)
            signal_key = f"{self.source}|{record_key}|headline"
            signal_type = _infer_hkgov_news_signal_type(title, description, matched_gba_enterprise=is_match)
            batch.trigger_signals.append(
                TriggerSignal(
                    source=self.source,
                    dataset="finance_news_signals",
                    signal_key=signal_key,
                    signal_type=signal_type,
                    event_time=signal_time,
                    company_id=None,
                    entity="HKG",
                    indicator="headline",
                    value_num=None,
                    value_text="gba_enterprise_match" if is_match else None,
                    unit=None,
                    signal_text=title,
                    evidence_refs=[ref for ref in [link] if ref],
                    extra={
                        "language": self.language,
                        "pub_date": pub_date,
                        "published_at": published_at,
                        "news_id": news_id,
                        "is_gba_enterprise_match": is_match,
                    },
                )
            )

        batch.meta = {
            "language": self.language,
            "window": window_label,
            "since_months": self.since_months,
            "since_days": self.since_days,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "max_items": self.max_items,
            "filter_limit": self.filter_limit,
            "require_geo_and_business": self.require_geo_and_business,
            "items_fetched": len(raw_articles),
            "items_filtered": len(filtered_articles),
            "json_path": str(json_path.resolve()),
            "csv_path": str(csv_path.resolve()),
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


class DongfangCSVCollector(BaseCollector):
    source = "dongfang_eastmoney"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        csv_paths: tuple[str, ...],
        snapshot_date: str | None = None,
        min_increase_value: float = 0.0,
        min_holding_ratio: float = 0.0,
        top_n_rank_signal: int = 20,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.csv_paths = tuple(Path(path).expanduser().resolve() for path in csv_paths if normalize_text(path))
        self.snapshot_date = normalize_text(snapshot_date) or None
        self.min_increase_value = float(min_increase_value)
        self.min_holding_ratio = float(min_holding_ratio)
        self.top_n_rank_signal = max(1, int(top_n_rank_signal))

    @staticmethod
    def _market_from_filename(path: Path) -> str:
        name = path.stem
        if "北向" in name:
            return "northbound"
        if "沪股通" in name:
            return "shanghai_connect"
        if "深股通" in name:
            return "shenzhen_connect"
        if "港股通" in name:
            return "southbound"
        return safe_filename(name).lower()

    def _normalize_row(self, row: dict[str, Any], *, market: str, source_file: str) -> dict[str, Any]:
        date_text = normalize_text(row.get("日期")) or self.snapshot_date
        event_time = extract_time_period_from_text(date_text)
        code = _coerce_code_text(row.get("代码"))
        name = normalize_text(row.get("名称"))
        sector = normalize_text(row.get("所属板块"))
        rank = int(coerce_float(row.get("序号")) or 0)

        return {
            "market": market,
            "source_file": source_file,
            "date": date_text or None,
            "event_time": event_time,
            "rank": rank,
            "company_id": code,
            "company_name": name,
            "sector": sector or None,
            "close_price": coerce_float(row.get("今日收盘价")),
            "price_change_pct": _coerce_percent(row.get("今日涨跌幅")),
            "holding_shares": coerce_float(row.get("今日持股-股数")),
            "holding_value": coerce_float(row.get("今日持股-市值")),
            "holding_float_ratio_pct": _coerce_percent(row.get("今日持股-占流通股比")),
            "holding_total_ratio_pct": _coerce_percent(row.get("今日持股-占总股本比")),
            "increase_shares": coerce_float(row.get("今日增持估计-股数")),
            "increase_value": coerce_float(row.get("今日增持估计-市值")),
            "increase_value_pct": _coerce_percent(row.get("今日增持估计-市值增幅")),
            "increase_float_ratio_pct": _coerce_percent(row.get("今日增持估计-占流通股比")),
            "increase_total_ratio_pct": _coerce_percent(row.get("今日增持估计-占总股本比")),
            "raw_row": row,
        }

    @staticmethod
    def _summary_text(item: dict[str, Any]) -> str:
        parts = [item["company_name"] or item["company_id"] or "Unknown company"]
        if item.get("sector"):
            parts.append(f"sector {item['sector']}")
        if item.get("holding_value") is not None:
            parts.append(f"holding value {item['holding_value']:.2f}")
        if item.get("increase_value") is not None:
            parts.append(f"increase value {item['increase_value']:.2f}")
        if item.get("price_change_pct") is not None:
            parts.append(f"price change {item['price_change_pct']:.2f}%")
        return "; ".join(parts)

    def _signal_candidates(self, item: dict[str, Any]) -> list[tuple[str, str, float | None, str | None, str]]:
        signals: list[tuple[str, str, float | None, str | None, str]] = []
        holding_value = item.get("holding_value")
        increase_value = item.get("increase_value")
        holding_float_ratio_pct = item.get("holding_float_ratio_pct")
        increase_float_ratio_pct = item.get("increase_float_ratio_pct")
        price_change_pct = item.get("price_change_pct")
        rank = item.get("rank") or 0

        if rank and rank <= self.top_n_rank_signal:
            signals.append(
                (
                    "market_attention",
                    "ranking",
                    float(rank),
                    f"top_{self.top_n_rank_signal}",
                    f"{item['company_name']} ranks {rank} in {item['market']} holdings.",
                )
            )
        if increase_value is not None and increase_value > self.min_increase_value:
            signals.append(
                (
                    "growth",
                    "estimated_increase_value",
                    increase_value,
                    "currency",
                    f"{item['company_name']} saw estimated connect-flow increase of {increase_value:.2f}.",
                )
            )
        if holding_float_ratio_pct is not None and holding_float_ratio_pct > self.min_holding_ratio:
            signals.append(
                (
                    "market",
                    "holding_float_ratio_pct",
                    holding_float_ratio_pct,
                    "percent",
                    f"{item['company_name']} has {holding_float_ratio_pct:.2f}% connect holding over float shares.",
                )
            )
        if price_change_pct is not None and increase_value is not None and price_change_pct > 0 and increase_value > self.min_increase_value:
            signals.append(
                (
                    "growth",
                    "price_and_flow_resonance",
                    price_change_pct,
                    "percent",
                    f"{item['company_name']} rose {price_change_pct:.2f}% with simultaneous connect inflow.",
                )
            )
        if increase_float_ratio_pct is not None and increase_float_ratio_pct > 0:
            signals.append(
                (
                    "market_attention",
                    "increase_float_ratio_pct",
                    increase_float_ratio_pct,
                    "percent",
                    f"{item['company_name']} increased connect holding by {increase_float_ratio_pct:.2f}% of float shares.",
                )
            )
        if holding_value is not None and holding_value > 0 and item.get("sector"):
            signals.append(
                (
                    "market",
                    "sector_capital_presence",
                    holding_value,
                    "currency",
                    f"{item['company_name']} shows material connect capital presence in sector {item['sector']}.",
                )
            )
        return signals

    @staticmethod
    def _expected_market_token(market: str) -> str:
        mapping = {
            "northbound": "北向资金持股排行",
            "shanghai_connect": "沪股通持股排行",
            "shenzhen_connect": "深股通持股排行",
            "southbound": "港股通持股排行",
        }
        return mapping.get(market, market)

    def collect(self) -> CollectionBatch:
        if not self.csv_paths:
            raise ValueError("dongfang collector requires at least one CSV path")

        batch = CollectionBatch(source=self.source)
        out_dir = self.raw_dir / "dongfang_eastmoney"
        out_dir.mkdir(parents=True, exist_ok=True)

        imported_files = 0
        imported_rows = 0
        generated_signals = 0
        seen_companies: set[str] = set()

        for csv_path in self.csv_paths:
            if not csv_path.exists():
                raise FileNotFoundError(f"Dongfang CSV not found: {csv_path}")

            market = self._market_from_filename(csv_path)
            copied_path = out_dir / csv_path.name
            if copied_path.resolve() != csv_path.resolve():
                shutil.copy2(csv_path, copied_path)
            digest = sha256_file(copied_path)

            file_record = IntelligenceRecord(
                source=self.source,
                dataset="holdings_csv_snapshot",
                record_key=f"{market}|{digest}",
                record_type="document",
                event_time=self.snapshot_date,
                company_id=None,
                entity="CN",
                title=f"Dongfang {market} holdings snapshot",
                summary=f"Connect-flow holdings ranking snapshot from {csv_path.name}",
                region="China",
                industry="Listed Companies",
                tags=[self.source, market, "csv_snapshot"],
                payload={
                    "file_path": str(copied_path.resolve()),
                    "file_sha256": digest,
                    "market": market,
                    "snapshot_date": self.snapshot_date,
                    "source_filename": csv_path.name,
                },
                evidence_url=None,
                lang="zh",
                raw=None,
            )
            batch.intelligence_records.append(file_record)
            batch.timeline_events.append(_timeline_from_record(file_record, event_type="document"))
            imported_files += 1

            with copied_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for idx, row in enumerate(reader):
                    normalized = self._normalize_row(row, market=market, source_file=csv_path.name)
                    company_id = normalized["company_id"]
                    company_name = normalized["company_name"]
                    if not company_id or not company_name:
                        continue

                    imported_rows += 1
                    event_time = normalized["event_time"] or self.snapshot_date or str(datetime.now().year)
                    record_key = f"{market}|{company_id}|{normalized['date'] or 'unknown'}|{idx}"

                    row_record = IntelligenceRecord(
                        source=self.source,
                        dataset="holdings_rank_rows",
                        record_key=record_key,
                        record_type="metric",
                        event_time=event_time,
                        company_id=company_id,
                        entity="CN",
                        title=f"{company_name} connect holdings snapshot",
                        summary=self._summary_text(normalized),
                        region="China",
                        industry=normalized.get("sector"),
                        tags=[self.source, market, "connect_holdings", normalized.get("sector") or "unknown_sector"],
                        payload=normalized,
                        evidence_url=None,
                        lang="zh",
                        raw=row,
                    )
                    batch.intelligence_records.append(row_record)
                    batch.timeline_events.append(_timeline_from_record(row_record, event_type="metric"))

                    if company_id not in seen_companies:
                        batch.companies.append(
                            CompanyProfile(
                                source=self.source,
                                company_id=company_id,
                                canonical_name=company_name,
                                display_name=company_name,
                                country="China",
                                region="Mainland China",
                                city=None,
                                segments=["listed_company", "connect_flow"],
                                industries=[normalized["sector"]] if normalized.get("sector") else [],
                                profile_summary="Company observed in Dongfang connect holdings ranking.",
                                description=self._summary_text(normalized),
                                extra={
                                    "market": market,
                                    "last_snapshot_date": normalized.get("date"),
                                    "source_filename": csv_path.name,
                                },
                            )
                        )
                        seen_companies.add(company_id)

                    for signal_type, indicator, value_num, unit, signal_text in self._signal_candidates(normalized):
                        signal_key = f"{market}|{company_id}|{event_time}|{indicator}"
                        batch.trigger_signals.append(
                            TriggerSignal(
                                source=self.source,
                                dataset="connect_flow_signals",
                                signal_key=signal_key,
                                signal_type=signal_type,
                                event_time=event_time,
                                company_id=company_id,
                                entity="CN",
                                indicator=indicator,
                                value_num=value_num,
                                value_text=normalized.get("sector"),
                                unit=unit,
                                signal_text=signal_text,
                                evidence_refs=[str(copied_path.resolve())],
                                extra={
                                    "market": market,
                                    "rank": normalized.get("rank"),
                                    "company_name": company_name,
                                    "sector": normalized.get("sector"),
                                    "snapshot_date": normalized.get("date"),
                                    "close_price": normalized.get("close_price"),
                                    "price_change_pct": normalized.get("price_change_pct"),
                                    "holding_value": normalized.get("holding_value"),
                                    "increase_value": normalized.get("increase_value"),
                                },
                            )
                        )
                        generated_signals += 1

        batch.meta = {
            "csv_paths": [str(path) for path in self.csv_paths],
            "snapshot_date": self.snapshot_date,
            "files_imported": imported_files,
            "rows_imported": imported_rows,
            "companies_discovered": len(seen_companies),
            "signals_generated": generated_signals,
            "min_increase_value": self.min_increase_value,
            "min_holding_ratio": self.min_holding_ratio,
            "top_n_rank_signal": self.top_n_rank_signal,
        }
        return batch


class DongfangAKShareCollector(DongfangCSVCollector):
    source = "dongfang_eastmoney"

    def __init__(
        self,
        *,
        raw_dir: str | Path,
        snapshot_date: str | None = None,
        min_increase_value: float = 0.0,
        min_holding_ratio: float = 0.0,
        top_n_rank_signal: int = 20,
        fetch_markets: tuple[str, ...] = ("northbound", "shanghai_connect", "shenzhen_connect", "southbound"),
        retry: int = 3,
        sleep_seconds: float = 1.0,
    ) -> None:
        super().__init__(
            raw_dir=raw_dir,
            csv_paths=(),
            snapshot_date=snapshot_date,
            min_increase_value=min_increase_value,
            min_holding_ratio=min_holding_ratio,
            top_n_rank_signal=top_n_rank_signal,
        )
        self.fetch_markets = tuple(fetch_markets)
        self.retry = max(1, int(retry))
        self.sleep_seconds = max(0.0, float(sleep_seconds))

    @staticmethod
    def _ak_market_name(market: str) -> str:
        mapping = {
            "northbound": "北向",
            "shanghai_connect": "沪股通",
            "shenzhen_connect": "深股通",
        }
        return mapping[market]

    @staticmethod
    def _southbound_trade_dates() -> tuple[str, ...]:
        return (
            "20260505",
            "20260502",
            "20260430",
            "20260429",
            "20260428",
            "20260427",
            "20260424",
        )

    @staticmethod
    def _southbound_dataframe_from_statistics(df: Any):
        import pandas as pd

        if df is None:
            return pd.DataFrame()

        renamed = pd.DataFrame(df).copy()
        if renamed.empty:
            return pd.DataFrame()
        renamed["序号"] = range(1, len(renamed) + 1)
        renamed["代码"] = renamed.get("股票代码")
        renamed["名称"] = renamed.get("股票简称")
        renamed["今日收盘价"] = renamed.get("当日收盘价")
        renamed["今日涨跌幅"] = renamed.get("当日涨跌幅")
        renamed["今日持股-股数"] = renamed.get("持股数量")
        renamed["今日持股-市值"] = renamed.get("持股市值")
        renamed["今日持股-占流通股比"] = renamed.get("持股数量占发行股百分比")
        renamed["今日持股-占总股本比"] = renamed.get("持股数量占发行股百分比")
        renamed["今日增持估计-股数"] = None
        renamed["今日增持估计-市值"] = renamed.get("持股市值变化-1日")
        renamed["今日增持估计-市值增幅"] = None
        renamed["今日增持估计-占流通股比"] = None
        renamed["今日增持估计-占总股本比"] = None
        renamed["所属板块"] = "Hong Kong Connect"
        renamed["日期"] = pd.to_datetime(renamed.get("持股日期"), errors="coerce").dt.strftime("%Y-%m-%d")
        return renamed[
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
            ]
        ]

    def _fetch_market_df(self, market: str):
        import os
        import pandas as pd

        for proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
            os.environ.pop(proxy_var, None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"

        import akshare as ak

        last_error: Exception | None = None
        if market == "southbound":
            for trade_date in self._southbound_trade_dates():
                for attempt in range(1, self.retry + 1):
                    try:
                        raw_df = ak.stock_hsgt_stock_statistics_em(
                            symbol="南向持股",
                            start_date=trade_date,
                            end_date=trade_date,
                        )
                        df = self._southbound_dataframe_from_statistics(raw_df)
                        if df is None or df.empty:
                            break
                        if self.snapshot_date is None:
                            self.snapshot_date = trade_date[:4] + "-" + trade_date[4:6] + "-" + trade_date[6:]
                        return df
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        if attempt < self.retry and self.sleep_seconds > 0:
                            time.sleep(self.sleep_seconds)
                if self.sleep_seconds > 0:
                    time.sleep(self.sleep_seconds)
            if last_error is not None:
                raise last_error
            return pd.DataFrame()

        ak_market = self._ak_market_name(market)
        for attempt in range(1, self.retry + 1):
            try:
                try:
                    df = ak.stock_hsgt_hold_stock_em(market=ak_market, indicator="今日排行")
                except TypeError:
                    df = ak.stock_hsgt_hold_stock_em(market=ak_market)
                if df is None:
                    return pd.DataFrame()
                return df
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.retry and self.sleep_seconds > 0:
                    time.sleep(self.sleep_seconds)
        if last_error is not None:
            raise last_error
        return pd.DataFrame()

    def collect(self) -> CollectionBatch:
        import pandas as pd

        out_dir = self.raw_dir / "dongfang_eastmoney"
        out_dir.mkdir(parents=True, exist_ok=True)
        fetched_paths: list[str] = []
        fetched_meta: list[dict[str, Any]] = []

        for market in self.fetch_markets:
            df = self._fetch_market_df(market)
            if df is None or df.empty:
                continue
            expected_name = f"{self._expected_market_token(market)}.csv"
            output_path = out_dir / expected_name
            cleaned_df = pd.DataFrame(df).copy()
            cleaned_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            fetched_paths.append(str(output_path.resolve()))
            fetched_meta.append(
                {
                    "market": market,
                    "rows": int(len(cleaned_df)),
                    "path": str(output_path.resolve()),
                }
            )
            if self.sleep_seconds > 0:
                time.sleep(self.sleep_seconds)

        self.csv_paths = tuple(Path(path) for path in fetched_paths)
        batch = super().collect()
        batch.meta = {
            **batch.meta,
            "fetch_mode": "akshare",
            "fetched_files": fetched_meta,
        }
        return batch

