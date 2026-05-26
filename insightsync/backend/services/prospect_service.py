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
        prospect_id = self._prospect_id(company["company_id"])
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
        workflow_state = self.repo.get_prospect_workflow_state(
            prospect_id=prospect_id,
            company_id=company["company_id"],
        )

        return {
            "prospect_id": prospect_id,
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
            "workflow_state": workflow_state,
        }

    @staticmethod
    def _compact_product_themes(focus_tags: list[str]) -> list[str]:
        themes: list[str] = []
        if any(tag in {"cross_border", "trade"} for tag in focus_tags):
            themes.extend(["cross-border payments", "trade finance", "treasury"])
        if any(tag in {"financing", "growth", "expansion", "acquisition", "m&a"} for tag in focus_tags):
            themes.extend(["working capital", "term loan", "cash management"])
        if "market" in focus_tags:
            themes.append("capital markets")
        if any(tag in {"risk", "regulatory", "compliance", "warning", "litigation", "risk_review"} for tag in focus_tags):
            themes.append("risk review")

        deduped: list[str] = []
        for theme in themes or ["Corporate Banking"]:
            if theme not in deduped:
                deduped.append(theme)
        return deduped[:4]

    @classmethod
    def _build_compact_prospect_summary(
        cls,
        company: dict[str, Any],
        signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prospect_id = cls._prospect_id(company["company_id"])
        signal_types: list[str] = []
        signal_titles: list[str] = []
        for signal in signals:
            signal_type = (signal.get("signal_type") or "").lower()
            if signal_type and signal_type not in signal_types:
                signal_types.append(signal_type)
            title = signal.get("signal_text") or signal.get("value_text") or signal.get("indicator")
            if title and title not in signal_titles:
                signal_titles.append(title)

        focus_tags = signal_types[:3]
        signal_count = len(signals)
        opportunity_signal_count = sum(
            1
            for signal in signals
            if (signal.get("signal_type") or "").lower()
            in {"growth", "cross_border", "market", "financing", "expansion", "acquisition", "m&a", "trade"}
        )
        risk_signal_count = sum(
            1
            for signal in signals
            if (signal.get("signal_type") or "").lower() in {"risk", "regulatory", "compliance", "warning", "litigation"}
        )
        status = "monitor"
        if signal_count:
            status = "active"
        if opportunity_signal_count >= 2 or risk_signal_count >= 2:
            status = "actionable"

        opportunity_score = min(100, opportunity_signal_count * 22 + signal_count * 5 + (8 if focus_tags else 0))
        risk_score = min(100, risk_signal_count * 20)
        evidence_confidence_score = min(100, signal_count * 15 + (20 if opportunity_signal_count else 0))
        priority_score, priority_components = cls._build_priority_score(
            opportunity_score=opportunity_score,
            risk_score=risk_score,
            evidence_confidence_score=evidence_confidence_score,
            status=status,
        )
        priority_level = cls._priority_level(priority_score=priority_score, status=status)
        product_themes = cls._compact_product_themes(focus_tags)
        activity_at = signals[0].get("event_time") if signals else company.get("activity_at")
        linkage_quality = {
            "linked_evidence_count": signal_count,
            "scoreable_evidence_count": signal_count,
            "direct_evidence_count": signal_count,
            "strong_linkage_count": signal_count,
            "context_only_count": 0,
            "direct_evidence_ratio": 1.0 if signal_count else 0.0,
            "scoreable_evidence_ratio": 1.0 if signal_count else 0.0,
            "linkage_type_counts": {"direct_company_link": signal_count} if signal_count else {},
        }
        latest_state = {
            "recommended_next_step": (
                f"review {product_themes[0]} angle and validate the linked evidence"
                if product_themes
                else "review linked evidence before outreach"
            )
        }
        governance_flags = cls._governance_flags(
            latest_state=latest_state,
            priority_score=priority_score,
            priority_level=priority_level,
            opportunity_score=opportunity_score,
            risk_score=risk_score,
            evidence_confidence_score=evidence_confidence_score,
            linkage_quality=linkage_quality,
        )

        return {
            "prospect_id": prospect_id,
            "company_id": company["company_id"],
            "canonical_name": company["canonical_name"],
            "display_name": company.get("display_name"),
            "region": company.get("region"),
            "city": company.get("city"),
            "industries": company.get("industries", []),
            "segments": company.get("segments", []),
            "activity_at": activity_at,
            "status": status,
            "priority_level": priority_level,
            "priority_score": priority_score,
            "opportunity_score": opportunity_score,
            "risk_score": risk_score,
            "evidence_confidence_score": evidence_confidence_score,
            "commercial_attractiveness_score": min(40, opportunity_signal_count * 16),
            "immediacy_score": min(20, signal_count * 5),
            "product_fit_score": 8 if product_themes else 0,
            "risk_penalty_score": risk_score,
            "focus_tags": focus_tags,
            "why_prioritized": [
                reason
                for reason in [
                    f"{signal_count} recent signals linked" if signal_count else None,
                    signal_titles[0] if signal_titles else None,
                ]
                if reason
            ],
            "recommended_next_step": latest_state["recommended_next_step"],
            "recommended_product_themes": product_themes,
            "product_fit": [
                {
                    "product_name": product,
                    "fit_score": max(60, 80 - index * 4),
                    "rationale": "Recommended from recent company-linked trigger signals.",
                    "supporting_signals": signal_titles[:3],
                }
                for index, product in enumerate(product_themes)
            ],
            "recommended_entry_angles": [
                f"Lead with the company event: {signal_titles[0]}" if signal_titles else "Review recent company activity."
            ],
            "decision_features": [],
            "decision_answers": [],
            "fusion": None,
            "score_breakdown": {
                **scorecard_contract(),
                "score_inputs": {
                    "opportunity_score": opportunity_score,
                    "risk_score": risk_score,
                    "evidence_confidence_score": evidence_confidence_score,
                    "priority_score": priority_score,
                },
                "opportunity_components": [],
                "risk_components": [],
                "priority_components": priority_components,
                "linkage_quality": linkage_quality,
                "governance_flags": governance_flags,
            },
            "workflow_state": {
                "prospect_id": prospect_id,
                "company_id": company["company_id"],
                "owner": None,
                "stage": "new",
                "status": "open",
                "last_action": None,
                "next_action": None,
                "review_status": "not_reviewed",
                "notes": None,
                "updated_at": None,
            },
        }

    def list_compact_prospects(
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
        return self.list_prospects(
            limit=limit,
            offset=offset,
            q=q,
            region=region,
            segment=segment,
            industry=industry,
            status=status,
            priority_level=priority_level,
        )

    def list_lightweight_prospects(
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
            limit=max(limit + offset + 200, 500),
            offset=0,
            q=q,
            region=region,
            segment=segment,
            industry=industry,
        )
        company_ids = {company["company_id"] for company in companies}
        signals_by_company: dict[str, list[dict[str, Any]]] = {company_id: [] for company_id in company_ids}
        for signal in self.repo.list_signals(limit=10000, offset=0):
            company_id = signal.get("company_id")
            if company_id in signals_by_company:
                signals_by_company[company_id].append(signal)

        items = [
            self._build_compact_prospect_summary(company, signals_by_company.get(company["company_id"], []))
            for company in companies
        ]
        if status:
            items = [item for item in items if item["status"] == status]
        if priority_level:
            items = [item for item in items if item["priority_level"] == priority_level]

        items.sort(
            key=lambda item: (
                item["priority_score"],
                item["opportunity_score"],
                str(item["activity_at"] or ""),
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
            limit=max(limit + offset + 20, 20),
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
        prospect = self._build_prospect_summary(detail)
        return {
            "prospect": prospect,
            "workflow_state": prospect["workflow_state"],
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

    def get_prospect_workflow(self, prospect_id: str) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None
        return self.repo.get_prospect_workflow_state(prospect_id=prospect_id, company_id=company_id)

    def update_prospect_workflow(self, prospect_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        company_id = self._company_id_from_prospect_id(prospect_id)
        detail = self.company_service.get_company_detail(company_id)
        if not detail:
            return None
        return self.repo.upsert_prospect_workflow_state(
            prospect_id=prospect_id,
            company_id=company_id,
            owner=payload.get("owner"),
            stage=payload["stage"],
            status=payload["status"],
            last_action=payload.get("last_action"),
            next_action=payload.get("next_action"),
            review_status=payload["review_status"],
            notes=payload.get("notes"),
        )

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
                allow_llm=self.settings.llm_brief_enabled,
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
