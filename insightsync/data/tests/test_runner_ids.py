from __future__ import annotations

from datetime import datetime, timezone

from insightsync.data.pipeline import runner


def test_run_id_format_includes_microseconds(monkeypatch) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 5, 11, 12, 34, 56, 789123, tzinfo=tz or timezone.utc)

    monkeypatch.setattr(runner, "datetime", FixedDatetime)

    run_id = runner._new_run_id()

    assert run_id == "run-20260511T123456789123Z"
