from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TimelineEventOut(BaseModel):
    """API representation of a timeline event."""

    id: int
    source: str
    company_id: str | None = None
    entity: str | None = None
    event_time: datetime | None = None
    event_type: str
    headline: str
    detail: str | None = None
    evidence_url: str | None = None
    payload: dict[str, Any] | None = None


class TimelineListOut(BaseModel):
    """Paginated timeline response."""

    items: list[TimelineEventOut]
    limit: int
    offset: int
