from __future__ import annotations

import json
from typing import Any

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings

MAX_REVIEW_SIGNALS = 5
MAX_REVIEW_FEATURES = 8
MAX_REVIEW_TEXT_CHARS = 220
REVIEW_MAX_TOKENS = 900
REVIEW_TIMEOUT_SECONDS = 35.0


class DecisionReviewService:
    """Use an LLM as a bounded reviewer for linkage and decision quality."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = OpenAIProvider(settings)

    def review(
        self,
        *,
        company: dict[str, Any],
        latest_state: dict[str, Any],
        prospect: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._build_payload(company=company, latest_state=latest_state, prospect=prospect)
        fallback = self._fallback(company=company, latest_state=latest_state, prospect=prospect)

        if not self.settings.llm_enabled:
            return fallback

        try:
            parsed = self.provider.chat_json(
                system_prompt=(
                    "You are a bounded audit reviewer for Hang Seng Bank commercial banking decisions. "
                    "Return compact JSON only. Do not rescore, rank, or add new business facts. "
                    "Review only linkage quality, subjectivity risk, rule overreach, and extraction gaps."
                ),
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                max_tokens=REVIEW_MAX_TOKENS,
                timeout_seconds=min(self.settings.llm_timeout_seconds, REVIEW_TIMEOUT_SECONDS),
                use_response_format=False,
            )
        except Exception as exc:  # noqa: BLE001
            fallback["status"] = "llm_error_fallback"
            fallback["llm_error"] = str(exc)
            return fallback
        return self._normalize(parsed, fallback=fallback)

    def _build_payload(
        self,
        *,
        company: dict[str, Any],
        latest_state: dict[str, Any],
        prospect: dict[str, Any] | None,
    ) -> dict[str, Any]:
        signals = [
            *latest_state.get("opportunity_signals", []),
            *latest_state.get("context_signals", []),
            *latest_state.get("risk_signals", []),
        ]
        signal_items = [
            {
                "item_key": f"signal_{index}",
                "title": _truncate(item.get("title")),
                "evidence_text": _truncate(item.get("detail")),
                "signal_type": item.get("signal_type"),
                "severity": item.get("severity"),
                "current_linkage_type": item.get("linkage_type"),
                "current_linkage_strength": item.get("linkage_strength"),
                "supports_company_scoring": item.get("supports_company_scoring"),
                "context_only": item.get("context_only"),
            }
            for index, item in enumerate(signals[:MAX_REVIEW_SIGNALS], start=1)
        ]

        feature_items = [
            {
                "key": item.get("feature_key"),
                "group": item.get("feature_group"),
                "points": item.get("score_contribution"),
                "rationale": _truncate(item.get("rationale")),
            }
            for item in latest_state.get("decision_features", [])[:MAX_REVIEW_FEATURES]
        ]

        return {
            "company": {
                "company_id": company.get("company_id"),
                "display_name": company.get("display_name") or company.get("canonical_name"),
                "region": company.get("region"),
                "industries": company.get("industries", [])[:3],
                "segments": company.get("segments", [])[:3],
            },
            "prospect": {
                "prospect_id": prospect.get("prospect_id") if prospect else None,
                "priority_level": prospect.get("priority_level") if prospect else None,
                "priority_score": prospect.get("priority_score") if prospect else None,
                "opportunity_score": prospect.get("opportunity_score") if prospect else None,
                "risk_score": prospect.get("risk_score") if prospect else None,
            },
            "scores": {
                "status": latest_state.get("status"),
                "recommended_next_step": latest_state.get("recommended_next_step"),
                "commercial_attractiveness_score": latest_state.get("commercial_attractiveness_score"),
                "immediacy_score": latest_state.get("immediacy_score"),
                "product_fit_score": latest_state.get("product_fit_score"),
                "risk_penalty_score": latest_state.get("risk_penalty_score"),
                "evidence_confidence_score": latest_state.get("evidence_confidence_score"),
            },
            "coverage_flags": latest_state.get("coverage_flags", {}),
            "signals_to_review": signal_items,
            "decision_features": feature_items,
            "top_products": [
                {
                    "product_name": item.get("product_name"),
                    "fit_score": item.get("fit_score"),
                    "rationale": _truncate(item.get("rationale")),
                }
                for item in latest_state.get("product_fit", [])[:3]
            ],
            "rules": [
                "Do not produce a new score or priority.",
                "Review the current decision logic only.",
                "Return at most 3 linkage_reviews, 3 audit_findings, and 3 extraction_opportunities.",
                "Use item_key from signals_to_review when producing linkage_reviews.",
                "Mark context-only or weak macro evidence as should_affect_scoring=false.",
                "Use status='ok' for successful review.",
            ],
            "required_schema": {
                "status": "ok",
                "review_summary": "one short paragraph",
                "linkage_reviews": [
                    {
                        "item_key": "signal_1",
                        "review_status": "confirm/challenge/uncertain",
                        "suggested_linkage_type": "direct_company_link/macro_context_link/cross_border_exposure_link/unknown",
                        "suggested_linkage_strength": "strong/medium/weak",
                        "reason": "short reason",
                        "should_affect_scoring": True,
                    }
                ],
                "audit_findings": [
                    {
                        "finding_key": "short_key",
                        "severity": "low/medium/high",
                        "area": "linkage/product_fit/risk/confidence/scoring",
                        "issue": "short issue",
                        "reason": "short reason",
                        "affected_feature_keys": ["optional"],
                        "suggested_action": "short action",
                    }
                ],
                "extraction_opportunities": [
                    {
                        "area": "management_discussion/business_events/structured_metrics/risk_factors",
                        "why": "short reason",
                        "suggested_output": "short output",
                    }
                ],
            },
        }

    def _fallback(
        self,
        *,
        company: dict[str, Any],
        latest_state: dict[str, Any],
        prospect: dict[str, Any] | None,
    ) -> dict[str, Any]:
        signals = [
            *latest_state.get("opportunity_signals", []),
            *latest_state.get("context_signals", []),
            *latest_state.get("risk_signals", []),
        ]
        linkage_reviews: list[dict[str, Any]] = []
        for index, item in enumerate(signals[:MAX_REVIEW_SIGNALS], start=1):
            signal_type = item.get("signal_type")
            current_linkage_type = item.get("linkage_type")
            suggested_linkage_type = current_linkage_type
            suggested_linkage_strength = item.get("linkage_strength")
            review_status = "confirm"
            reason = "Current linkage is reasonable based on the available structured evidence."

            if signal_type in {"market", "policy", "macro"} and current_linkage_type not in {
                "direct_company_link",
                "macro_context_link",
            }:
                suggested_linkage_type = "macro_context_link"
                suggested_linkage_strength = "weak"
                review_status = "challenge"
                reason = "This looks more like background context than strong company-specific evidence."
            elif signal_type in {"cross_border", "trade"} and current_linkage_type not in {
                "direct_company_link",
                "cross_border_exposure_link",
            }:
                suggested_linkage_type = "cross_border_exposure_link"
                suggested_linkage_strength = "medium"
                review_status = "challenge"
                reason = "This evidence appears more relevant through overseas or trade exposure."

            linkage_reviews.append(
                {
                    "item_key": f"signal_{index}",
                    "title": item.get("title"),
                    "evidence_text": item.get("detail"),
                    "current_linkage_type": current_linkage_type,
                    "current_linkage_strength": item.get("linkage_strength"),
                    "suggested_linkage_type": suggested_linkage_type,
                    "suggested_linkage_strength": suggested_linkage_strength,
                    "review_status": review_status,
                    "confidence": 0.6,
                    "reason": reason,
                    "should_affect_scoring": suggested_linkage_type != "macro_context_link",
                }
            )

        audit_findings: list[dict[str, Any]] = []
        product_fit = latest_state.get("product_fit", [])
        top_product = product_fit[0]["product_name"] if product_fit else None
        feature_keys = {item.get("feature_key") for item in latest_state.get("decision_features", [])}
        evidence_confidence_score = latest_state.get("evidence_confidence_score", 0)
        priority_level = prospect.get("priority_level") if prospect else None

        if priority_level == "high" and evidence_confidence_score < 40:
            audit_findings.append(
                {
                    "finding_key": "high_priority_low_confidence",
                    "severity": "high",
                    "area": "confidence",
                    "issue": "Priority may be too strong relative to current evidence confidence.",
                    "reason": "The company is ranked high priority while evidence confidence remains limited.",
                    "affected_feature_keys": ["direct_evidence_ratio", "structured_evidence_coverage", "source_diversity"],
                    "suggested_action": "Require human review before treating this as a strong RM target.",
                }
            )

        if top_product in {"cross-border payments", "trade finance", "treasury"} and "cross_border_operating_exposure" not in feature_keys:
            audit_findings.append(
                {
                    "finding_key": "cross_border_product_overreach",
                    "severity": "medium",
                    "area": "product_fit",
                    "issue": "Cross-border product hypothesis may be too eager.",
                    "reason": "The product angle is cross-border oriented, but the structured feature set does not yet show explicit cross-border operating exposure.",
                    "affected_feature_keys": ["top_product_fit_strength"],
                    "suggested_action": "Check whether cross-border evidence is direct enough before using this entry angle.",
                }
            )

        if latest_state.get("risk_penalty_score", 0) >= 30 and latest_state.get("recommended_next_step") and "risk" not in latest_state.get("recommended_next_step", ""):
            audit_findings.append(
                {
                    "finding_key": "risk_underemphasized",
                    "severity": "medium",
                    "area": "risk_penalty",
                    "issue": "Risk may not be emphasized enough in the next-step guidance.",
                    "reason": "The current risk penalty is meaningful, but the suggested action does not foreground caution strongly enough.",
                    "affected_feature_keys": ["linked_risk_severity", "structured_risk_coverage"],
                    "suggested_action": "Make risk review explicit before outreach.",
                }
            )

        extraction_opportunities: list[dict[str, Any]] = []
        coverage_flags = latest_state.get("coverage_flags", {})
        if not coverage_flags.get("has_management_discussion"):
            extraction_opportunities.append(
                {
                    "area": "management_discussion",
                    "why": "Current case lacks structured management commentary.",
                    "suggested_output": "Extract strategy, timing, expansion plans, and management statements from the latest report or announcement.",
                }
            )
        if not coverage_flags.get("has_business_events"):
            extraction_opportunities.append(
                {
                    "area": "business_events",
                    "why": "No structured business event is currently captured.",
                    "suggested_output": "Extract expansion, fundraising, acquisition, and partnership events from filings or news.",
                }
            )
        if not coverage_flags.get("has_structured_metrics"):
            extraction_opportunities.append(
                {
                    "area": "structured_metrics",
                    "why": "The current case lacks extracted business or financial metrics.",
                    "suggested_output": "Extract revenue, growth, capex, debt, and operating metrics to support timing and product fit.",
                }
            )
        if not coverage_flags.get("has_risk_factors"):
            extraction_opportunities.append(
                {
                    "area": "risk_factors",
                    "why": "The current case lacks structured risk extraction.",
                    "suggested_output": "Extract regulatory, liquidity, execution, and compliance risks from reports and announcements.",
                }
            )

        display_name = company.get("display_name") or company.get("canonical_name") or "This company"
        summary_parts = [f"{display_name} review generated in fallback mode."]
        if audit_findings:
            summary_parts.append(f"{len(audit_findings)} review finding(s) need attention.")
        if extraction_opportunities:
            summary_parts.append(f"{len(extraction_opportunities)} extraction gap(s) could improve evidence quality.")

        return {
            "status": "fallback",
            "review_summary": " ".join(summary_parts),
            "linkage_reviews": linkage_reviews,
            "audit_findings": audit_findings,
            "extraction_opportunities": extraction_opportunities,
            "model_name": None,
            "llm_error": None,
        }

    def _normalize(self, payload: dict[str, Any], *, fallback: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": payload.get("status", "ok"),
            "review_summary": payload.get("review_summary") or fallback["review_summary"],
            "linkage_reviews": _normalize_linkage_reviews(
                payload.get("linkage_reviews"),
                fallback["linkage_reviews"],
            ),
            "audit_findings": _list_or_fallback(payload.get("audit_findings"), fallback["audit_findings"]),
            "extraction_opportunities": _list_or_fallback(
                payload.get("extraction_opportunities"),
                fallback["extraction_opportunities"],
            ),
            "model_name": self.settings.llm_chat_model if self.settings.llm_enabled else None,
            "llm_error": payload.get("llm_error"),
        }


def _truncate(value: Any, limit: int = MAX_REVIEW_TEXT_CHARS) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _list_or_fallback(value: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return fallback
    return [item for item in value if isinstance(item, dict)] or fallback


def _normalize_linkage_reviews(value: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return fallback
    fallback_by_key = {item.get("item_key"): item for item in fallback if item.get("item_key")}
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        item_key = item.get("item_key")
        base = fallback_by_key.get(item_key, {})
        merged = dict(base)
        for key, raw_value in item.items():
            if raw_value is not None and raw_value != "":
                merged[key] = raw_value
        if not merged.get("item_key"):
            continue
        if not merged.get("review_status"):
            merged["review_status"] = "uncertain"
        if not merged.get("reason"):
            merged["reason"] = "LLM review did not provide a reason; use fallback context for manual review."
        normalized.append(merged)
    return normalized or fallback
