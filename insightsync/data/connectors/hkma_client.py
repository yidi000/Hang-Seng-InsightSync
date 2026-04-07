from __future__ import annotations

from typing import Any, Literal, Mapping, MutableMapping

import requests

DEFAULT_BASE = "https://api.hkma.gov.hk/public"
DEFAULT_USER_AGENT = "insightsync-hkma/1.0"


class HKMAClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        session: requests.Session | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", user_agent)

    def get(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: int = 60,
    ) -> requests.Response:
        p = path.lstrip("/")
        url = f"{self.base_url}/{p}"
        r = self._session.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r

    def get_json(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: int = 60,
        expect_success: bool = True,
    ) -> Any:
        data = self.get(path, params=params, timeout=timeout).json()
        if expect_success:
            hdr = data.get("header")
            if isinstance(hdr, dict) and hdr.get("success") is False:
                raise RuntimeError(f"HKMA API reported failure: {data}")
        return data

    def monthly_statistical_bulletin(
        self,
        subsection: str,
        resource: str,
        *,
        pagesize: int = 30,
        offset: int = 0,
        sortby: str | None = None,
        sortorder: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> Any:
        path = f"market-data-and-statistics/monthly-statistical-bulletin/{subsection}/{resource}"
        q: MutableMapping[str, Any] = {"pagesize": pagesize, "offset": offset}
        if sortby is not None:
            q["sortby"] = sortby
        if sortorder is not None:
            q["sortorder"] = sortorder
        if extra:
            q.update(extra)
        return self.get_json(path, params=q)

    def press_releases(
        self,
        *,
        lang: str = "en",
        pagesize: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.get_json(
            "press-releases",
            params={"lang": lang, "pagesize": pagesize, "offset": offset},
        )

    def exchange_rates_eeri_daily(
        self,
        *,
        pagesize: int = 30,
        offset: int = 0,
        sortby: str = "end_of_day",
        sortorder: Literal["asc", "desc"] = "desc",
    ) -> dict[str, Any]:
        return self.monthly_statistical_bulletin(
            "er-ir",
            "er-eeri-daily",
            pagesize=pagesize,
            offset=offset,
            sortby=sortby,
            sortorder=sortorder,
        )

    def hkd_interbank_rates_daily(
        self,
        *,
        pagesize: int = 30,
        offset: int = 0,
        sortby: str = "end_of_day",
        sortorder: Literal["asc", "desc"] = "desc",
    ) -> dict[str, Any]:
        return self.monthly_statistical_bulletin(
            "er-ir",
            "hk-interbank-ir-daily",
            pagesize=pagesize,
            offset=offset,
            sortby=sortby,
            sortorder=sortorder,
        )

    def composite_interest_rate_monthly(
        self,
        *,
        pagesize: int = 24,
        offset: int = 0,
        sortby: str = "end_of_month",
        sortorder: Literal["asc", "desc"] = "desc",
    ) -> dict[str, Any]:
        return self.monthly_statistical_bulletin(
            "er-ir",
            "composite-ir",
            pagesize=pagesize,
            offset=offset,
            sortby=sortby,
            sortorder=sortorder,
        )

