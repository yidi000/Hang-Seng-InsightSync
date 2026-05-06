from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from insightsync.backend.repositories.read_repository import ReadRepository


class CompanyService:
    """Assemble company-centric read models from repository data."""

    _OPPORTUNITY_SIGNAL_TYPES = {
        "growth",
        "cross_border",
        "market",
        "financing",
        "expansion",
        "acquisition",
        "m&a",
        "trade",
    }
    _RISK_SIGNAL_TYPES = {
        "risk",
        "regulatory",
        "compliance",
        "warning",
        "litigation",
    }

    def __init__(self, db: Session) -> None:
        self.repo = ReadRepository(db)

    @staticmethod
    def _first_sentence(text: str | None) -> str | None:
        if not text:
            return None
        clean = " ".join(text.split())
        if not clean:
            return None
        for separator in (". ", "; ", "。", "\n"):
            if separator in clean:
                return clean.split(separator, 1)[0].strip()
        return clean

    @staticmethod
    def _activity_at(detail: dict[str, Any]) -> datetime | None:
        timestamps = [
            detail.get("stats", {}).get("last_signal_at"),
            detail.get("stats", {}).get("last_event_at"),
            detail.get("stats", {}).get("last_insight_at"),
            detail.get("evidence_summary", {}).get("last_parsed_at"),
        ]
        values = [ts for ts in timestamps if ts is not None]
        return max(values) if values else None

    @staticmethod
    def _pretty_label(value: str | None) -> str:
        if not value:
            return "unknown"
        return value.replace("_", " ").replace("-", " ").strip()

    @classmethod
    def _build_focus_tags(cls, detail: dict[str, Any]) -> list[str]:
        stats = detail["stats"]
        evidence_summary = detail["evidence_summary"]
        business_events = detail["key_business_events"]
        focus_tags = [
            item["name"]
            for item in stats.get("signal_type_distribution", [])
            if item.get("name")
        ][:3]

        if business_events:
            event_type = business_events[0].get("event_type")
            if event_type and event_type not in focus_tags:
                focus_tags.append(event_type)
        if evidence_summary.get("management_discussion_count", 0) > 0 and "management_discussion" not in focus_tags:
            focus_tags.append("management_discussion")
        if evidence_summary.get("xbrl_hit_count", 0) > 0 and "xbrl" not in focus_tags:
            focus_tags.append("xbrl")
        if evidence_summary.get("risk_factor_count", 0) > 0 and "risk_review" not in focus_tags:
            focus_tags.append("risk_review")
        return focus_tags

    @staticmethod
    def _dedupe_state_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str | None, str]] = set()
        deduped: list[dict[str, Any]] = []
        for item in items:
            key = (item["title"], item.get("detail"), item["source_type"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @classmethod
    def _build_coverage_flags(cls, detail: dict[str, Any]) -> dict[str, bool]:
        stats = detail["stats"]
        evidence_summary = detail["evidence_summary"]
        return {
            "has_recent_signals": stats.get("signal_count", 0) > 0,
            "has_recent_timeline": stats.get("timeline_event_count", 0) > 0,
            "has_generated_insights": stats.get("generated_insight_count", 0) > 0,
            "has_parsed_reports": evidence_summary.get("parsed_document_count", 0) > 0,
            "has_management_discussion": evidence_summary.get("management_discussion_count", 0) > 0,
            "has_structured_metrics": evidence_summary.get("metric_count", 0) > 0,
            "has_risk_factors": evidence_summary.get("risk_factor_count", 0) > 0,
            "has_business_events": evidence_summary.get("business_event_count", 0) > 0,
            "has_ocr_support": evidence_summary.get("ocr_hit_count", 0) > 0,
            "has_xbrl_support": evidence_summary.get("xbrl_hit_count", 0) > 0,
        }

    @classmethod
    def _build_opportunity_signals(cls, detail: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        for signal in detail["recent_signals"]:
            signal_type = signal.get("signal_type")
            if signal_type not in cls._OPPORTUNITY_SIGNAL_TYPES:
                continue
            items.append(
                {
                    "title": f"{cls._pretty_label(signal_type).title()} signal",
                    "detail": cls._first_sentence(
                        signal.get("signal_text") or signal.get("value_text") or signal.get("indicator")
                    ),
                    "source_type": "trigger_signal",
                    "signal_type": signal_type,
                    "severity": None,
                    "confidence": signal.get("signal_score"),
                }
            )

        for event in detail["key_business_events"]:
            event_type = event.get("event_type")
            items.append(
                {
                    "title": f"{cls._pretty_label(event_type).title()} event",
                    "detail": cls._first_sentence(event.get("summary")),
                    "source_type": "parsed_business_event",
                    "signal_type": event_type,
                    "severity": None,
                    "confidence": event.get("confidence"),
                }
            )

        top_document = detail["recent_documents"][0] if detail["recent_documents"] else None
        if top_document and top_document.get("management_discussion_summary"):
            items.append(
                {
                    "title": "Management discussion takeaway",
                    "detail": cls._first_sentence(top_document.get("management_discussion_summary")),
                    "source_type": "parsed_document",
                    "signal_type": "management_discussion",
                    "severity": None,
                    "confidence": None,
                }
            )

        return cls._dedupe_state_items(items)[:4]

    @classmethod
    def _build_risk_signals(cls, detail: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        for signal in detail["recent_signals"]:
            signal_type = signal.get("signal_type")
            if signal_type not in cls._RISK_SIGNAL_TYPES:
                continue
            items.append(
                {
                    "title": f"{cls._pretty_label(signal_type).title()} signal",
                    "detail": cls._first_sentence(
                        signal.get("signal_text") or signal.get("value_text") or signal.get("indicator")
                    ),
                    "source_type": "trigger_signal",
                    "signal_type": signal_type,
                    "severity": signal.get("signal_level"),
                    "confidence": signal.get("signal_score"),
                }
            )

        for risk in detail["key_risk_factors"]:
            items.append(
                {
                    "title": f"{cls._pretty_label(risk.get('category')).title()} risk",
                    "detail": cls._first_sentence(risk.get("description")),
                    "source_type": "parsed_risk_factor",
                    "signal_type": risk.get("category"),
                    "severity": risk.get("severity"),
                    "confidence": risk.get("confidence"),
                }
            )

        return cls._dedupe_state_items(items)[:4]

    @classmethod
    def _build_signal_highlights(
        cls,
        detail: dict[str, Any],
        coverage_flags: dict[str, bool],
    ) -> list[str]:
        stats = detail["stats"]
        evidence_summary = detail["evidence_summary"]
        highlights: list[str] = []

        signal_types = [
            item["name"]
            for item in stats.get("signal_type_distribution", [])
            if item.get("name")
        ]
        if stats.get("signal_count", 0) > 0:
            if signal_types:
                highlights.append(
                    f"{stats['signal_count']} recent signals linked, led by {', '.join(signal_types[:3])}"
                )
            else:
                highlights.append(f"{stats['signal_count']} recent signals linked to the company")

        if coverage_flags["has_parsed_reports"]:
            doc_parts: list[str] = [f"{evidence_summary['parsed_document_count']} parsed documents"]
            if coverage_flags["has_management_discussion"]:
                doc_parts.append(f"{evidence_summary['management_discussion_count']} with management discussion")
            if coverage_flags["has_ocr_support"]:
                doc_parts.append("OCR support hit")
            if coverage_flags["has_xbrl_support"]:
                doc_parts.append("XBRL support hit")
            highlights.append(", ".join(doc_parts))

        structured_parts: list[str] = []
        if coverage_flags["has_structured_metrics"]:
            structured_parts.append(f"{evidence_summary['metric_count']} metrics")
        if coverage_flags["has_risk_factors"]:
            structured_parts.append(f"{evidence_summary['risk_factor_count']} risk factors")
        if coverage_flags["has_business_events"]:
            structured_parts.append(f"{evidence_summary['business_event_count']} business events")
        if structured_parts:
            highlights.append(f"Structured extraction captured {', '.join(structured_parts)}")

        return highlights

    @classmethod
    def _build_state_summary(
        cls,
        detail: dict[str, Any],
        coverage_flags: dict[str, bool],
        status: str,
    ) -> str | None:
        stats = detail["stats"]
        evidence_summary = detail["evidence_summary"]
        parts: list[str] = []

        if stats.get("signal_count", 0) > 0:
            parts.append(f"{stats['signal_count']} recent signals")
        if evidence_summary.get("parsed_document_count", 0) > 0:
            parts.append(f"{evidence_summary['parsed_document_count']} parsed documents")
        if stats.get("generated_insight_count", 0) > 0:
            parts.append(f"{stats['generated_insight_count']} generated insights")

        if status == "actionable":
            prefix = "Company has enough linked evidence for immediate RM follow-up"
        elif status == "active":
            prefix = "Company has recent linked evidence worth review"
        else:
            prefix = "Company currently has limited linked evidence"

        if not parts and not any(coverage_flags.values()):
            return prefix
        if parts:
            return f"{prefix}: {', '.join(parts)}."
        return prefix

    @classmethod
    def _build_why_now(
        cls,
        detail: dict[str, Any],
        opportunity_signals: list[dict[str, Any]],
        risk_signals: list[dict[str, Any]],
    ) -> str | None:
        why_parts: list[str] = []

        if opportunity_signals:
            top_opportunity = opportunity_signals[0]
            if top_opportunity.get("detail"):
                why_parts.append(f"opportunity: {top_opportunity['detail']}")
        if risk_signals:
            top_risk = risk_signals[0]
            if top_risk.get("detail"):
                why_parts.append(f"risk watch: {top_risk['detail']}")

        recent_documents = detail["recent_documents"]
        if recent_documents:
            top_doc = recent_documents[0]
            if top_doc.get("management_discussion_summary"):
                why_parts.append(
                    f"latest report takeaway: {cls._first_sentence(top_doc.get('management_discussion_summary'))}"
                )
            elif top_doc.get("title"):
                why_parts.append(f"latest parsed document: {top_doc['title']}")

        return "; ".join(why_parts) if why_parts else None

    @classmethod
    def _derive_status(
        cls,
        detail: dict[str, Any],
        coverage_flags: dict[str, bool],
        opportunity_signals: list[dict[str, Any]],
        risk_signals: list[dict[str, Any]],
    ) -> str:
        stats = detail["stats"]
        status = "monitor"
        if (
            coverage_flags["has_recent_signals"]
            or coverage_flags["has_parsed_reports"]
            or coverage_flags["has_recent_timeline"]
        ):
            status = "active"
        if (
            coverage_flags["has_generated_insights"]
            or len(opportunity_signals) >= 2
            or len(risk_signals) >= 2
            or stats.get("generated_insight_count", 0) > 0
        ):
            status = "actionable"
        return status

    @classmethod
    def _recommended_next_step(
        cls,
        focus_tags: list[str],
        coverage_flags: dict[str, bool],
        risk_signals: list[dict[str, Any]],
    ) -> str:
        if risk_signals:
            severities = {item.get("severity") for item in risk_signals if item.get("severity")}
            if "high" in severities:
                return "review high-severity risks before outreach and decide whether escalation is required"
            return "review latest risk factors alongside business signals before RM outreach"
        if "cross_border" in focus_tags:
            return "review cross-border exposure and map treasury, payments, or trade-finance follow-up"
        if "growth" in focus_tags or "expansion" in focus_tags:
            return "validate growth momentum with parsed report evidence and prepare acquisition outreach"
        if coverage_flags["has_parsed_reports"]:
            return "review parsed report evidence and prepare RM follow-up"
        return "review linked evidence and prepare RM follow-up"

    def _build_latest_state(self, detail: dict[str, Any]) -> dict[str, Any]:
        evidence_summary = detail["evidence_summary"]
        coverage_flags = self._build_coverage_flags(detail)
        focus_tags = self._build_focus_tags(detail)
        opportunity_signals = self._build_opportunity_signals(detail)
        risk_signals = self._build_risk_signals(detail)
        status = self._derive_status(detail, coverage_flags, opportunity_signals, risk_signals)

        return {
            "activity_at": self._activity_at(detail),
            "status": status,
            "state_summary": self._build_state_summary(detail, coverage_flags, status),
            "why_now": self._build_why_now(detail, opportunity_signals, risk_signals),
            "recommended_next_step": self._recommended_next_step(focus_tags, coverage_flags, risk_signals),
            "focus_tags": focus_tags,
            "signal_highlights": self._build_signal_highlights(detail, coverage_flags),
            "opportunity_signals": opportunity_signals,
            "risk_signals": risk_signals,
            "coverage_flags": coverage_flags,
            "evidence_summary": evidence_summary,
        }

    def get_company_detail(self, company_id: str) -> dict[str, Any] | None:
        detail = self.repo.get_company_detail(company_id)
        if not detail:
            return None
        detail["latest_state"] = self._build_latest_state(detail)
        return detail
