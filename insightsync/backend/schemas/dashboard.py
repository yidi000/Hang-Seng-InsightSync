from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CountItem(BaseModel):
    """Named count item."""

    name: str
    count: int


class DashboardOverviewOut(BaseModel):
    """Dashboard overview response."""

    ingestion_runs: int
    intelligence_records: int
    trigger_signals: int
    timeline_events: int
    generated_insights: int
    latest_run_status: str | None = None
    latest_run_id: str | None = None
    signal_type_distribution: list[CountItem]
    source_distribution: list[CountItem]


class DashboardSummaryOut(BaseModel):
    """Homepage summary cards derived from current prospect state."""

    lead_pool: int
    high_priority: int
    cross_border: int
    financing_signals: int
    last_updated: datetime | None = None


class DashboardPriorityProspectItemOut(BaseModel):
    """Compact homepage prospect card."""

    prospect_id: str
    company_id: str
    display_name: str
    priority_level: str
    priority_score: int
    opportunity_score: int
    risk_score: int
    region: str | None = None
    industries: list[str] = Field(default_factory=list)
    focus_tags: list[str] = Field(default_factory=list)
    why_prioritized: list[str] = Field(default_factory=list)
    recommended_next_step: str | None = None


class DashboardPriorityProspectsOut(BaseModel):
    """Homepage priority prospects block."""

    items: list[DashboardPriorityProspectItemOut]


class DashboardTriggerSignalItemOut(BaseModel):
    """Compact homepage trigger-signal card."""

    signal_id: int
    company_id: str | None = None
    prospect_id: str | None = None
    signal_type: str
    source: str
    title: str
    event_time: datetime
    focus_tags: list[str] = Field(default_factory=list)


class DashboardTriggerSignalsOut(BaseModel):
    """Homepage trigger signals block."""

    items: list[DashboardTriggerSignalItemOut]


class DashboardMarketOverviewOut(BaseModel):
    """Homepage market-overview block derived from current prospect state."""

    industry_breakdown: list[CountItem]
    region_breakdown: list[CountItem]
    company_size_breakdown: list[CountItem]
