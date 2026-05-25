from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.signals import SignalListOut, SignalOut

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=SignalListOut)
def list_signals(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    company_id: str | None = None,
    entity: str | None = None,
    signal_type: str | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
) -> SignalListOut:
    """Return trigger signals from PostgreSQL."""

    repo = ReadRepository(db)
    rows = repo.list_signals(
        limit=limit,
        offset=offset,
        company_id=company_id,
        entity=entity,
        signal_type=signal_type,
        source=source,
        date_from=date_from,
        date_to=date_to,
    )
    items = [
        SignalOut(
            **{
                **row,
                "evidence_refs": row.get("evidence_refs") or [],
                "extra": row.get("extra") or {},
            }
        )
        for row in rows
    ]
    return SignalListOut(items=items, limit=limit, offset=offset)


@router.get("/{signal_id}", response_model=SignalOut)
def get_signal(signal_id: int, db: Session = Depends(get_db)) -> SignalOut:
    """Return one trigger signal by id."""

    row = ReadRepository(db).get_signal(signal_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")
    return SignalOut(
        **{
            **row,
            "evidence_refs": row.get("evidence_refs") or [],
            "extra": row.get("extra") or {},
        }
    )
