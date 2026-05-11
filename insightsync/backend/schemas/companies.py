from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class CompanyEvidenceSummaryOut(BaseModel):
    """Coverage summary for parsed company evidence."""

    parsed_document_count: int = 0
    parsed_document_success_count: int = 0
    parsed_document_partial_count: int = 0
    parsed_document_failed_count: int = 0
    ocr_hit_count: int = 0
    xbrl_hit_count: int = 0
    management_discussion_count: int = 0
    metric_count: int = 0
    risk_factor_count: int = 0
    business_event_count: int = 0
    last_parsed_at: datetime | None = None


class CompanyStateSignalOut(BaseModel):
    """Explainable company-state item derived from signals or parsed evidence."""

    title: str
    detail: str | None = None
    source_type: str
    source: str | None = None
    signal_type: str | None = None
    severity: str | None = None
    confidence: float | None = None
    linkage_type: str | None = None
    linkage_label: str | None = None
    linkage_strength: str | None = None
    linkage_rationale: str | None = None
    supports_company_scoring: bool | None = None
    context_only: bool | None = None


class CompanyProductFitOut(BaseModel):
    """Recommended product fit derived from fused company and market evidence."""

    product_name: str
    fit_score: int
    rationale: str
    supporting_signals: list[str] = Field(default_factory=list)


class CompanyDecisionFeatureOut(BaseModel):
    """Documented feature item used in company- and prospect-level reasoning."""

    feature_key: str
    feature_label: str | None = None
    feature_group: str
    feature_description: str | None = None
    business_question: str | None = None
    preferred_linkage_types: list[str] = Field(default_factory=list)
    max_score_contribution: int | None = None
    value_num: float | None = None
    score_contribution: int
    rationale: str
    evidence_items: list[str] = Field(default_factory=list)


class CompanyFusionReasoningStepOut(BaseModel):
    """Structured reasoning step produced by the fusion layer."""

    step_key: str
    title: str
    summary: str
    feature_keys: list[str] = Field(default_factory=list)
    linkage_types: list[str] = Field(default_factory=list)
    evidence_items: list[str] = Field(default_factory=list)


class CompanyOpportunityLensOut(BaseModel):
    """Business lens derived from structured fusion."""

    lens_key: str
    label: str
    lens_score: int
    rationale: str
    supporting_evidence: list[str] = Field(default_factory=list)
    recommended_products: list[str] = Field(default_factory=list)


class CompanyDecisionAnswerOut(BaseModel):
    """Plain-language answer to a core business question."""

    question_key: str
    question: str
    answer: str
    supporting_evidence: list[str] = Field(default_factory=list)


class CompanyFusionOutputOut(BaseModel):
    """Structured fusion output assembled from evidence, linkage, features, and scores."""

    summary: str | None = None
    why_now: str | None = None
    primary_lens_key: str | None = None
    primary_opportunity: str | None = None
    context_alignment: str | None = None
    key_risk: str | None = None
    reasoning_steps: list[CompanyFusionReasoningStepOut] = Field(default_factory=list)
    opportunity_lenses: list[CompanyOpportunityLensOut] = Field(default_factory=list)
    decision_answers: list[CompanyDecisionAnswerOut] = Field(default_factory=list)


class CompanyCoverageFlagsOut(BaseModel):
    """Boolean coverage flags for company evidence completeness."""

    has_recent_signals: bool = False
    has_recent_timeline: bool = False
    has_generated_insights: bool = False
    has_parsed_reports: bool = False
    has_management_discussion: bool = False
    has_structured_metrics: bool = False
    has_risk_factors: bool = False
    has_business_events: bool = False
    has_ocr_support: bool = False
    has_xbrl_support: bool = False


class GenAIExtractionFactOut(BaseModel):
    """Normalized GenAI extraction fact with evidence and scoring gate metadata."""

    model_config = ConfigDict(extra="allow")

    fact_type: str
    extraction_confidence: float | None = None
    evidence_span: dict[str, Any] = Field(default_factory=dict)
    scoring_eligibility: dict[str, Any] = Field(default_factory=dict)


class GenAIRejectedFactOut(BaseModel):
    """Rejected GenAI extraction fact with validation reasons."""

    model_config = ConfigDict(extra="allow")

    fact_type: str | None = None
    reasons: list[str] = Field(default_factory=list)
    normalized: dict[str, Any] | None = None


class GenAIExtractionOut(BaseModel):
    """Auditable GenAI extraction metadata attached to a parsed document."""

    status: str | None = None
    prompt_version: str | None = None
    candidate_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    scoring_eligible_counts: dict[str, int] = Field(default_factory=dict)
    context_only_count: int = 0
    rejected_reason_counts: dict[str, int] = Field(default_factory=dict)
    accepted_facts: list[GenAIExtractionFactOut] = Field(default_factory=list)
    rejected_facts: list[GenAIRejectedFactOut] = Field(default_factory=list)


class ParsedDocumentPreviewOut(BaseModel):
    """Recent parsed document preview for company detail."""

    id: int
    source: str
    dataset: str | None = None
    title: str | None = None
    summary: str | None = None
    media_type: str | None = None
    lang: str | None = None
    parser_name: str
    backend_name: str | None = None
    parse_status: str
    ocr_status: str | None = None
    xbrl_status: str | None = None
    management_discussion_summary: str | None = None
    section_count: int = 0
    table_count: int = 0
    metric_count: int = 0
    risk_factor_count: int = 0
    business_event_count: int = 0
    evidence_url: str | None = None
    genai_extraction: GenAIExtractionOut | None = None
    parsed_at: datetime


class CompanyMetricOut(BaseModel):
    """Structured metric extracted from a parsed company document."""

    document_id: int
    title: str | None = None
    name: str
    value: str
    unit: str | None = None
    period: str | None = None
    context: str | None = None
    confidence: float | None = None
    parsed_at: datetime


class CompanyRiskFactorOut(BaseModel):
    """Structured risk factor extracted from a parsed company document."""

    document_id: int
    title: str | None = None
    category: str
    description: str
    severity: str
    confidence: float | None = None
    parsed_at: datetime


class CompanyBusinessEventOut(BaseModel):
    """Structured business event extracted from a parsed company document."""

    document_id: int
    title: str | None = None
    event_type: str
    summary: str
    event_date: str | None = None
    parties: list[Any] = Field(default_factory=list)
    confidence: float | None = None
    parsed_at: datetime


class CompanyLatestStateOut(BaseModel):
    """Latest explainable company state assembled from linked evidence."""

    activity_at: datetime | None = None
    status: str
    state_summary: str | None = None
    why_now: str | None = None
    fusion_summary: str | None = None
    fusion: CompanyFusionOutputOut | None = None
    recommended_next_step: str | None = None
    commercial_attractiveness_score: int = 0
    immediacy_score: int = 0
    product_fit_score: int = 0
    risk_penalty_score: int = 0
    evidence_confidence_score: int = 0
    focus_tags: list[str] = Field(default_factory=list)
    signal_highlights: list[str] = Field(default_factory=list)
    opportunity_signals: list[CompanyStateSignalOut] = Field(default_factory=list)
    risk_signals: list[CompanyStateSignalOut] = Field(default_factory=list)
    context_signals: list[CompanyStateSignalOut] = Field(default_factory=list)
    product_fit: list[CompanyProductFitOut] = Field(default_factory=list)
    recommended_entry_angles: list[str] = Field(default_factory=list)
    decision_features: list[CompanyDecisionFeatureOut] = Field(default_factory=list)
    decision_answers: list[CompanyDecisionAnswerOut] = Field(default_factory=list)
    coverage_flags: CompanyCoverageFlagsOut
    evidence_summary: CompanyEvidenceSummaryOut


class CompanyDetailOut(BaseModel):
    """Company-centric detail view."""

    company: CompanyProfileOut
    stats: CompanyStatsOut
    latest_state: CompanyLatestStateOut
    recent_signals: list[SignalOut] = Field(default_factory=list)
    recent_timeline: list[TimelineEventOut] = Field(default_factory=list)
    recent_insights: list[CompanyInsightPreviewOut] = Field(default_factory=list)
    recent_documents: list[ParsedDocumentPreviewOut] = Field(default_factory=list)
    key_metrics: list[CompanyMetricOut] = Field(default_factory=list)
    key_risk_factors: list[CompanyRiskFactorOut] = Field(default_factory=list)
    key_business_events: list[CompanyBusinessEventOut] = Field(default_factory=list)
