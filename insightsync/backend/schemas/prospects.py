from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from insightsync.backend.schemas.companies import (
    CompanyBusinessEventOut,
    CompanyCoverageFlagsOut,
    CompanyDecisionFeatureOut,
    CompanyDecisionAnswerOut,
    CompanyEvidenceSummaryOut,
    CompanyFusionOutputOut,
    CompanyInsightPreviewOut,
    CompanyLatestStateOut,
    CompanyMetricOut,
    CompanyProductFitOut,
    CompanyProfileOut,
    CompanyRiskFactorOut,
    ParsedDocumentPreviewOut,
)
from insightsync.backend.schemas.rag import CitationOut
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
    evidence_confidence_score: int = 0
    commercial_attractiveness_score: int = 0
    immediacy_score: int = 0
    product_fit_score: int = 0
    risk_penalty_score: int = 0
    focus_tags: list[str] = Field(default_factory=list)
    why_prioritized: list[str] = Field(default_factory=list)
    recommended_next_step: str | None = None
    recommended_product_themes: list[str] = Field(default_factory=list)
    product_fit: list[CompanyProductFitOut] = Field(default_factory=list)
    recommended_entry_angles: list[str] = Field(default_factory=list)
    decision_features: list[CompanyDecisionFeatureOut] = Field(default_factory=list)
    decision_answers: list[CompanyDecisionAnswerOut] = Field(default_factory=list)
    fusion: CompanyFusionOutputOut | None = None
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


class ProspectInsightListOut(BaseModel):
    """Generated insight history for a prospect."""

    items: list[CompanyInsightPreviewOut] = Field(default_factory=list)
    limit: int
    offset: int


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


class ProspectLinkageQualityOut(BaseModel):
    """Evidence-linkage quality metrics used to guard prospect scoring."""

    linked_evidence_count: int = 0
    scoreable_evidence_count: int = 0
    direct_evidence_count: int = 0
    strong_linkage_count: int = 0
    context_only_count: int = 0
    direct_evidence_ratio: float = 0.0
    scoreable_evidence_ratio: float = 0.0
    linkage_type_counts: dict[str, int] = Field(default_factory=dict)


class ProspectGovernanceFlagOut(BaseModel):
    """Score governance flag for subjectivity, weak evidence, or linkage overreach."""

    flag_key: str
    severity: str
    area: str
    message: str
    suggested_action: str


class ProspectScoreBreakdownOut(BaseModel):
    """Explainable score composition for prospect prioritization."""

    scorecard_version: str
    scoring_method: str
    calibration_status: str
    llm_score_assignment: str
    priority_formula: str
    score_interpretation: dict[str, str] = Field(default_factory=dict)
    priority_policy: dict[str, float | int] = Field(default_factory=dict)
    score_inputs: dict[str, int] = Field(default_factory=dict)
    opportunity_components: list[ProspectScoreComponentOut] = Field(default_factory=list)
    risk_components: list[ProspectScoreComponentOut] = Field(default_factory=list)
    priority_components: list[ProspectScoreComponentOut] = Field(default_factory=list)
    linkage_quality: ProspectLinkageQualityOut
    governance_flags: list[ProspectGovernanceFlagOut] = Field(default_factory=list)


class ProspectBriefOut(BaseModel):
    """Banker-facing brief derived from prospect state and linked evidence."""

    prospect_id: str
    company_id: str
    title: str
    summary: str
    priority_level: str
    recommended_next_step: str | None = None
    recommended_product_themes: list[str] = Field(default_factory=list)
    recommended_entry_angles: list[str] = Field(default_factory=list)
    top_opportunities: list[str] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    evidence_highlights: list[str] = Field(default_factory=list)
    fusion_explanation: dict | None = None
    decision_answers: list[CompanyDecisionAnswerOut] = Field(default_factory=list)


class ProspectQuestionIn(BaseModel):
    """Prospect-scoped question request."""

    question: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    include_chunks: bool = False
    insight_type: str = "explanation"


class ProspectQuestionOut(BaseModel):
    """Prospect-scoped evidence-grounded answer."""

    prospect_id: str
    company_id: str
    answer: str
    status: str
    retrieval_run_id: int | None = None
    citations: list[CitationOut] = Field(default_factory=list)
    structured_insight: dict | None = None


class ProspectCopilotOut(BaseModel):
    """Prospect-centered copilot workspace payload."""

    prospect: ProspectSummaryOut
    brief: ProspectBriefOut
    evidence: ProspectEvidenceOut
    fusion_explanation: dict | None = None
    suggested_questions: list[str] = Field(default_factory=list)


class ProspectLinkageReviewOut(BaseModel):
    """Review of whether a signal-to-company linkage is too strong, too weak, or reasonable."""

    item_key: str
    title: str | None = None
    evidence_text: str | None = None
    current_linkage_type: str | None = None
    current_linkage_strength: str | None = None
    suggested_linkage_type: str | None = None
    suggested_linkage_strength: str | None = None
    review_status: str
    confidence: float | None = None
    reason: str
    should_affect_scoring: bool | None = None


class ProspectAuditFindingOut(BaseModel):
    """Review finding about subjectivity, overreach, or weak decision logic."""

    finding_key: str
    severity: str
    area: str
    issue: str
    reason: str
    affected_feature_keys: list[str] = Field(default_factory=list)
    suggested_action: str


class ProspectExtractionOpportunityOut(BaseModel):
    """Suggested extraction gap that would improve the case quality."""

    area: str
    why: str
    suggested_output: str


class ProspectReviewOut(BaseModel):
    """Prospect-level LLM review for linkage quality, subjectivity risk, and extraction gaps."""

    prospect_id: str
    company_id: str
    status: str
    review_summary: str
    linkage_reviews: list[ProspectLinkageReviewOut] = Field(default_factory=list)
    audit_findings: list[ProspectAuditFindingOut] = Field(default_factory=list)
    extraction_opportunities: list[ProspectExtractionOpportunityOut] = Field(default_factory=list)
    model_name: str | None = None
