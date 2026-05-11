from __future__ import annotations

import json
from typing import Any

from insightsync.backend.core.config import Settings


class DecisionReviewService:
    """Use an LLM as a bounded reviewer for linkage and decision quality."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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

        from openai import OpenAI

        client = OpenAI(api_key=self.settings.llm_api_key, base_url=self.settings.llm_base_url)
        response = client.chat.completions.create(
            model=self.settings.llm_chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You review commercial banking decision logic as strict JSON. "
                        "You are not allowed to rescore the company. "
                        "You only review linkage quality, subjectivity risks, rule overreach, "
                        "and extraction gaps based on the supplied evidence."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
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
                "title": item.get("title"),
                "detail": item.get("detail"),
                "source_type": item.get("source_type"),
                "source": item.get("source"),
                "signal_type": item.get("signal_type"),
                "severity": item.get("severity"),
                "current_linkage_type": item.get("linkage_type"),
                "current_linkage_strength": item.get("linkage_strength"),
                "current_linkage_rationale": item.get("linkage_rationale"),
                "supports_company_scoring": item.get("supports_company_scoring"),
                "context_only": item.get("context_only"),
            }
            for item in signals[:8]
        ]

        feature_items = [
            {
                "feature_key": item.get("feature_key"),
                "feature_label": item.get("feature_label"),
                "feature_group": item.get("feature_group"),
                "feature_description": item.get("feature_description"),
                "business_question": item.get("business_question"),
                "value_num": item.get("value_num"),
                "score_contribution": item.get("score_contribution"),
                "rationale": item.get("rationale"),
            }
            for item in latest_state.get("decision_features", [])
        ]

        return {
            "company": {
                "company_id": company.get("company_id"),
                "display_name": company.get("display_name") or company.get("canonical_name"),
                "region": company.get("region"),
                "industries": company.get("industries", []),
                "segments": company.get("segments", []),
            },
            "prospect": {
                "prospect_id": prospect.get("prospect_id") if prospect else None,
                "priority_level": prospect.get("priority_level") if prospect else None,
                "priority_score": prospect.get("priority_score") if prospect else None,
                "opportunity_score": prospect.get("opportunity_score") if prospect else None,
                "risk_score": prospect.get("risk_score") if prospect else None,
            },
            "latest_state": {
                "status": latest_state.get("status"),
                "why_now": latest_state.get("why_now"),
                "recommended_next_step": latest_state.get("recommended_next_step"),
                "commercial_attractiveness_score": latest_state.get("commercial_attractiveness_score"),
                "immediacy_score": latest_state.get("immediacy_score"),
                "product_fit_score": latest_state.get("product_fit_score"),
                "risk_penalty_score": latest_state.get("risk_penalty_score"),
                "evidence_confidence_score": latest_state.get("evidence_confidence_score"),
                "coverage_flags": latest_state.get("coverage_flags", {}),
                "signals": signal_items,
                "decision_features": feature_items,
                "product_fit": latest_state.get("product_fit", []),
                "decision_answers": latest_state.get("decision_answers", []),
            },
            "instructions": [
                "Review whether each current linkage assignment is appropriate, too strong, or too weak.",
                "Flag rules or outputs that appear overly subjective, overly expert-driven, or too eager.",
                "Do not produce a new score. Review the current decision logic only.",
                "Highlight missing extraction opportunities that would materially improve this case.",
                "Return JSON with review_summary, linkage_reviews, audit_findings, and extraction_opportunities.",
            ],
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
        for index, item in enumerate(signals[:8], start=1):
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
        }

    def _normalize(self, payload: dict[str, Any], *, fallback: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": payload.get("status", "ok"),
            "review_summary": payload.get("review_summary") or fallback["review_summary"],
            "linkage_reviews": payload.get("linkage_reviews") or fallback["linkage_reviews"],
            "audit_findings": payload.get("audit_findings") or fallback["audit_findings"],
            "extraction_opportunities": payload.get("extraction_opportunities") or fallback["extraction_opportunities"],
            "model_name": self.settings.llm_chat_model if self.settings.llm_enabled else None,
        }
