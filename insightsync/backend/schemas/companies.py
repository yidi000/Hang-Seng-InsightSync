from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from insightsync.backend.schemas.dashboard import CountItem
from insightsync.backend.schemas.signals import SignalOut
from insightsync.backend.schemas.timeline import TimelineEventOut


class CompanyProfileOut(BaseModel):
    """Company profile assembled from the latest company snapshot."""

    source: str
    company_id: str
    canonical_name: str
    display_name: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    segments: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    website_url: str | None = None
    linkedin_url: str | None = None
    facebook_url: str | None = None
    x_url: str | None = None
    instagram_url: str | None = None
    wikipedia_url: str | None = None
    profile_summary: str | None = None
    description: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class CompanyListItemOut(CompanyProfileOut):
    """Company list item with aggregated activity stats."""

    signal_count: int = 0
    timeline_event_count: int = 0
    generated_insight_count: int = 0
    last_signal_at: datetime | None = None
    last_event_at: datetime | None = None
    last_insight_at: datetime | None = None
    activity_at: datetime | None = None


class CompanyListOut(BaseModel):
    """Paginated company list response."""

    items: list[CompanyListItemOut]
    limit: int
    offset: int


class CompanyStatsOut(BaseModel):
    """Aggregated company activity counts."""

    signal_count: int = 0
    timeline_event_count: int = 0
    generated_insight_count: int = 0
    last_signal_at: datetime | None = None
    last_event_at: datetime | None = None
    last_insight_at: datetime | None = None
    signal_type_distribution: list[CountItem] = Field(default_factory=list)


class CompanyInsightPreviewOut(BaseModel):
    """Recent generated insight preview for a company."""

    id: int
    source: str
    insight_type: str
    title: str
    summary: str
    confidence: float | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    generated_at: datetime


class CompanyDetailOut(BaseModel):
    """Company-centric detail view."""

    company: CompanyProfileOut
    stats: CompanyStatsOut
    recent_signals: list[SignalOut] = Field(default_factory=list)
    recent_timeline: list[TimelineEventOut] = Field(default_factory=list)
    recent_insights: list[CompanyInsightPreviewOut] = Field(default_factory=list)
