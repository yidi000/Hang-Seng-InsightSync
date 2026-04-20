from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO string."""

    return datetime.now(timezone.utc).isoformat()


_TIMESTAMP_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y-%m",
    "%Y",
)


def parse_timestamp(value: Any) -> datetime | None:
    """Parse a loose timestamp string into a timezone-aware datetime.

    Accepts ``None``/empty → ``None``. Naive values are assumed to be UTC.
    """

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    # datetime.fromisoformat handles most ISO variants including offsets on 3.11+.
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is None:
        for fmt in _TIMESTAMP_FORMATS:
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def stable_json(value: Any) -> str:
    """Serialize JSON-compatible data in a stable way.

    Non-JSON-native values (``datetime``, ``date``) are coerced to their
    ISO-8601 string form so hashes remain stable across code that receives
    either raw strings or parsed datetimes.
    """

    def _default(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_default)


def stable_hash(value: Any) -> str:
    """Return a stable SHA-256 hash for JSON-compatible data."""

    if isinstance(value, str):
        payload = value
    else:
        payload = stable_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
