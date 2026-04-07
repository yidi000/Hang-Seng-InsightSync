from __future__ import annotations

import time
from typing import Any, BinaryIO, Mapping, Sequence

import requests

DEFAULT_BASE = "https://kidb.adb.org"
DEFAULT_USER_AGENT = "insightsync-adb-kidb/1.0"

ECONOMY_TABLES_XLSX_KI2025 = (
    "https://www.adb.org/sites/default/files/publication/1067171/ki2025-economy-tables.xlsx"
)


def parse_kidb_sdmx_timeseries(
    payload: Mapping[str, Any],
    *,
    dataset_index: int = 0,
    series_index: int = 0,
) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []

    datasets = data.get("datasets") or []
    if dataset_index < 0 or dataset_index >= len(datasets):
        return []
    ds = datasets[dataset_index]
    struct_idx = int(ds.get("structure", 0) or 0)
    structures: Sequence[Any] = data.get("structures") or []
    if struct_idx < 0 or struct_idx >= len(structures):
        return []

    struct = structures[struct_idx]
    periods: list[str] = []
    for dim in (struct.get("dimensions") or {}).get("observation") or []:
        if dim.get("id") == "TIME_PERIOD" or dim.get("role") == "time":
            for v in dim.get("values") or []:
                if isinstance(v, dict):
                    label = v.get("value")
                    if label is None:
                        label = v.get("id")
                    periods.append(str(label) if label is not None else "")
                else:
                    periods.append(str(v))
            break

    unit_name: str | None = None
    mult_pow10: int | None = None
    for attr in (struct.get("attributes") or {}).get("observation") or []:
        aid = attr.get("id")
        vals = attr.get("values") or []
        if aid == "UNIT" and vals:
            unit_name = (vals[0].get("name") or vals[0].get("id")) if isinstance(vals[0], dict) else str(vals[0])
        if aid == "UNIT_MULT" and vals:
            raw = vals[0].get("id") if isinstance(vals[0], dict) else vals[0]
            try:
                mult_pow10 = int(str(raw))
            except (TypeError, ValueError):
                mult_pow10 = None

    series_map = ds.get("series") or {}
    if not series_map:
        return []
    keys = sorted(series_map.keys(), key=lambda x: [int(p) if p.isdigit() else p for p in str(x).split(".")])
    if series_index < 0 or series_index >= len(keys):
        return []
    ser = series_map[keys[series_index]]
    observations = ser.get("observations") or {}
    obs_keys = sorted(observations.keys(), key=lambda k: int(k) if str(k).isdigit() else 0)

    rows: list[dict[str, Any]] = []
    for i, ok in enumerate(obs_keys):
        cell = observations[ok]
        raw_val: Any = None
        if isinstance(cell, list) and cell:
            raw_val = cell[0]
        period = periods[i] if i < len(periods) else None
        sval = str(raw_val) if raw_val is not None else ""
        num: float | None = None
        if sval:
            try:
                num = float(sval)
            except ValueError:
                num = None
        rows.append(
            {
                "time_period": period,
                "observation_index": i,
                "value": sval,
                "value_num": num,
                "unit": unit_name,
                "unit_multiplier_pow10": mult_pow10,
            }
        )
    return rows


class ADBKIDBClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        session: requests.Session | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        min_interval_seconds: float = 3.1,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", user_agent)
        self._min_interval = min_interval_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._last_request_at: float | None = None

    def _throttle(self) -> None:
        if self._min_interval <= 0 or self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self._min_interval - elapsed
        if wait > 0:
            time.sleep(wait)

    def _get(self, path: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        timeout = kwargs.pop("timeout", 120)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                r = self._session.get(url, params=params, timeout=timeout, **kwargs)
                self._last_request_at = time.monotonic()
                r.raise_for_status()
                return r
            except requests.exceptions.RequestException as exc:
                self._last_request_at = time.monotonic()
                last_exc = exc
                if attempt >= self._max_retries:
                    break
                backoff = self._retry_backoff_seconds * (2**attempt)
                time.sleep(backoff)

        if last_exc is not None:
            raise RuntimeError(f"KIDB request failed after retries: {url}") from last_exc
        raise RuntimeError(f"KIDB request failed without exception details: {url}")

    def fetch_sdmx_data(
        self,
        dataflow_id: str,
        sdmx_key: str,
        *,
        start_period: str | int | None = None,
        end_period: str | int | None = None,
        format: str = "sdmx-json",
        version: str | None = None,
        grouping: str | None = None,
    ) -> requests.Response:
        path = f"/api/v4/sdmx/data/{dataflow_id}/{sdmx_key}"
        q: dict[str, Any] = {"format": format}
        if start_period is not None:
            q["startPeriod"] = str(start_period)
        if end_period is not None:
            q["endPeriod"] = str(end_period)
        if version is not None:
            q["version"] = version
        if grouping is not None:
            q["grouping"] = grouping
        return self._get(path, params=q)

    def fetch_sdmx_data_json(self, dataflow_id: str, sdmx_key: str, **kwargs: Any) -> Any:
        return self.fetch_sdmx_data(dataflow_id, sdmx_key, **kwargs).json()

    def list_dataflow_indicators(self, dataflow_code: str) -> Any:
        return self._get(f"/api/dataflow/indicators/{dataflow_code}").json()

    def get_merchandise_exports_fob(
        self,
        economy: str = "HKG",
        *,
        start_year: int | str = 2018,
        end_year: int | str = 2022,
    ) -> dict[str, Any]:
        key = f"A.TXG_FOB_XDC.{economy}"
        return self.fetch_sdmx_data_json("ADB,GLB_ET", key, start_period=start_year, end_period=end_year)

    def get_population_midyear(
        self,
        economy: str = "HKG",
        *,
        start_year: int | str = 2018,
        end_year: int | str = 2022,
    ) -> dict[str, Any]:
        key = f"A.LP_PE_NUM_MOP.{economy}"
        return self.fetch_sdmx_data_json("ADB,PPL_POP", key, start_period=start_year, end_period=end_year)

    def get_unemployment_rate(
        self,
        economy: str = "HKG",
        *,
        start_year: int | str = 2018,
        end_year: int | str = 2024,
    ) -> dict[str, Any]:
        key = f"A.LUR_PT.{economy}"
        return self.fetch_sdmx_data_json("ADB,PPL_LE", key, start_period=start_year, end_period=end_year)

    def get_general_government_final_consumption_current_prices(
        self,
        economy: str = "HKG",
        *,
        start_year: int | str = 2018,
        end_year: int | str = 2022,
    ) -> dict[str, Any]:
        key = f"A.NCGG_XDC.{economy}"
        return self.fetch_sdmx_data_json(
            "ADB,EO_NA_CURR_GDP_EXP",
            key,
            start_period=start_year,
            end_period=end_year,
        )

    def download_file(self, url: str, dest: str | BinaryIO) -> None:
        self._throttle()
        with self._session.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            if hasattr(dest, "write"):
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        dest.write(chunk)  # type: ignore[attr-defined]
            else:
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
        self._last_request_at = time.monotonic()

