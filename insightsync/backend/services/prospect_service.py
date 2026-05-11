from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from insightsync.backend.core.config import Settings
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.services.company_service import CompanyService
from insightsync.backend.services.decision_framework import priority_score_policy, scorecard_contract
from insightsync.backend.services.decision_review_service import DecisionReviewService
from insightsync.backend.services.fusion_explainer import FusionExplainer
from insightsync.backend.services.insight_generator import InsightGenerator


class ProspectService:
    """Build business-facing prospect views from company-centric state."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.repo = ReadRepository(db)
        self.company_service = CompanyService(db)
        self.settings = settings

    @staticmethod
    def _prospect_id(company_id: str) -> str:
        return f"prospect:{company_id}"

    @staticmethod
    def _company_id_from_prospect_id(prospect_id: str) -> str:
        return prospect_id.removeprefix("prospect:")

    @staticmethod
    def _recommended_product_themes(detail: dict[str, Any]) -> list[str]:
        latest_state = detail["latest_state"]
        return [item["product_name"] for item in latest_state.get("product_fit", [])[:4]]

    @staticmethod
    def _build_opportunity_score(detail: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        latest_state = detail["latest_state"]
        components = [
            {
                "name": feature["feature_key"],
                "category": feature["feature_group"],
                "points": feature["score_contribution"],
                "detail": feature["rationale"],
            }
            for feature in latest_state.get("decision_features", [])
            if feature["feature_group"] in {"commercial_attractiveness", "immediacy", "product_fit"}
        ]
        score = (
            latest_state.get("commercial_attractiveness_score", 0)
            + latest_state.get("immediacy_score", 0)
            + latest_state.get("product_fit_score", 0)
        )
        return min(score, 100), components

    @staticmethod
    def _build_risk_score(detail: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        latest_state = detail["latest_state"]
        components = [
            {
                "name": feature["feature_key"],
                "category": feature["feature_group"],
                "points": feature["score_contribution"],
                "detail": feature["rationale"],
            }
            for feature in latest_state.get("decision_features", [])
            if feature["feature_group"] == "risk_penalty"
        ]
        return min(latest_state.get("risk_penalty_score", 0), 100), components

    @staticmethod
    def _build_priority_score(
        *,
        opportunity_score: int,
        risk_score: int,
        evidence_confidence_score: int,
        status: str,
    ) -> tuple[int, list[dict[str, Any]]]:
        policy = priority_score_policy()
        opportunity_points = int(opportunity_score * float(policy["opportunity_weight"]))
        confidence_points = int(evidence_confidence_score * float(policy["evidence_confidence_weight"]))
        risk_headroom = max(0, int(policy["risk_headroom_cap"]) - risk_score)
        risk_buffer_points = int(risk_headroom * float(policy["risk_buffer_weight"]))
        components = [
            {
                "name": "opportunity_weighted",
                "category": "priority",
                "points": opportunity_points,
                "detail": f"{int(float(policy['opportunity_weight']) * 100)}% weighting applied to opportunity score {opportunity_score}",
            },
            {
                "name": "evidence_confidence_weighted",
                "category": "priority",
                "points": confidence_points,
                "detail": f"{int(float(policy['evidence_confidence_weight']) * 100)}% weighting applied to evidence confidence score {evidence_confidence_score}",
            },
            {
                "name": "risk_buffer",
                "category": "priority",
                "points": risk_buffer_points,
                "detail": f"{int(float(policy['risk_buffer_weight']) * 100)}% weighting applied to remaining risk headroom {risk_headroom}",
            },
        ]
        if status == "actionable":
            components.append(
                {
                    "name": "actionable_status_gate",
                    "category": "priority",
                    "points": 0,
                    "detail": "company status is actionable, so it can qualify for high priority",
                }
            )

        return min(opportunity_points + confidence_points + risk_buffer_points, 100), components

    @staticmethod
    def _linkage_quality(latest_state: dict[str, Any]) -> dict[str, Any]:
        linked_items = [
            *latest_state.get("opportunity_signals", []),
            *latest_state.get("risk_signals", []),
            *latest_state.get("context_signals", []),
        ]
        total = len(linked_items)
        scoreable_items = [item for item in linked_items if item.get("supports_company_scoring") is not False]
        direct_items = [item for item in linked_items if item.get("linkage_type") == "direct_company_link"]
        strong_items = [item for item in linked_items if item.get("linkage_strength") == "strong"]
        context_only_items = [item for item in linked_items if item.get("context_only")]
        type_counts: dict[str, int] = {}
        for item in linked_items:
            linkage_type = item.get("linkage_type") or "unknown"
            type_counts[linkage_type] = type_counts.get(linkage_type, 0) + 1

        return {
            "linked_evidence_count": total,
            "scoreable_evidence_count": len(scoreable_items),
            "direct_evidence_count": len(direct_items),
            "strong_linkage_count": len(strong_items),
            "context_only_count": len(context_only_items),
            "direct_evidence_ratio": round(len(direct_items) / total, 2) if total else 0.0,
            "scoreable_evidence_ratio": round(len(scoreable_items) / total, 2) if total else 0.0,
            "linkage_type_counts": type_counts,
        }

    @classmethod
    def _governance_flags(
        cls,
        *,
        latest_state: dict[str, Any],
        priority_score: int,
        priority_level: str,
        opportunity_score: int,
        risk_score: int,
        evidence_confidence_score: int,
        linkage_quality: dict[str, Any],
    ) -> list[dict[str, Any]]:
        flags: list[dict[str, Any]] = []
        if priority_level == "high" and evidence_confidence_score < 50:
            flags.append(
                {
                    "flag_key": "high_priority_below_confidence_target",
                    "severity": "high",
                    "area": "evidence_confidence",
                    "message": "High-priority ranking should be reviewed because evidence confidence is below the target threshold.",
                    "suggested_action": "Require analyst or RM review before using this as a primary outreach target.",
                }
            )
        if priority_score >= 50 and linkage_quality["direct_evidence_ratio"] < 0.5:
            flags.append(
                {
                    "flag_key": "priority_relies_on_contextual_linkage",
                    "severity": "medium",
                    "area": "linkage",
                    "message": "Priority score relies on a low share of direct company-linked evidence.",
                    "suggested_action": "Validate company identity and evidence linkage before outreach.",
                }
            )
        if opportunity_score > 60 and linkage_quality["context_only_count"] > linkage_quality["direct_evidence_count"]:
            flags.append(
                {
                    "flag_key": "opportunity_context_overreach",
                    "severity": "medium",
                    "area": "opportunity_score",
                    "message": "Opportunity score may be overstated because context-only evidence outnumbers direct evidence.",
                    "suggested_action": "Use macro or market context as background until direct company evidence is added.",
                }
            )
        if risk_score >= 30 and latest_state.get("recommended_next_step") and "risk" not in latest_state["recommended_next_step"]:
            flags.append(
                {
                    "flag_key": "risk_not_explicit_in_next_step",
                    "severity": "medium",
                    "area": "risk_score",
                    "message": "Risk score is meaningful but the recommended next step does not explicitly mention risk review.",
                    "suggested_action": "Make risk review explicit in the banker workflow before outreach.",
                }
            )
        return flags

    @classmethod
    def _priority_level(cls, *, priority_score: int, status: str) -> str:
        policy = priority_score_policy()
        if status == "actionable" and priority_score >= int(policy["high_priority_threshold"]):
            return "high"
        if priority_score >= int(policy["medium_priority_threshold"]):
            return "medium"
        return "monitor"

    @staticmethod
    def _why_prioritized(detail: dict[str, Any]) -> list[str]:
        latest_state = detail["latest_state"]
        reasons: list[str] = []

        for answer in latest_state.get("decision_answers", [])[:2]:
            if answer.get("answer"):
                reasons.append(answer["answer"])
        reasons.extend(latest_state.get("signal_highlights", [])[:2])
        if latest_state.get("fusion_summary"):
            reasons.append(latest_state["fusion_summary"])
        if latest_state.get("why_now"):
            reasons.append(latest_state["why_now"])
        if latest_state.get("state_summary"):
            reasons.append(latest_state["state_summary"])

        deduped: list[str] = []
        seen: set[str] = set()
        for item in reasons:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped[:4]

    def _build_prospect_summary(self, detail: dict[str, Any]) -> dict[str, Any]:
        company = detail["company"]
        latest_state = detail["latest_state"]
        opportunity_score, opportunity_components = self._build_opportunity_score(detail)
        risk_score, risk_components = self._build_risk_score(detail)
        evidence_confidence_score = latest_state.get("evidence_confidence_score", 0)
        decision_answers = latest_state.get("decision_answers", [])
        priority_score, priority_components = self._build_priority_score(
            opportunity_score=opportunity_score,
            risk_score=risk_score,
            evidence_confidence_score=evidence_confidence_score,
            status=latest_state["status"],
        )
        priority_level = self._priority_level(priority_score=priority_score, status=latest_state["status"])
        linkage_quality = self._linkage_quality(latest_state)
        governance_flags = self._governance_flags(
            latest_state=latest_state,
            priority_score=priority_score,
            priority_level=priority_level,
            opportunity_score=opportunity_score,
            risk_score=risk_score,
            evidence_confidence_score=evidence_confidence_score,
            linkage_quality=linkage_quality,
        )

        return {
            "prospect_id": self._prospect_id(company["company_id"]),
            "company_id": company["company_id"],
            "canonical_name": company["canonical_name"],
            "display_name": company.get("display_name"),
            "region": company.get("region"),
            "city": company.get("city"),
            "industries": company.get("industries", []),
            "segments": company.get("segments", []),
            "activity_at": latest_state.get("activity_at"),
            "status": latest_state["status"],
            "priority_level": priority_level,
            "priority_score": priority_score,
            "opportunity_score": opportunity_score,
            "risk_score": risk_score,
            "evidence_confidence_score": evidence_confidence_score,
            "commercial_attractiveness_score": latest_state.get("commercial_attractiveness_score", 0),
            "immediacy_score": latest_state.get("immediacy_score", 0),
            "product_fit_score": latest_state.get("product_fit_score", 0),
            "risk_penalty_score": latest_state.get("risk_penalty_score", 0),
            "focus_tags": latest_state.get("focus_tags", []),
            "why_prioritized": self._why_prioritized(detail),
            "recommended_next_step": latest_state.get("recommended_next_step"),
            "recommended_product_themes": self._recommended_product_themes(detail),
            "product_fit": latest_state.get("product_fit", []),
            "recommended_entry_angles": latest_state.get("recommended_entry_angles", []),
            "decision_features": latest_state.get("decision_features", []),
            "decision_answers": decision_answers,
            "fusion": latest_state.get("fusion"),
            "score_breakdown": {
                **scorecard_contract(),
                "score_inputs": {
                    "opportunity_score": opportunity_score,
                    "risk_score": risk_score,
                    "evidence_confidence_score": evidence_confidence_score,
                    "priority_score": priority_score,
                },
                "opportunity_components": opportunity_components,
                "risk_components": risk_components,
                "priority_components": priority_components,
                "linkage_quality": linkage_quality,
                "governance_flags": governance_flags,
            },
        }

    def list_prospects(
        self,
        *,
        limit: int,
        offset: int,
        q: str | None = None,
        region: str | None = None,
        segment: str | None = None,
        industry: str | None = None,
        status: str | None = None,
        priority_level: str | None = None,
    ) -> dict[str, Any]:
        companies = self.repo.list_companies(
            limit=max(limit + offset + 20, 50),
            offset=0,
            q=q,
            region=region,
            segment=segment,
            industry=industry,
        )

        items: list[dict[str, Any]] = []
        for company in companies:
            detail = self.company_service.get_company_detail(company["company_id"])
            if not detail:
                continue
            summary = self._build_prospect_summary(detail)
            if status and summary["status"] != status:
                continue
            if priority_level and summary["priority_level"] != priority_level:
                continue
            items.append(summary)

        items.sort(
            key=lambda item: (
                item["priority_score"],
                item["opportunity_score"],
                item["activity_at"] or "",
                item["company_id"],
            ),
            reverse=True,
        )
        total = len(items)
        return {
            "items": items[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_prospect_detail(self, prospect_id: str) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None
        brief = self.get_prospect_brief(prospect_id)
        return {
            "prospect": self._build_prospect_summary(detail),
            "company": detail["company"],
            "latest_state": detail["latest_state"],
            "fusion_explanation": brief.get("fusion_explanation") if brief else None,
            "recent_signals": detail["recent_signals"],
            "recent_timeline": detail["recent_timeline"],
            "recent_insights": detail["recent_insights"],
            "recent_documents": detail["recent_documents"],
            "key_metrics": detail["key_metrics"],
            "key_risk_factors": detail["key_risk_factors"],
            "key_business_events": detail["key_business_events"],
        }

    def list_prospect_signals(self, prospect_id: str, *, limit: int, offset: int) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None
        items = detail["recent_signals"]
        return {
            "items": items[offset : offset + limit],
            "limit": limit,
            "offset": offset,
        }

    def list_prospect_timeline(self, prospect_id: str, *, limit: int, offset: int) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None
        items = detail["recent_timeline"]
        return {
            "items": items[offset : offset + limit],
            "limit": limit,
            "offset": offset,
        }

    def list_prospect_insights(
        self,
        prospect_id: str,
        *,
        limit: int,
        offset: int,
        insight_type: str | None = None,
    ) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None
        items = self.repo.list_generated_insights(
            limit=limit,
            offset=offset,
            company_id=company_id,
            insight_type=insight_type,
        )
        return {
            "items": items,
            "limit": limit,
            "offset": offset,
        }

    def get_prospect_evidence(self, prospect_id: str) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None
        latest_state = detail["latest_state"]
        return {
            "prospect_id": prospect_id,
            "company_id": company_id,
            "coverage_flags": latest_state["coverage_flags"],
            "evidence_summary": latest_state["evidence_summary"],
            "recent_documents": detail["recent_documents"],
            "key_metrics": detail["key_metrics"],
            "key_risk_factors": detail["key_risk_factors"],
            "key_business_events": detail["key_business_events"],
        }

    def get_prospect_brief(self, prospect_id: str) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None

        prospect = self._build_prospect_summary(detail)
        latest_state = detail["latest_state"]
        explanation = None
        if self.settings:
            explanation = FusionExplainer(self.settings).explain(
                company=detail["company"],
                latest_state=latest_state,
                prospect=prospect,
            )
        top_opportunities = [
            item.get("detail") or item.get("title")
            for item in latest_state.get("opportunity_signals", [])[:3]
            if item.get("detail") or item.get("title")
        ]
        top_risks = [
            item.get("detail") or item.get("title")
            for item in latest_state.get("risk_signals", [])[:3]
            if item.get("detail") or item.get("title")
        ]
        evidence_highlights = latest_state.get("signal_highlights", [])[:3]

        display_name = prospect.get("display_name") or prospect["canonical_name"]
        summary_parts = [
            f"{display_name} is currently {prospect['priority_level']} priority with status {prospect['status']}."
        ]
        if explanation and explanation.get("headline"):
            summary_parts.append(explanation["headline"])
        elif prospect.get("why_prioritized"):
            summary_parts.append(prospect["why_prioritized"][0])
        if prospect.get("recommended_next_step"):
            summary_parts.append(f"Next step: {prospect['recommended_next_step']}.")

        return {
            "prospect_id": prospect_id,
            "company_id": company_id,
            "title": f"{display_name} brief",
            "summary": " ".join(summary_parts),
            "priority_level": prospect["priority_level"],
            "recommended_next_step": prospect.get("recommended_next_step"),
            "recommended_product_themes": prospect.get("recommended_product_themes", []),
            "recommended_entry_angles": prospect.get("recommended_entry_angles", []),
            "top_opportunities": top_opportunities,
            "top_risks": top_risks,
            "evidence_highlights": evidence_highlights,
            "fusion_explanation": explanation,
            "decision_answers": latest_state.get("decision_answers", []),
        }

    @staticmethod
    def _suggested_questions(detail: dict[str, Any]) -> list[str]:
        company = detail["company"]
        latest_state = detail["latest_state"]
        display_name = company.get("display_name") or company["canonical_name"]
        questions: list[str] = []

        if latest_state.get("opportunity_signals"):
            questions.append(f"What are the strongest opportunity signals for {display_name}?")
        if latest_state.get("risk_signals"):
            questions.append(f"What are the main risks to watch for {display_name}?")
        if latest_state["coverage_flags"].get("has_business_events"):
            questions.append(f"What recent business events matter most for {display_name}?")
        if latest_state["coverage_flags"].get("has_structured_metrics"):
            questions.append(f"Which metrics best support RM outreach for {display_name}?")

        seen: set[str] = set()
        ordered: list[str] = []
        for item in questions:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered[:4]

    def get_prospect_copilot(self, prospect_id: str) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None

        prospect = self._build_prospect_summary(detail)
        brief = self.get_prospect_brief(prospect_id)
        evidence = self.get_prospect_evidence(prospect_id)
        if not brief or not evidence:
            return None

        return {
            "prospect": prospect,
            "brief": brief,
            "evidence": evidence,
            "fusion_explanation": brief.get("fusion_explanation"),
            "suggested_questions": self._suggested_questions(detail),
        }

    def get_prospect_review(self, prospect_id: str) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail or not self.settings:
            return None

        prospect = self._build_prospect_summary(detail)
        review = DecisionReviewService(self.settings).review(
            company=detail["company"],
            latest_state=detail["latest_state"],
            prospect=prospect,
        )
        return {
            "prospect_id": prospect_id,
            "company_id": company_id,
            **review,
        }

    def answer_prospect_question(
        self,
        prospect_id: str,
        *,
        question: str,
        top_k: int | None = None,
        insight_type: str = "explanation",
    ) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail or not self.settings:
            return None

        company = detail["company"]
        filters = {
            "company_id": company_id,
        }
        if company.get("region") == "Hong Kong":
            filters["entity"] = "HKG"

        result = InsightGenerator(self.db, self.settings).answer_question(
            question=question,
            filters=filters,
            top_k=top_k,
            insight_type=insight_type,
        )
        return {
            "prospect_id": prospect_id,
            "company_id": company_id,
            "answer": result["answer"],
            "status": result["status"],
            "retrieval_run_id": result.get("retrieval_run_id"),
            "citations": result.get("citations", []),
            "structured_insight": result.get("structured_insight"),
        }
