from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.dashboard import DashboardOverviewOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverviewOut)
def overview(db: Session = Depends(get_db)) -> DashboardOverviewOut:
    """Return backend dashboard overview metrics."""

    return DashboardOverviewOut(**ReadRepository(db).overview())
