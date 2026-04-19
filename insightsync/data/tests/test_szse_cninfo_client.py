from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from insightsync.data.connectors.szse_cninfo_client import (
    SZSECninfoClient,
    build_cninfo_pdf_url,
    timestamp_ms_to_date,
    timestamp_ms_to_datetime,
)


class _DummyResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _DummySession:
    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = payloads
        self._idx = 0
        self.headers: dict[str, str] = {}

    def post(self, *_args, **_kwargs) -> _DummyResponse:
        payload = self._payloads[self._idx]
        self._idx += 1
        return _DummyResponse(payload)


class SZSECninfoClientTests(unittest.TestCase):
    def test_timestamp_helpers_convert_millis(self) -> None:
        dt = datetime(2026, 4, 20, 9, 30, 0, tzinfo=timezone(timedelta(hours=8)))
        ts_ms = int(dt.timestamp() * 1000)

        self.assertEqual(timestamp_ms_to_date(ts_ms), "2026-04-20")
        self.assertEqual(timestamp_ms_to_datetime(ts_ms), "2026-04-20 09:30:00")

    def test_build_cninfo_pdf_url_supports_relative_and_absolute(self) -> None:
        self.assertEqual(
            build_cninfo_pdf_url("finalpage/2026-04-20/123456.PDF"),
            "http://static.cninfo.com.cn/finalpage/2026-04-20/123456.PDF",
        )
        self.assertEqual(
            build_cninfo_pdf_url("http://static.cninfo.com.cn/finalpage/2026-04-20/abc.PDF"),
            "http://static.cninfo.com.cn/finalpage/2026-04-20/abc.PDF",
        )

    def test_fetch_announcements_handles_pagination(self) -> None:
        payloads = [
            {
                "announcements": [{"announcementId": "a1"}, {"announcementId": "a2"}],
                "hasMore": True,
                "totalpages": 2,
                "totalRecordNum": 3,
            },
            {
                "announcements": [{"announcementId": "a3"}],
                "hasMore": False,
                "totalpages": 2,
                "totalRecordNum": 3,
            },
        ]
        client = SZSECninfoClient(session=_DummySession(payloads))

        out = client.fetch_announcements(
            start_date="2026-01-01",
            end_date="2026-04-20",
            delay_seconds=0.0,
            page_size=30,
            max_records=500,
        )

        self.assertEqual(len(out["items"]), 3)
        self.assertEqual(out["meta"]["pages_fetched"], 2)
        self.assertEqual(out["meta"]["total_pages"], 2)


if __name__ == "__main__":
    unittest.main()
