from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.schemas.prospects import ProspectDetailOut, ProspectListOut
from insightsync.backend.services.prospect_service import ProspectService

router = APIRouter(prefix="/api/prospects", tags=["prospects"])


@router.get("", response_model=ProspectListOut)
def list_prospects(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    industry: str | None = None,
    status: str | None = None,
    priority_level: str | None = None,
    db: Session = Depends(get_db),
) -> ProspectListOut:
    """Return a business-facing prospect list derived from company state."""

    payload = ProspectService(db).list_prospects(
        limit=limit,
        offset=offset,
        q=q,
        region=region,
        segment=segment,
        industry=industry,
        status=status,
        priority_level=priority_level,
    )
    return ProspectListOut(**payload)


@router.get("/{prospect_id}", response_model=ProspectDetailOut)
def get_prospect_detail(prospect_id: str, db: Session = Depends(get_db)) -> ProspectDetailOut:
    """Return business-facing prospect detail derived from company state."""

    detail = ProspectService(db).get_prospect_detail(prospect_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return ProspectDetailOut(**detail)
