from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProspectScoreOut(BaseModel):
    score: float
    tier: str
    reasons: list[dict[str, Any]] = Field(default_factory=list)
    recommended_products: list[str] = Field(default_factory=list)
    recommended_entry_angle: str | None = None
    updated_at: datetime | None = None


class ProspectListItemOut(BaseModel):
    prospect_id: str
    company_id: str | None = None
    display_name: str
    canonical_name: str | None = None
    region: str | None = None
    industry: str | None = None
    size_band: str = "unknown"
    segments: list[str] = Field(default_factory=list)
    last_activity_at: datetime | None = None
    score: float | None = None
    tier: str | None = None
    recommended_products: list[str] = Field(default_factory=list)
    recommended_entry_angle: str | None = None


class ProspectListOut(BaseModel):
    items: list[ProspectListItemOut]
    total: int
    page: int
    pageSize: int


class ProspectEvidenceOut(BaseModel):
    evidence_id: str
    prospect_id: str | None = None
    evidence_type: str
    event_time: datetime | None = None
    title: str
    summary: str | None = None
    url: str | None = None
    source: str
    dataset: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProspectSignalOut(BaseModel):
    signal_id: str
    prospect_id: str | None = None
    signal_type: str
    signal_subtype: str
    signal_level: str | None = None
    signal_score: float | None = None
    event_time: datetime | None = None
    signal_text: str
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProspectTimelineOut(BaseModel):
    id: int
    event_time: datetime | None = None
    event_type: str
    title: str
    summary: str | None = None
    source: str
    url: str | None = None


class ProspectInsightOut(BaseModel):
    id: int
    insight_type: str
    title: str
    summary: str
    confidence: float | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    generated_at: datetime


class ProspectDetailOut(ProspectListItemOut):
    score_detail: ProspectScoreOut | None = None
    stats: dict[str, Any] = Field(default_factory=dict)
    latest_evidence: list[ProspectEvidenceOut] = Field(default_factory=list)
    latest_signals: list[ProspectSignalOut] = Field(default_factory=list)
