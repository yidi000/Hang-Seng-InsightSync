from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from insightsync.backend.core.config import Settings
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.services.company_service import CompanyService
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
        focus_tags = set(latest_state.get("focus_tags", []))
        products: list[str] = []

        if "cross_border" in focus_tags:
            products.extend(["cross-border payments", "trade finance", "treasury"])
        if "growth" in focus_tags or "expansion" in focus_tags:
            products.extend(["working capital", "term loan", "cash management"])
        if "market" in focus_tags:
            products.append("capital markets")
        if latest_state.get("risk_signals"):
            products.append("risk review")

        seen: set[str] = set()
        ordered: list[str] = []
        for item in products:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered[:4]

    @staticmethod
    def _build_opportunity_score(detail: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        latest_state = detail["latest_state"]
        coverage_flags = latest_state["coverage_flags"]
        components: list[dict[str, Any]] = []

        opportunity_signal_points = min(len(latest_state.get("opportunity_signals", [])) * 20, 40)
        if opportunity_signal_points > 0:
            components.append(
                {
                    "name": "opportunity_signals",
                    "category": "opportunity",
                    "points": opportunity_signal_points,
                    "detail": f"{len(latest_state.get('opportunity_signals', []))} opportunity signal(s) linked",
                }
            )

        recent_signal_points = min(detail["stats"].get("signal_count", 0) * 5, 15)
        if recent_signal_points > 0:
            components.append(
                {
                    "name": "recent_signal_volume",
                    "category": "opportunity",
                    "points": recent_signal_points,
                    "detail": f"{detail['stats'].get('signal_count', 0)} recent signal(s) linked to the company",
                }
            )

        if coverage_flags.get("has_management_discussion"):
            components.append(
                {
                    "name": "management_discussion",
                    "category": "opportunity",
                    "points": 10,
                    "detail": "management discussion summary is available",
                }
            )
        if coverage_flags.get("has_business_events"):
            components.append(
                {
                    "name": "business_events",
                    "category": "opportunity",
                    "points": 10,
                    "detail": "structured business events are available",
                }
            )
        if coverage_flags.get("has_structured_metrics"):
            components.append(
                {
                    "name": "structured_metrics",
                    "category": "opportunity",
                    "points": 10,
                    "detail": "structured metrics are available for validation",
                }
            )
        if detail["stats"].get("generated_insight_count", 0) > 0:
            components.append(
                {
                    "name": "generated_insights",
                    "category": "opportunity",
                    "points": 15,
                    "detail": f"{detail['stats'].get('generated_insight_count', 0)} generated insight(s) already exist",
                }
            )

        score = sum(item["points"] for item in components)
        return min(score, 100), components

    @staticmethod
    def _build_risk_score(detail: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        latest_state = detail["latest_state"]
        components: list[dict[str, Any]] = []

        for index, risk in enumerate(latest_state.get("risk_signals", []), start=1):
            severity = (risk.get("severity") or "").lower()
            if severity == "high":
                points = 35
            elif severity == "medium":
                points = 20
            elif severity == "low":
                points = 10
            else:
                points = 15
            components.append(
                {
                    "name": f"risk_signal_{index}",
                    "category": "risk",
                    "points": points,
                    "detail": risk.get("detail") or "risk signal linked",
                }
            )

        if detail["latest_state"]["coverage_flags"].get("has_risk_factors"):
            components.append(
                {
                    "name": "risk_factor_coverage",
                    "category": "risk",
                    "points": 10,
                    "detail": "structured risk factors are present in parsed evidence",
                }
            )

        score = sum(item["points"] for item in components)
        return min(score, 100), components

    @staticmethod
    def _build_priority_score(
        *,
        opportunity_score: int,
        risk_score: int,
        status: str,
    ) -> tuple[int, list[dict[str, Any]]]:
        opportunity_points = int(opportunity_score * 0.7)
        risk_headroom = max(0, 40 - risk_score)
        risk_buffer_points = int(risk_headroom * 0.3)
        components = [
            {
                "name": "opportunity_weighted",
                "category": "priority",
                "points": opportunity_points,
                "detail": f"70% weighting applied to opportunity score {opportunity_score}",
            },
            {
                "name": "risk_buffer",
                "category": "priority",
                "points": risk_buffer_points,
                "detail": f"30% weighting applied to remaining risk headroom {risk_headroom}",
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

        return min(opportunity_points + risk_buffer_points, 100), components

    @classmethod
    def _priority_level(cls, *, priority_score: int, status: str) -> str:
        if status == "actionable" and priority_score >= 55:
            return "high"
        if priority_score >= 45:
            return "medium"
        return "monitor"

    @staticmethod
    def _why_prioritized(detail: dict[str, Any]) -> list[str]:
        latest_state = detail["latest_state"]
        reasons: list[str] = []

        reasons.extend(latest_state.get("signal_highlights", [])[:2])
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
        priority_score, priority_components = self._build_priority_score(
            opportunity_score=opportunity_score,
            risk_score=risk_score,
            status=latest_state["status"],
        )
        priority_level = self._priority_level(priority_score=priority_score, status=latest_state["status"])

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
            "focus_tags": latest_state.get("focus_tags", []),
            "why_prioritized": self._why_prioritized(detail),
            "recommended_next_step": latest_state.get("recommended_next_step"),
            "recommended_product_themes": self._recommended_product_themes(detail),
            "score_breakdown": {
                "opportunity_components": opportunity_components,
                "risk_components": risk_components,
                "priority_components": priority_components,
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
        return {
            "prospect": self._build_prospect_summary(detail),
            "company": detail["company"],
            "latest_state": detail["latest_state"],
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
        if prospect.get("why_prioritized"):
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
            "top_opportunities": top_opportunities,
            "top_risks": top_risks,
            "evidence_highlights": evidence_highlights,
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
            "suggested_questions": self._suggested_questions(detail),
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
