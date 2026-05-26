from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.dashboard import (
    CountItem,
    DashboardMarketOverviewOut,
    DashboardOverviewOut,
    DashboardPriorityProspectsOut,
    DashboardSummaryOut,
    DashboardTriggerSignalsOut,
)
from insightsync.backend.services.prospect_service import ProspectService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverviewOut)
def overview(db: Session = Depends(get_db)) -> DashboardOverviewOut:
    """Return backend dashboard overview metrics."""

    return DashboardOverviewOut(**ReadRepository(db).overview())


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(db: Session = Depends(get_db)) -> DashboardSummaryOut:
    """Return homepage summary cards derived from current prospect state."""

    return DashboardSummaryOut(**ProspectService(db).dashboard_rollup()["summary"])


@router.get("/priority-prospects", response_model=DashboardPriorityProspectsOut)
def priority_prospects(db: Session = Depends(get_db)) -> DashboardPriorityProspectsOut:
    """Return homepage priority prospects derived from the current prospect layer."""

    items = ProspectService(db).list_compact_prospects(limit=5, offset=0)["items"]
    compact_items = [
        {
            "prospect_id": item["prospect_id"],
            "company_id": item["company_id"],
            "display_name": item.get("display_name") or item["canonical_name"],
            "priority_level": item["priority_level"],
            "priority_score": item["priority_score"],
            "opportunity_score": item["opportunity_score"],
            "risk_score": item["risk_score"],
            "region": item.get("region"),
            "industries": item.get("industries", []),
            "focus_tags": item.get("focus_tags", []),
            "why_prioritized": item.get("why_prioritized", [])[:2],
            "recommended_next_step": item.get("recommended_next_step"),
        }
        for item in items
    ]
    return DashboardPriorityProspectsOut(items=compact_items)


@router.get("/trigger-signals", response_model=DashboardTriggerSignalsOut)
def trigger_signals(db: Session = Depends(get_db)) -> DashboardTriggerSignalsOut:
    """Return homepage trigger-signal cards with lightweight prospect linkage."""

    repo = ReadRepository(db)
    signals = repo.list_signals(limit=5, offset=0)
    focus_tags_by_company = repo.list_company_signal_types(
        [signal["company_id"] for signal in signals if signal.get("company_id")]
    )

    items = []
    for signal in signals:
        company_id = signal.get("company_id")
        prospect_id = f"prospect:{company_id}" if company_id else None

        title = signal.get("signal_text") or signal.get("value_text") or signal.get("indicator") or signal["signal_key"]
        items.append(
            {
                "signal_id": signal["id"],
                "company_id": company_id,
                "prospect_id": prospect_id,
                "signal_type": signal["signal_type"],
                "source": signal["source"],
                "title": title,
                "event_time": signal["event_time"],
                "focus_tags": focus_tags_by_company.get(company_id, [])[:3] if company_id else [],
            }
        )

    return DashboardTriggerSignalsOut(items=items)


@router.get("/market-overview", response_model=DashboardMarketOverviewOut)
def market_overview(db: Session = Depends(get_db)) -> DashboardMarketOverviewOut:
    """Return homepage market-overview blocks derived from current prospect state."""

    rollup = ProspectService(db).dashboard_rollup()
    industry_breakdown = [CountItem(**item) for item in rollup["industry_breakdown"]]
    region_breakdown = [CountItem(**item) for item in rollup["region_breakdown"]]

    return DashboardMarketOverviewOut(
        industry_breakdown=industry_breakdown,
        region_breakdown=region_breakdown,
        company_size_breakdown=[],
    )
