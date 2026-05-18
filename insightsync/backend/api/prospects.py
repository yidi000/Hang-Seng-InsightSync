from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from insightsync.backend.core.config import get_settings
from insightsync.backend.db.session import get_db
from insightsync.backend.schemas.prospects import (
    ProspectBriefOut,
    ProspectCopilotOut,
    ProspectDetailOut,
    ProspectEvidenceOut,
    ProspectInsightListOut,
    ProspectListOut,
    ProspectQuestionIn,
    ProspectQuestionOut,
    ProspectReviewOut,
    ProspectWorkflowStateOut,
    ProspectWorkflowUpdateIn,
)
from insightsync.backend.schemas.signals import SignalListOut
from insightsync.backend.schemas.timeline import TimelineListOut
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
    view: Literal["full", "compact"] = Query(default="full"),
    db: Session = Depends(get_db),
) -> ProspectListOut:
    """Return a business-facing prospect list derived from company state."""

    service = ProspectService(db)
    list_method = service.list_compact_prospects if view == "compact" else service.list_prospects
    payload = list_method(
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


@router.get("/{prospect_id}/signals", response_model=SignalListOut)
def list_prospect_signals(
    prospect_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SignalListOut:
    """Return recent signals linked to a business-facing prospect."""

    payload = ProspectService(db).list_prospect_signals(prospect_id, limit=limit, offset=offset)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return SignalListOut(**payload)


@router.get("/{prospect_id}/timeline", response_model=TimelineListOut)
def list_prospect_timeline(
    prospect_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> TimelineListOut:
    """Return recent timeline events linked to a business-facing prospect."""

    payload = ProspectService(db).list_prospect_timeline(prospect_id, limit=limit, offset=offset)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return TimelineListOut(**payload)


@router.get("/{prospect_id}/insights", response_model=ProspectInsightListOut)
def list_prospect_insights(
    prospect_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    insight_type: str | None = None,
    db: Session = Depends(get_db),
) -> ProspectInsightListOut:
    """Return generated insight history linked to a business-facing prospect."""

    payload = ProspectService(db).list_prospect_insights(
        prospect_id,
        limit=limit,
        offset=offset,
        insight_type=insight_type,
    )
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return ProspectInsightListOut(**payload)


@router.get("/{prospect_id}/workflow", response_model=ProspectWorkflowStateOut)
def get_prospect_workflow(prospect_id: str, db: Session = Depends(get_db)) -> ProspectWorkflowStateOut:
    """Return persisted banker workflow state for a prospect."""

    payload = ProspectService(db).get_prospect_workflow(prospect_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return ProspectWorkflowStateOut(**payload)


@router.put("/{prospect_id}/workflow", response_model=ProspectWorkflowStateOut)
def update_prospect_workflow(
    prospect_id: str,
    payload: ProspectWorkflowUpdateIn,
    db: Session = Depends(get_db),
) -> ProspectWorkflowStateOut:
    """Update persisted banker workflow state for a prospect."""

    result = ProspectService(db).update_prospect_workflow(
        prospect_id,
        payload.model_dump(),
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    db.commit()
    return ProspectWorkflowStateOut(**result)


@router.get("/{prospect_id}/evidence", response_model=ProspectEvidenceOut)
def get_prospect_evidence(prospect_id: str, db: Session = Depends(get_db)) -> ProspectEvidenceOut:
    """Return parsed-document evidence linked to a business-facing prospect."""

    payload = ProspectService(db).get_prospect_evidence(prospect_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return ProspectEvidenceOut(**payload)


@router.get("/{prospect_id}/brief", response_model=ProspectBriefOut)
def get_prospect_brief(prospect_id: str, db: Session = Depends(get_db)) -> ProspectBriefOut:
    """Return a banker-facing brief for a prospect."""

    payload = ProspectService(db, settings=get_settings()).get_prospect_brief(prospect_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return ProspectBriefOut(**payload)


@router.post("/{prospect_id}/question", response_model=ProspectQuestionOut)
def ask_prospect_question(
    prospect_id: str,
    payload: ProspectQuestionIn,
    db: Session = Depends(get_db),
) -> ProspectQuestionOut:
    """Answer a prospect-scoped question using evidence-grounded retrieval."""

    settings = get_settings()
    result = ProspectService(db, settings=settings).answer_prospect_question(
        prospect_id,
        question=payload.question,
        top_k=payload.top_k,
        insight_type=payload.insight_type,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    db.commit()
    citations = [
        {**item, "text": item.get("text") if payload.include_chunks else None}
        for item in result.get("citations", [])
    ]
    return ProspectQuestionOut(**{**result, "citations": citations})


@router.get("/{prospect_id}/copilot", response_model=ProspectCopilotOut)
def get_prospect_copilot(prospect_id: str, db: Session = Depends(get_db)) -> ProspectCopilotOut:
    """Return a prospect-centered copilot workspace payload."""

    payload = ProspectService(db, settings=get_settings()).get_prospect_copilot(prospect_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return ProspectCopilotOut(**payload)


@router.get("/{prospect_id}/review", response_model=ProspectReviewOut)
def get_prospect_review(prospect_id: str, db: Session = Depends(get_db)) -> ProspectReviewOut:
    """Return an LLM-assisted review of linkage quality, decision subjectivity, and extraction gaps."""

    payload = ProspectService(db, settings=get_settings()).get_prospect_review(prospect_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return ProspectReviewOut(**payload)
