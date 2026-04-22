from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.companies import CompanyDetailOut, CompanyListItemOut, CompanyListOut

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=CompanyListOut)
def list_companies(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    industry: str | None = None,
    db: Session = Depends(get_db),
) -> CompanyListOut:
    """Return a paginated company-centric view."""

    repo = ReadRepository(db)
    rows = repo.list_companies(
        limit=limit,
        offset=offset,
        q=q,
        region=region,
        segment=segment,
        industry=industry,
    )
    return CompanyListOut(items=[CompanyListItemOut(**row) for row in rows], limit=limit, offset=offset)


@router.get("/{company_id}", response_model=CompanyDetailOut)
def get_company_detail(company_id: str, db: Session = Depends(get_db)) -> CompanyDetailOut:
    """Return company profile, stats, and recent evidence."""

    detail = ReadRepository(db).get_company_detail(company_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyDetailOut(**detail)
