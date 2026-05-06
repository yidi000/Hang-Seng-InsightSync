from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from insightsync.backend.schemas.companies import (
    CompanyBusinessEventOut,
    CompanyCoverageFlagsOut,
    CompanyEvidenceSummaryOut,
    CompanyInsightPreviewOut,
    CompanyLatestStateOut,
    CompanyMetricOut,
    CompanyProfileOut,
    CompanyRiskFactorOut,
    ParsedDocumentPreviewOut,
)
from insightsync.backend.schemas.signals import SignalOut
from insightsync.backend.schemas.timeline import TimelineEventOut


class ProspectSummaryOut(BaseModel):
    """Business-facing prospect summary derived from company state."""

    prospect_id: str
    company_id: str
    canonical_name: str
    display_name: str | None = None
    region: str | None = None
    city: str | None = None
    industries: list[str] = Field(default_factory=list)
    segments: list[str] = Field(default_factory=list)
    activity_at: datetime | None = None
    status: str
    priority_level: str
    priority_score: int
    opportunity_score: int
    risk_score: int
    focus_tags: list[str] = Field(default_factory=list)
    why_prioritized: list[str] = Field(default_factory=list)
    recommended_next_step: str | None = None
    recommended_product_themes: list[str] = Field(default_factory=list)
    score_breakdown: "ProspectScoreBreakdownOut"


class ProspectListOut(BaseModel):
    """Paginated prospect list response."""

    items: list[ProspectSummaryOut]
    total: int
    limit: int
    offset: int


class ProspectDetailOut(BaseModel):
    """Prospect detail assembled from company state and linked evidence."""

    prospect: ProspectSummaryOut
    company: CompanyProfileOut
    latest_state: CompanyLatestStateOut
    recent_signals: list[SignalOut] = Field(default_factory=list)
    recent_timeline: list[TimelineEventOut] = Field(default_factory=list)
    recent_insights: list[CompanyInsightPreviewOut] = Field(default_factory=list)
    recent_documents: list[ParsedDocumentPreviewOut] = Field(default_factory=list)
    key_metrics: list[CompanyMetricOut] = Field(default_factory=list)
    key_risk_factors: list[CompanyRiskFactorOut] = Field(default_factory=list)
    key_business_events: list[CompanyBusinessEventOut] = Field(default_factory=list)


class ProspectEvidenceOut(BaseModel):
    """Evidence bundle linked to a business-facing prospect."""

    prospect_id: str
    company_id: str
    coverage_flags: CompanyCoverageFlagsOut
    evidence_summary: CompanyEvidenceSummaryOut
    recent_documents: list[ParsedDocumentPreviewOut] = Field(default_factory=list)
    key_metrics: list[CompanyMetricOut] = Field(default_factory=list)
    key_risk_factors: list[CompanyRiskFactorOut] = Field(default_factory=list)
    key_business_events: list[CompanyBusinessEventOut] = Field(default_factory=list)


class ProspectScoreComponentOut(BaseModel):
    """Single scoring component used to explain a prospect score."""

    name: str
    category: str
    points: int
    detail: str


class ProspectScoreBreakdownOut(BaseModel):
    """Explainable score composition for prospect prioritization."""

    opportunity_components: list[ProspectScoreComponentOut] = Field(default_factory=list)
    risk_components: list[ProspectScoreComponentOut] = Field(default_factory=list)
    priority_components: list[ProspectScoreComponentOut] = Field(default_factory=list)
