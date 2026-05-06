from __future__ import annotations

from typing import Any


COMPANY_ID_KEYS = ("company_id", "stock_code", "ticker", "code", "security_code")
EXCLUDED_MACRO_SOURCE_TOKENS = ("censtatd", "guangdong", "hkma", "adb", "kpmg")


def extract_company_id_from_payload(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    for key in COMPANY_ID_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return None


def canonical_company_token(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def is_company_mappable_source(source: str | None, dataset: str | None) -> bool:
    source_key = f"{source or ''} {dataset or ''}".lower()
    return not any(token in source_key for token in EXCLUDED_MACRO_SOURCE_TOKENS)


def mapping_coverage(*, mapped: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return mapped / total
