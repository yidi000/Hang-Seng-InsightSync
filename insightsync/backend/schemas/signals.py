from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SignalOut(BaseModel):
    """API representation of a trigger signal."""

    id: int
    source: str
    dataset: str
    signal_key: str
    signal_type: str
    company_id: str | None = None
    entity: str | None = None
    event_time: datetime
    indicator: str | None = None
    value_num: float | None = None
    value_text: str | None = None
    unit: str | None = None
    signal_text: str | None = None
    signal_score: float | None = None
    signal_level: str | None = None
    evidence_refs: list[Any] = []
    extra: dict[str, Any] | None = None


class SignalListOut(BaseModel):
    """Paginated signal response."""

    items: list[SignalOut]
    limit: int
    offset: int
