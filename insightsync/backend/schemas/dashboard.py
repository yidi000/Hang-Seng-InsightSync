from __future__ import annotations

from pydantic import BaseModel


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
