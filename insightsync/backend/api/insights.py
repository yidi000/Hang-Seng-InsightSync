from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from insightsync.backend.core.config import get_settings
from insightsync.backend.db.session import get_db
from insightsync.backend.schemas.rag import CitationOut, GenerateInsightIn, GeneratedInsightOut
from insightsync.backend.services.insight_generator import InsightGenerator

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.post("/generate", response_model=GeneratedInsightOut)
def generate_insight(payload: GenerateInsightIn, db: Session = Depends(get_db)) -> GeneratedInsightOut:
    """Generate and persist an evidence-grounded insight."""

    settings = get_settings()
    generator = InsightGenerator(db, settings)
    filters = payload.filters.model_dump(exclude_none=True)
    result = generator.answer_question(
        question=payload.question,
        filters=filters,
        insight_type=payload.insight_type,
    )
    generator.persist_generated_insight(result, entity=filters.get("entity"), company_id=filters.get("company_id"))
    db.commit()
    return GeneratedInsightOut(
        status=result["status"],
        insight=result.get("structured_insight"),
        citations=[CitationOut(**item) for item in result.get("citations", [])],
    )
