from __future__ import annotations

from typing import Any

import requests

DEFAULT_BASE = "https://www.censtatd.gov.hk"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

RETAIL_SALES_TABLE_ID = "620-67002"
EXTERNAL_TRADE_TABLE_ID = "410-50001A"


def extract_censtatd_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("dataSet")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


class CENSTATDClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        session: requests.Session | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json,text/plain,*/*",
                "Origin": "https://www.censtatd.gov.hk",
                "Referer": "https://www.censtatd.gov.hk/en/web_table.html",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def get_table(self, table_id: str, *, lang: str = "en", full_series: bool = True, timeout: int = 60) -> dict[str, Any]:
        params: dict[str, Any] = {"id": table_id, "lang": lang}
        if full_series:
            params["full_series"] = 1
        resp = self._session.get(f"{self.base_url}/api/get.php", params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        status = ((payload.get("header") or {}).get("status") or {}) if isinstance(payload, dict) else {}
        if status.get("code") not in (None, 0):
            raise RuntimeError(f"CENSTATD API reported failure for table {table_id}: {status}")
        return payload

    def retail_sales(self, *, lang: str = "en", full_series: bool = True, timeout: int = 60) -> dict[str, Any]:
        return self.get_table(RETAIL_SALES_TABLE_ID, lang=lang, full_series=full_series, timeout=timeout)

    def external_merchandise_trade(self, *, lang: str = "en", full_series: bool = True, timeout: int = 60) -> dict[str, Any]:
        return self.get_table(EXTERNAL_TRADE_TABLE_ID, lang=lang, full_series=full_series, timeout=timeout)
