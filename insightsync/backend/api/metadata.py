from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.metadata import MetadataFiltersOut

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.get("/filters", response_model=MetadataFiltersOut)
def get_metadata_filters(db: Session = Depends(get_db)) -> MetadataFiltersOut:
    """Return current filter options derived from the available backend data."""

    return MetadataFiltersOut(**ReadRepository(db).metadata_filters())
