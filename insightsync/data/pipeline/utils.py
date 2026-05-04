from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DATE_KEYS = (
    "end_of_day",
    "end_of_month",
    "date",
    "release_date",
    "release_datetime",
    "publish_date",
    "effective_date",
    "time_period",
)

MISSING_TOKENS = {"", "-", "--", "na", "n/a", "null", "none"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_json_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(text: str, *, max_len: int = 120) -> str:
    cleaned = re.sub(r"[^\w\-. ]+", "_", text.strip(), flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    if not cleaned:
        cleaned = "untitled"
    return cleaned[:max_len]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def build_natural_key(dataset: str, record: Mapping[str, Any], *, fallback: str = "") -> str:
    key_fields = (
        "id",
        "uuid",
        "ref_no",
        "reference_no",
        "reference_number",
        "end_of_day",
        "end_of_month",
        "release_date",
        "title",
        "subject",
        "time_period",
    )
    parts: list[str] = []
    for key in key_fields:
        value = normalize_text(record.get(key))
        if value:
            parts.append(value)
    if fallback:
        parts.append(fallback)
    if not parts:
        parts.append(stable_json_hash(record)[:16])
    return f"{dataset}|" + "|".join(parts)[:400]


def extract_time_period_from_text(text: str | None) -> str | None:
    if not text:
        return None
    value = text.strip()
    if not value:
        return None

    m = re.fullmatch(r"(20\d{2})(\d{2})(\d{2})", value)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    m = re.fullmatch(r"(20\d{2})(\d{2})", value)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    m = re.search(r"(20\d{2})[\u5e74/\-.](\d{1,2})[\u6708/\-.](\d{1,2})", value)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    m = re.search(r"(20\d{2})[\u5e74/\-.](\d{1,2})[\u6708]?", value)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    m = re.search(r"\b(20\d{2})\b", value)
    if m:
        return m.group(1)
    return None


def detect_record_time(record: Mapping[str, Any]) -> str | None:
    for key in DATE_KEYS:
        value = normalize_text(record.get(key))
        if not value:
            continue
        period = extract_time_period_from_text(value)
        if period:
            return period
    for value in record.values():
        if isinstance(value, str):
            period = extract_time_period_from_text(value)
            if period:
                return period
    return None


def is_likely_date_string(value: str) -> bool:
    if not value:
        return False
    if re.fullmatch(r"20\d{2}(\d{2}){0,2}", value):
        return True
    if re.search(r"(20\d{2})[\u5e74/\-.]\d{1,2}", value):
        return True
    return False


def coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None
    if s.lower() in MISSING_TOKENS:
        return None
    if is_likely_date_string(s):
        return None

    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]

    multiplier = 1.0
    if s.endswith("亿"):
        multiplier = 1e8
        s = s[:-1]
    elif s.endswith("万"):
        multiplier = 1e4
        s = s[:-1]
    elif s.endswith("千"):
        multiplier = 1e3
        s = s[:-1]

    s = s.replace("HK$", "").replace("$", "")
    s = s.replace(",", "").replace("，", "").replace(" ", "").replace("\u00a0", "")
    s = s.replace("%", "").replace("％", "")

    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        out = float(m.group(0)) * multiplier
    except ValueError:
        return None
    if negative:
        out = -out
    return out


def infer_unit(indicator: str | None, value_text: str | None) -> str | None:
    if value_text and ("%" in value_text or "％" in value_text):
        return "percent"
    key = (indicator or "").lower()
    if "rate" in key or "ratio" in key or "hibor" in key:
        return "percent"
    if "usd" in key or "hkd" in key or "cny" in key or "fob" in key:
        return "currency"
    return None
