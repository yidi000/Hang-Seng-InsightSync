from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.services.company_service import CompanyService


class ProspectService:
    """Build business-facing prospect views from company-centric state."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReadRepository(db)
        self.company_service = CompanyService(db)

    @staticmethod
    def _prospect_id(company_id: str) -> str:
        return f"prospect:{company_id}"

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
    def _opportunity_score(detail: dict[str, Any]) -> int:
        latest_state = detail["latest_state"]
        coverage_flags = latest_state["coverage_flags"]
        score = 0

        score += min(len(latest_state.get("opportunity_signals", [])) * 20, 40)
        score += min(detail["stats"].get("signal_count", 0) * 5, 15)
        if coverage_flags.get("has_management_discussion"):
            score += 10
        if coverage_flags.get("has_business_events"):
            score += 10
        if coverage_flags.get("has_structured_metrics"):
            score += 10
        if detail["stats"].get("generated_insight_count", 0) > 0:
            score += 15

        return min(score, 100)

    @staticmethod
    def _risk_score(detail: dict[str, Any]) -> int:
        latest_state = detail["latest_state"]
        score = 0

        for risk in latest_state.get("risk_signals", []):
            severity = (risk.get("severity") or "").lower()
            if severity == "high":
                score += 35
            elif severity == "medium":
                score += 20
            elif severity == "low":
                score += 10
            else:
                score += 15

        if detail["latest_state"]["coverage_flags"].get("has_risk_factors"):
            score += 10

        return min(score, 100)

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
        opportunity_score = self._opportunity_score(detail)
        risk_score = self._risk_score(detail)
        priority_score = min(int(opportunity_score * 0.7 + max(0, 40 - risk_score) * 0.3), 100)
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
        company_id = prospect_id.removeprefix("prospect:")
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
