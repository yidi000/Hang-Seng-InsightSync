from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IntelligenceRecord:
    source: str
    dataset: str
    record_key: str
    record_type: str
    event_time: str | None
    company_id: str | None
    entity: str | None
    title: str | None
    summary: str | None
    region: str | None
    industry: str | None
    tags: list[str]
    payload: dict[str, Any]
    evidence_url: str | None
    lang: str | None
    raw: dict[str, Any] | None = None


@dataclass(slots=True)
class TriggerSignal:
    source: str
    dataset: str
    signal_key: str
    signal_type: str
    event_time: str
    company_id: str | None
    entity: str | None
    indicator: str | None
    value_num: float | None
    value_text: str | None
    unit: str | None
    signal_text: str
    signal_score: float | None = None
    signal_level: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TimelineEvent:
    source: str
    company_id: str | None
    entity: str | None
    event_time: str | None
    event_type: str
    headline: str
    detail: str | None
    evidence_url: str | None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProspectScore:
    company_id: str
    score: float | None
    tier: str | None
    reasons: list[str] = field(default_factory=list)
    recommended_products: list[str] = field(default_factory=list)
    recommended_entry_angle: str | None = None


@dataclass(slots=True)
class GeneratedInsight:
    source: str
    company_id: str | None
    entity: str | None
    insight_type: str  # opportunity / risk / action
    title: str
    summary: str
    confidence: float | None = None
    evidence_record_keys: list[str] = field(default_factory=list)
    evidence_signal_keys: list[str] = field(default_factory=list)
    model_name: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompanyProfile:
    source: str
    company_id: str
    canonical_name: str
    display_name: str | None
    country: str | None
    region: str | None
    city: str | None
    segments: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    website_url: str | None = None
    linkedin_url: str | None = None
    facebook_url: str | None = None
    x_url: str | None = None
    instagram_url: str | None = None
    wikipedia_url: str | None = None
    profile_summary: str | None = None
    description: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CollectionBatch:
    source: str
    intelligence_records: list[IntelligenceRecord] = field(default_factory=list)
    trigger_signals: list[TriggerSignal] = field(default_factory=list)
    timeline_events: list[TimelineEvent] = field(default_factory=list)
    prospect_scores: list[ProspectScore] = field(default_factory=list)
    generated_insights: list[GeneratedInsight] = field(default_factory=list)
    companies: list[CompanyProfile] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def counts(self) -> dict[str, int]:
        return {
            "intelligence_records": len(self.intelligence_records),
            "trigger_signals": len(self.trigger_signals),
            "timeline_events": len(self.timeline_events),
            "prospect_scores": len(self.prospect_scores),
            "generated_insights": len(self.generated_insights),
            "companies": len(self.companies),
        }
