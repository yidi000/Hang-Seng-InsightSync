from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.timeline import TimelineEventOut, TimelineListOut

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("", response_model=TimelineListOut)
def list_timeline(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    company_id: str | None = None,
    entity: str | None = None,
    event_type: str | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
) -> TimelineListOut:
    """Return timeline events from PostgreSQL."""

    repo = ReadRepository(db)
    rows = repo.list_timeline(
        limit=limit,
        offset=offset,
        company_id=company_id,
        entity=entity,
        event_type=event_type,
        source=source,
        date_from=date_from,
        date_to=date_to,
    )
    items = [TimelineEventOut(**{**row, "payload": row.get("payload_json") or {}}) for row in rows]
    return TimelineListOut(items=items, limit=limit, offset=offset)
