from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.schemas.metadata import MetadataFiltersOut

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


def _values(db: Session, sql: str) -> list[str]:
    return [str(row[0]) for row in db.execute(text(sql)).all() if row[0]]


@router.get("/filters", response_model=MetadataFiltersOut)
def filters(db: Session = Depends(get_db)) -> MetadataFiltersOut:
    """Return frontend filter metadata."""

    return MetadataFiltersOut(
        regions=_values(db, "SELECT DISTINCT region FROM prospects WHERE region IS NOT NULL ORDER BY region"),
        industries=_values(db, "SELECT DISTINCT industry FROM prospects WHERE industry IS NOT NULL ORDER BY industry"),
        sizeBands=_values(db, "SELECT DISTINCT size_band FROM prospects ORDER BY size_band"),
        signalTypes=_values(db, "SELECT DISTINCT signal_subtype FROM prospect_signals ORDER BY signal_subtype"),
        sources=_values(db, "SELECT DISTINCT source FROM prospect_evidence_items ORDER BY source"),
    )
