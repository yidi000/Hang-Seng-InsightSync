from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CollectionBatch, CompanyProfile
from .storage import SQLiteRepository
from .utils import normalize_text, utc_now_iso

_MARKET_SOURCES = ("hkex_disclosure", "szse_cninfo")
_GENERIC_ALIAS_STOPWORDS = {
    "limited",
    "holdings",
    "holding",
    "group",
    "company",
    "co",
    "co.",
    "inc",
    "ltd",
    "bank",
    "corporation",
    "有限公司",
    "股份有限公司",
    "集团",
    "公司",
}


def _normalize_alias(value: Any) -> str:
    text = normalize_text(value).lower()
    if not text:
        return ""
    return re.sub(r"\s+", " ", text)


def _is_ascii_text(text: str) -> bool:
    return all(ord(ch) < 128 for ch in text)


def _is_usable_alias(alias: str) -> bool:
    if not alias:
        return False
    if alias in _GENERIC_ALIAS_STOPWORDS:
        return False
    if alias.isdigit() and len(alias) < 4:
        return False
    if _is_ascii_text(alias):
        compact = re.sub(r"[^a-z0-9]+", "", alias)
        if len(compact) < 4:
            return False
    else:
        if len(alias) < 2:
            return False
    return True


def _contains_alias(text: str, alias: str) -> bool:
    if not text or not alias:
        return False

    if alias.isdigit():
        return re.search(rf"(?<!\\d){re.escape(alias)}(?!\\d)", text) is not None

    if _is_ascii_text(alias) and re.search(r"[a-z]", alias):
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        return re.search(pattern, text) is not None

    return alias in text


def _safe_load_json(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_market_company_name(source: str, payload: dict[str, Any], title: str | None) -> str:
    if source == "szse_cninfo":
        candidates = [
            payload.get("stock_name"),
            payload.get("secName"),
            payload.get("sec_name"),
        ]
        for value in candidates:
            text = normalize_text(value)
            if text:
                return text

    if source == "hkex_disclosure":
        candidates = [
            payload.get("company_name"),
            payload.get("stock_name"),
        ]
        for value in candidates:
            text = normalize_text(value)
            if text:
                return text

        title_text = normalize_text(title)
        lower_title = title_text.lower()
        suffix = " annual report"
        if title_text and suffix in lower_title:
            idx = lower_title.find(suffix)
            base = title_text[:idx].strip(" -")
            if base:
                return base

    return normalize_text(title)


def _build_market_company_profiles(repo: SQLiteRepository) -> list[CompanyProfile]:
    rows = repo.conn.execute(
        """
        SELECT source, company_id, title, industry, payload_json
        FROM intelligence_records
        WHERE source IN (?, ?)
          AND company_id IS NOT NULL
          AND TRIM(company_id) <> ''
        ORDER BY id ASC
        """,
        _MARKET_SOURCES,
    ).fetchall()

    profiles: dict[str, CompanyProfile] = {}
    for row in rows:
        source = normalize_text(row["source"])
        company_id = normalize_text(row["company_id"])
        title = normalize_text(row["title"])
        industry = normalize_text(row["industry"]) or "Listed Companies"
        payload = _safe_load_json(row["payload_json"])

        if not company_id:
            continue

        canonical_name = _extract_market_company_name(source, payload, title)
        if not canonical_name:
            continue

        if source == "szse_cninfo":
            country = "China"
            region = "Mainland China"
            city = None
            segments = ["listed_company", "szse"]
        else:
            country = "China"
            region = "Hong Kong"
            city = "Hong Kong"
            segments = ["listed_company", "hkex"]

        existing = profiles.get(company_id)
        if existing is None:
            profiles[company_id] = CompanyProfile(
                source="company_mapper",
                company_id=company_id,
                canonical_name=canonical_name,
                display_name=canonical_name,
                country=country,
                region=region,
                city=city,
                segments=segments,
                industries=[industry],
                website_url=None,
                linkedin_url=None,
                facebook_url=None,
                x_url=None,
                instagram_url=None,
                wikipedia_url=None,
                profile_summary=None,
                description=f"Auto-discovered from {source}",
                extra={"discovered_from": source},
            )
            continue

        if canonical_name and len(canonical_name) > len(existing.canonical_name):
            existing.canonical_name = canonical_name
            existing.display_name = canonical_name

        merged_segments = sorted(set(existing.segments + segments))
        existing.segments = merged_segments
        if industry and industry not in existing.industries:
            existing.industries.append(industry)

    return list(profiles.values())


def _build_alias_index(repo: SQLiteRepository) -> list[tuple[str, str]]:
    alias_to_company_ids: dict[str, set[str]] = {}

    company_rows = repo.conn.execute(
        """
        SELECT company_id, canonical_name, display_name
        FROM companies
        ORDER BY id DESC
        """
    ).fetchall()
    for row in company_rows:
        company_id = normalize_text(row["company_id"])
        aliases = [
            normalize_text(row["canonical_name"]),
            normalize_text(row["display_name"]),
            company_id,
        ]
        for alias_raw in aliases:
            alias = _normalize_alias(alias_raw)
            if not _is_usable_alias(alias):
                continue
            alias_to_company_ids.setdefault(alias, set()).add(company_id)

    market_rows = repo.conn.execute(
        """
        SELECT source, company_id, title, payload_json
        FROM intelligence_records
        WHERE source IN (?, ?)
          AND company_id IS NOT NULL
          AND TRIM(company_id) <> ''
        ORDER BY id DESC
        """,
        _MARKET_SOURCES,
    ).fetchall()
    for row in market_rows:
        source = normalize_text(row["source"])
        company_id = normalize_text(row["company_id"])
        payload = _safe_load_json(row["payload_json"])
        title = normalize_text(row["title"])

        alias_candidates = [
            company_id,
            _extract_market_company_name(source, payload, title),
            normalize_text(payload.get("company_name")),
            normalize_text(payload.get("stock_name")),
            normalize_text(payload.get("secName")),
        ]
        for alias_raw in alias_candidates:
            alias = _normalize_alias(alias_raw)
            if not _is_usable_alias(alias):
                continue
            alias_to_company_ids.setdefault(alias, set()).add(company_id)

    unique_aliases: list[tuple[str, str]] = []
    for alias, company_ids in alias_to_company_ids.items():
        if len(company_ids) != 1:
            continue
        unique_aliases.append((alias, next(iter(company_ids))))

    unique_aliases.sort(key=lambda item: len(item[0]), reverse=True)
    return unique_aliases


def _match_company_id(text: str, alias_index: list[tuple[str, str]]) -> tuple[str | None, str | None, float | None]:
    normalized_text = _normalize_alias(text)
    if not normalized_text:
        return None, None, None

    matched_by_company: dict[str, tuple[str, float]] = {}
    for alias, company_id in alias_index:
        if not _contains_alias(normalized_text, alias):
            continue

        score = float(len(alias))
        existing = matched_by_company.get(company_id)
        if existing is None or score > existing[1]:
            matched_by_company[company_id] = (alias, score)

    if len(matched_by_company) != 1:
        return None, None, None

    company_id, (alias, _) = next(iter(matched_by_company.items()))
    if normalized_text == alias:
        confidence = 0.95
    elif len(alias) >= 10:
        confidence = 0.92
    elif len(alias) >= 6:
        confidence = 0.88
    else:
        confidence = 0.85
    return company_id, alias, confidence


def _insert_mapping_audit(
    repo: SQLiteRepository,
    *,
    run_id: str,
    target_table: str,
    target_row_id: int,
    old_company_id: str | None,
    new_company_id: str,
    mapping_method: str,
    confidence: float | None,
    matched_alias: str | None,
    matched_context: str | None,
) -> None:
    repo.conn.execute(
        """
        INSERT OR IGNORE INTO company_mapping_audit(
          run_id, target_table, target_row_id, old_company_id, new_company_id,
          mapping_method, confidence, matched_alias, matched_context, mapped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            target_table,
            target_row_id,
            old_company_id,
            new_company_id,
            mapping_method,
            confidence,
            matched_alias,
            matched_context,
            utc_now_iso(),
        ),
    )


def _build_intelligence_text(row: Any) -> str:
    payload = _safe_load_json(row["payload_json"])
    parts = [
        normalize_text(row["title"]),
        normalize_text(row["summary"]),
        normalize_text(payload.get("company_name")),
        normalize_text(payload.get("stock_name")),
        normalize_text(payload.get("secName")),
        normalize_text(payload.get("entity")),
    ]
    return " | ".join([x for x in parts if x])


def _build_signal_text(row: Any) -> str:
    extra = _safe_load_json(row["extra_json"])
    parts = [
        normalize_text(row["signal_text"]),
        normalize_text(row["value_text"]),
        normalize_text(extra.get("company_name")),
        normalize_text(extra.get("stock_name")),
        normalize_text(extra.get("secName")),
    ]
    return " | ".join([x for x in parts if x])


def sync_market_companies_impl(
    repo: SQLiteRepository,
    *,
    run_id: str,
    dry_run: bool,
) -> dict[str, Any]:
    profiles = _build_market_company_profiles(repo)

    inserted = 0
    if profiles and not dry_run:
        batch = CollectionBatch(source="company_mapper")
        batch.companies.extend(profiles)
        inserted = repo.persist_batch(run_id, batch)["companies"]

    return {
        "dry_run": dry_run,
        "candidate_companies": len(profiles),
        "inserted_companies": inserted,
    }


def backfill_company_ids_impl(
    repo: SQLiteRepository,
    *,
    run_id: str,
    dry_run: bool,
    limit: int,
) -> dict[str, Any]:
    alias_index = _build_alias_index(repo)

    intelligence_sql = (
        "SELECT id, company_id, title, summary, payload_json FROM intelligence_records "
        "WHERE company_id IS NULL ORDER BY id ASC"
    )
    signal_sql = (
        "SELECT id, company_id, signal_text, value_text, extra_json FROM trigger_signals "
        "WHERE company_id IS NULL ORDER BY id ASC"
    )
    if limit > 0:
        intelligence_sql += " LIMIT ?"
        signal_sql += " LIMIT ?"
        intelligence_rows = repo.conn.execute(intelligence_sql, (limit,)).fetchall()
        signal_rows = repo.conn.execute(signal_sql, (limit,)).fetchall()
    else:
        intelligence_rows = repo.conn.execute(intelligence_sql).fetchall()
        signal_rows = repo.conn.execute(signal_sql).fetchall()

    int_matched = 0
    int_updated = 0
    sig_matched = 0
    sig_updated = 0

    with repo.conn:
        for row in intelligence_rows:
            text = _build_intelligence_text(row)
            company_id, alias, confidence = _match_company_id(text, alias_index)
            if not company_id:
                continue
            int_matched += 1

            if not dry_run:
                repo.conn.execute(
                    "UPDATE intelligence_records SET company_id = ? WHERE id = ? AND company_id IS NULL",
                    (company_id, row["id"]),
                )
                int_updated += 1
                _insert_mapping_audit(
                    repo,
                    run_id=run_id,
                    target_table="intelligence_records",
                    target_row_id=int(row["id"]),
                    old_company_id=None,
                    new_company_id=company_id,
                    mapping_method="alias_match",
                    confidence=confidence,
                    matched_alias=alias,
                    matched_context=text[:400],
                )

        for row in signal_rows:
            text = _build_signal_text(row)
            company_id, alias, confidence = _match_company_id(text, alias_index)
            if not company_id:
                continue
            sig_matched += 1

            if not dry_run:
                repo.conn.execute(
                    "UPDATE trigger_signals SET company_id = ? WHERE id = ? AND company_id IS NULL",
                    (company_id, row["id"]),
                )
                sig_updated += 1
                _insert_mapping_audit(
                    repo,
                    run_id=run_id,
                    target_table="trigger_signals",
                    target_row_id=int(row["id"]),
                    old_company_id=None,
                    new_company_id=company_id,
                    mapping_method="alias_match",
                    confidence=confidence,
                    matched_alias=alias,
                    matched_context=text[:400],
                )

    return {
        "dry_run": dry_run,
        "alias_count": len(alias_index),
        "intelligence_records_scanned": len(intelligence_rows),
        "intelligence_records_matched": int_matched,
        "intelligence_records_updated": int_updated,
        "trigger_signals_scanned": len(signal_rows),
        "trigger_signals_matched": sig_matched,
        "trigger_signals_updated": sig_updated,
    }


def run_company_mapping_once(
    db_path: str | Path,
    *,
    sync_market_companies: bool = True,
    backfill_company_ids: bool = True,
    dry_run: bool = False,
    limit: int = 0,
) -> dict[str, Any]:
    target_db = Path(db_path).expanduser().resolve()
    run_id = datetime.now(timezone.utc).strftime("company-map-%Y%m%dT%H%M%SZ")
    started_at = utc_now_iso()

    summary: dict[str, Any] = {
        "run_id": run_id,
        "db_path": str(target_db),
        "started_at": started_at,
        "status": "success",
        "sync_market_companies": None,
        "backfill_company_ids": None,
    }

    with SQLiteRepository(target_db) as repo:
        repo.start_run(run_id, started_at=started_at)
        try:
            if sync_market_companies:
                summary["sync_market_companies"] = sync_market_companies_impl(
                    repo,
                    run_id=run_id,
                    dry_run=dry_run,
                )
            if backfill_company_ids:
                summary["backfill_company_ids"] = backfill_company_ids_impl(
                    repo,
                    run_id=run_id,
                    dry_run=dry_run,
                    limit=max(0, int(limit)),
                )
            summary["finished_at"] = utc_now_iso()
            repo.finish_run(
                run_id,
                status="success",
                message="company mapping completed",
                summary=summary,
            )
        except Exception as exc:  # noqa: BLE001
            summary["status"] = "failed"
            summary["error"] = str(exc)
            summary["finished_at"] = utc_now_iso()
            repo.finish_run(
                run_id,
                status="failed",
                message=str(exc),
                summary=summary,
            )
            raise

    return summary
