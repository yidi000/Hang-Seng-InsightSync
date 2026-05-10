from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.dashboard import (
    DashboardOverviewOut,
    DashboardPriorityProspectOut,
    DashboardPriorityProspectsOut,
    DashboardSummaryOut,
    DashboardTriggerSignalOut,
    DashboardTriggerSignalsOut,
    MarketOverviewOut,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _string_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _product_fit(row: dict) -> list[str]:
    return _string_ids(row.get("recommended_products"))


def _signal_subtype(reason: dict) -> str | None:
    subtype = reason.get("signal_subtype", reason.get("signalSubtype"))
    if not isinstance(subtype, str):
        return None
    return subtype


def _score_reason_items(row: dict) -> list[dict]:
    score_reasons = row.get("score_reasons") or []
    if not isinstance(score_reasons, list):
        return []
    items: list[dict] = []
    for reason in score_reasons:
        if not isinstance(reason, dict):
            continue
        items.append(
            {
                "reason": str(reason.get("reason") or ""),
                "signalSubtype": _signal_subtype(reason),
                "evidenceIds": _string_ids(reason.get("evidence_ids")),
            }
        )
    return items


def _evidence_ids(row: dict) -> list[str]:
    score_inputs = row.get("score_inputs") or {}
    if not isinstance(score_inputs, dict):
        return []
    evidence_refs = score_inputs.get("evidence_refs") or []
    if not isinstance(evidence_refs, list):
        return []
    ids: list[str] = []
    for ref in evidence_refs:
        if isinstance(ref, dict):
            evidence_id = ref.get("evidence_id")
        else:
            evidence_id = ref
        if isinstance(evidence_id, str):
            ids.append(evidence_id)
    return ids


@router.get("/overview", response_model=DashboardOverviewOut)
def overview(db: Session = Depends(get_db)) -> DashboardOverviewOut:
    """Return backend dashboard overview metrics."""

    return DashboardOverviewOut(**ReadRepository(db).overview())


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(db: Session = Depends(get_db)) -> DashboardSummaryOut:
    """Return frontend-ready dashboard summary cards."""

    return DashboardSummaryOut(**ReadRepository(db).dashboard_summary())


@router.get("/market-overview", response_model=MarketOverviewOut)
def market_overview(db: Session = Depends(get_db)) -> MarketOverviewOut:
    """Return market opportunity chart breakdowns."""

    repo = ReadRepository(db)
    return MarketOverviewOut(
        industryBreakdown=repo.chart_breakdown("industry"),
        regionBreakdown=repo.chart_breakdown("region"),
        companySizeBreakdown=repo.chart_breakdown("size_band"),
        signalBreakdown=repo.signal_breakdown(),
    )


@router.get("/priority-prospects", response_model=DashboardPriorityProspectsOut)
def priority_prospects(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> DashboardPriorityProspectsOut:
    """Return ranked prospects for the dashboard."""

    rows = ReadRepository(db).priority_prospects(limit=limit)
    return DashboardPriorityProspectsOut(
        items=[
            DashboardPriorityProspectOut(
                prospectId=row["prospect_id"],
                displayName=row["display_name"],
                score=row["score"],
                tier=row["tier"],
                industry=row.get("industry"),
                region=row.get("region"),
                productFit=_product_fit(row),
                recommendedEntryAngle=row.get("recommended_entry_angle"),
                scoreReasons=_score_reason_items(row),
                evidenceIds=_evidence_ids(row),
            )
            for row in rows
        ]
    )


@router.get("/trigger-signals", response_model=DashboardTriggerSignalsOut)
def trigger_signals(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> DashboardTriggerSignalsOut:
    """Return compact trigger signal cards for the dashboard."""

    rows = ReadRepository(db).dashboard_trigger_signals(limit=limit)
    return DashboardTriggerSignalsOut(
        items=[
            DashboardTriggerSignalOut(
                signalId=row["signal_id"],
                prospectId=row.get("prospect_id"),
                signalType=row["signal_type"],
                signalSubtype=row["signal_subtype"],
                signalText=row["signal_text"],
                eventTime=row.get("event_time"),
                source=row.get("source"),
            )
            for row in rows
        ]
    )
