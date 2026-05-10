from __future__ import annotations

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
    leadPool: int
    highPriority: int
    crossBorder: int
    financingSignals: int
    lastUpdated: str | None = None


class ScoreReasonItem(BaseModel):
    reason: str
    signalSubtype: str | None = None
    evidenceIds: list[str] = Field(default_factory=list)


class ChartDrilldown(BaseModel):
    prospectIds: list[str] = Field(default_factory=list)
    evidenceIds: list[str] = Field(default_factory=list)


class ChartItem(BaseModel):
    key: str
    label: str
    value: float | int
    drilldown: ChartDrilldown | None = None


class MarketOverviewOut(BaseModel):
    industryBreakdown: list[ChartItem]
    regionBreakdown: list[ChartItem]
    companySizeBreakdown: list[ChartItem]
    signalBreakdown: list[ChartItem]


class DashboardPriorityProspectOut(BaseModel):
    prospectId: str
    displayName: str
    score: float
    tier: str
    industry: str | None = None
    region: str | None = None
    productFit: list[str]
    recommendedEntryAngle: str | None = None
    scoreReasons: list[ScoreReasonItem] = Field(default_factory=list)
    evidenceIds: list[str] = Field(default_factory=list)


class DashboardPriorityProspectsOut(BaseModel):
    items: list[DashboardPriorityProspectOut]


class DashboardTriggerSignalOut(BaseModel):
    signalId: str
    prospectId: str | None = None
    signalType: str
    signalSubtype: str
    signalText: str
    eventTime: str | None = None
    source: str | None = None


class DashboardTriggerSignalsOut(BaseModel):
    items: list[DashboardTriggerSignalOut]
