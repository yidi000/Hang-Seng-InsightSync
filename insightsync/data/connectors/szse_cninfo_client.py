from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CNINFO_BASE_URL = "http://www.cninfo.com.cn"
CNINFO_QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE_URL = "http://static.cninfo.com.cn"
CN_TZ = timezone(timedelta(hours=8))
DEFAULT_USER_AGENT = "insightsync-szse-cninfo/1.0"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def timestamp_ms_to_datetime(value: Any) -> str:
    """Convert CNINFO millisecond timestamp to local CN datetime string."""
    ts = _coerce_int(value)
    if ts is None:
        return ""
    try:
        dt = datetime.fromtimestamp(ts / 1000, tz=CN_TZ)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OverflowError, OSError, ValueError):
        return ""


def timestamp_ms_to_date(value: Any) -> str:
    dt_text = timestamp_ms_to_datetime(value)
    if not dt_text:
        return ""
    return dt_text.split(" ")[0]


def build_cninfo_pdf_url(adjunct_url: Any) -> str:
    raw = _normalize_text(adjunct_url)
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return urljoin(CNINFO_STATIC_BASE_URL.rstrip("/") + "/", raw.lstrip("/"))


class SZSECninfoClient:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout_seconds: int = 15,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        if session is not None:
            self.session = session
        else:
            self.session = requests.Session()
            retry = Retry(
                total=3,
                backoff_factor=1.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset(["POST"]),
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

        self.session.headers.setdefault("User-Agent", user_agent)
        self.session.headers.setdefault("Accept", "application/json")
        self.session.headers.setdefault("Referer", CNINFO_BASE_URL + "/")
        self.session.headers.setdefault("X-Requested-With", "XMLHttpRequest")

    def fetch_announcements(
        self,
        *,
        start_date: str,
        end_date: str,
        plate: str = "sz",
        stock: str = "",
        tab_name: str = "fulltext",
        page_size: int = 30,
        max_records: int = 50000,
        delay_seconds: float = 0.3,
    ) -> dict[str, Any]:
        if page_size <= 0:
            raise ValueError("page_size must be > 0")
        if max_records <= 0:
            return {
                "items": [],
                "meta": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "plate": plate,
                    "stock": stock,
                    "tab_name": tab_name,
                    "page_size": page_size,
                    "pages_fetched": 0,
                    "total_record_num": None,
                    "total_pages": None,
                    "has_more_last": None,
                },
            }

        all_items: list[dict[str, Any]] = []
        page_num = 1
        pages_fetched = 0
        total_record_num: int | None = None
        total_pages: int | None = None
        has_more_last: bool | None = None

        while len(all_items) < max_records:
            params = {
                "pageNum": page_num,
                "pageSize": page_size,
                "tabName": tab_name,
                "stock": stock,
                "plate": plate,
                "seDate": f"{start_date}~{end_date}",
            }

            resp = self.session.post(CNINFO_QUERY_URL, data=params, timeout=self.timeout_seconds)
            resp.raise_for_status()
            payload = resp.json()
            pages_fetched += 1

            announcements = payload.get("announcements", [])
            if not isinstance(announcements, list) or not announcements:
                break

            for item in announcements:
                if not isinstance(item, dict):
                    continue
                all_items.append(item)
                if len(all_items) >= max_records:
                    break

            total_record_num = _coerce_int(payload.get("totalRecordNum"))
            total_pages = _coerce_int(payload.get("totalpages"))
            raw_has_more = payload.get("hasMore")
            has_more_last = None if raw_has_more is None else bool(raw_has_more)

            if len(all_items) >= max_records:
                break
            if has_more_last is False:
                break
            if total_pages is not None and total_pages > 0 and page_num >= total_pages:
                break
            # Fallback only when upstream does not provide paging indicators.
            if has_more_last is None and (total_pages is None or total_pages <= 0) and len(announcements) < page_size:
                break

            page_num += 1
            if delay_seconds > 0:
                time.sleep(delay_seconds)

        return {
            "items": all_items[:max_records],
            "meta": {
                "start_date": start_date,
                "end_date": end_date,
                "plate": plate,
                "stock": stock,
                "tab_name": tab_name,
                "page_size": page_size,
                "max_records": max_records,
                "pages_fetched": pages_fetched,
                "total_record_num": total_record_num,
                "total_pages": total_pages,
                "has_more_last": has_more_last,
            },
        }
