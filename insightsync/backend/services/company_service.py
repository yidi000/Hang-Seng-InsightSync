from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.services.decision_framework import (
    FEATURE_GROUP_CAPS,
    PRODUCT_FIT_CATALOG,
    build_feature,
    build_linkage,
)
from insightsync.backend.services.fusion_service import FusionService


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
    _CONTEXT_SIGNAL_TYPES = {
        "market",
        "cross_border",
        "trade",
        "policy",
        "macro",
        "financing",
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
        seen: set[tuple[str, str | None, str, str | None, str | None]] = set()
        deduped: list[dict[str, Any]] = []
        for item in items:
            key = (
                item["title"],
                item.get("detail"),
                item["source_type"],
                item.get("linkage_type"),
                item.get("linkage_strength"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _linkage_from_signal(signal: dict[str, Any], detail: dict[str, Any]) -> dict[str, str]:
        company_id = detail["company"].get("company_id")
        signal_company_id = signal.get("company_id")
        signal_type = (signal.get("signal_type") or "").lower()

        if signal_company_id and signal_company_id == company_id:
            return build_linkage(
                "direct_company_link",
                linkage_rationale="Signal is directly mapped to the company.",
            )
        if signal_type in {"cross_border", "trade"} and signal.get("entity"):
            return build_linkage(
                "cross_border_exposure_link",
                linkage_rationale="Signal matches the company's regional or cross-border operating context.",
            )
        if signal.get("entity") and detail["company"].get("region") == "Hong Kong":
            return build_linkage(
                "region_link",
                linkage_rationale="Signal matches the company's regional market context.",
            )
        if signal_type in {"market", "policy", "macro"}:
            return build_linkage(
                "macro_context_link",
                linkage_rationale="Signal provides market background but is not company-specific.",
            )
        return build_linkage(
            "industry_link",
            linkage_rationale="Signal is treated as linked sector context.",
        )

    @staticmethod
    def _linkage_from_document(dataset: str | None, detail: dict[str, Any]) -> dict[str, str]:
        company = detail["company"]
        if company.get("company_id") and dataset:
            return build_linkage(
                "direct_company_link",
                linkage_rationale=f"Parsed company document is linked through dataset {dataset}.",
            )
        return build_linkage(
            "direct_company_link",
            linkage_rationale="Parsed company document belongs to the company.",
        )

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
            linkage = cls._linkage_from_signal(signal, detail)
            items.append(
                {
                    "title": f"{cls._pretty_label(signal_type).title()} signal",
                    "detail": cls._first_sentence(
                        signal.get("signal_text") or signal.get("value_text") or signal.get("indicator")
                    ),
                    "source_type": "trigger_signal",
                    "source": signal.get("source"),
                    "signal_type": signal_type,
                    "severity": None,
                    "confidence": signal.get("signal_score"),
                    **linkage,
                }
            )

        for event in detail["key_business_events"]:
            event_type = event.get("event_type")
            linkage = build_linkage(
                "direct_company_link",
                linkage_rationale="Structured business event comes from a document linked to the company.",
            )
            items.append(
                {
                    "title": f"{cls._pretty_label(event_type).title()} event",
                    "detail": cls._first_sentence(event.get("summary")),
                    "source_type": "parsed_business_event",
                    "source": "parsed_documents",
                    "signal_type": event_type,
                    "severity": None,
                    "confidence": event.get("confidence"),
                    **linkage,
                }
            )

        top_document = detail["recent_documents"][0] if detail["recent_documents"] else None
        if top_document and top_document.get("management_discussion_summary"):
            linkage = cls._linkage_from_document(top_document.get("dataset"), detail)
            items.append(
                {
                    "title": "Management discussion takeaway",
                    "detail": cls._first_sentence(top_document.get("management_discussion_summary")),
                    "source_type": "parsed_document",
                    "source": top_document.get("source"),
                    "signal_type": "management_discussion",
                    "severity": None,
                    "confidence": None,
                    **linkage,
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
            linkage = cls._linkage_from_signal(signal, detail)
            items.append(
                {
                    "title": f"{cls._pretty_label(signal_type).title()} signal",
                    "detail": cls._first_sentence(
                        signal.get("signal_text") or signal.get("value_text") or signal.get("indicator")
                    ),
                    "source_type": "trigger_signal",
                    "source": signal.get("source"),
                    "signal_type": signal_type,
                    "severity": signal.get("signal_level"),
                    "confidence": signal.get("signal_score"),
                    **linkage,
                }
            )

        for risk in detail["key_risk_factors"]:
            linkage = build_linkage(
                "direct_company_link",
                linkage_rationale="Structured risk factor comes from a document linked to the company.",
            )
            items.append(
                {
                    "title": f"{cls._pretty_label(risk.get('category')).title()} risk",
                    "detail": cls._first_sentence(risk.get("description")),
                    "source_type": "parsed_risk_factor",
                    "source": "parsed_documents",
                    "signal_type": risk.get("category"),
                    "severity": risk.get("severity"),
                    "confidence": risk.get("confidence"),
                    **linkage,
                }
            )

        return cls._dedupe_state_items(items)[:4]

    @classmethod
    def _build_context_signals(cls, detail: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        for signal in detail["recent_signals"]:
            signal_type = signal.get("signal_type")
            if signal_type not in cls._CONTEXT_SIGNAL_TYPES:
                continue
            linkage = cls._linkage_from_signal(signal, detail)
            items.append(
                {
                    "title": f"{cls._pretty_label(signal_type).title()} context",
                    "detail": cls._first_sentence(
                        signal.get("signal_text") or signal.get("value_text") or signal.get("indicator")
                    ),
                    "source_type": "market_signal",
                    "source": signal.get("source"),
                    "signal_type": signal_type,
                    "severity": signal.get("signal_level"),
                    "confidence": signal.get("signal_score"),
                    **linkage,
                }
            )

        top_document = detail["recent_documents"][0] if detail["recent_documents"] else None
        if top_document and top_document.get("management_discussion_summary"):
            linkage = cls._linkage_from_document(top_document.get("dataset"), detail)
            items.append(
                {
                    "title": "Company context from latest report",
                    "detail": cls._first_sentence(top_document.get("management_discussion_summary")),
                    "source_type": "parsed_document",
                    "source": top_document.get("source"),
                    "signal_type": "company_context",
                    "severity": None,
                    "confidence": None,
                    **linkage,
                }
            )

        return cls._dedupe_state_items(items)[:5]

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
    def _build_product_fit(
        cls,
        detail: dict[str, Any],
        focus_tags: list[str],
        opportunity_signals: list[dict[str, Any]],
        context_signals: list[dict[str, Any]],
        risk_signals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []

        signal_texts = [
            item.get("detail")
            for item in [*opportunity_signals, *context_signals, *risk_signals]
            if item.get("detail")
        ]

        def append_product(product_name: str) -> None:
            definition = PRODUCT_FIT_CATALOG[product_name]
            products.append(
                {
                    "product_name": product_name,
                    "fit_score": definition["fit_score"],
                    "rationale": definition["rationale"],
                    "supporting_signals": signal_texts[:2],
                }
            )

        if "cross_border" in focus_tags:
            for key in ("cross-border payments", "trade finance", "treasury"):
                append_product(key)
        if "growth" in focus_tags or "expansion" in focus_tags or "financing" in focus_tags:
            for key in ("working capital", "term loan", "cash management"):
                append_product(key)
        if "market" in focus_tags:
            append_product("capital markets")
        if risk_signals:
            append_product("risk review")

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for product in sorted(products, key=lambda item: (-item["fit_score"], item["product_name"])):
            if product["product_name"] in seen:
                continue
            seen.add(product["product_name"])
            deduped.append(product)
        return deduped[:4]

    @staticmethod
    def _evidence_items(items: list[dict[str, Any]], *, max_items: int = 3) -> list[str]:
        evidence_items: list[str] = []
        for item in items:
            text = item.get("detail") or item.get("title")
            if not text or text in evidence_items:
                continue
            evidence_items.append(text)
            if len(evidence_items) >= max_items:
                break
        return evidence_items

    @staticmethod
    def _feature(
        *,
        feature_key: str,
        feature_group: str,
        value_num: float | None,
        score_contribution: int,
        rationale: str,
        evidence_items: list[str],
    ) -> dict[str, Any]:
        feature = build_feature(
            feature_key=feature_key,
            value_num=value_num,
            score_contribution=score_contribution,
            rationale=rationale,
            evidence_items=evidence_items,
        )
        if feature["feature_group"] != feature_group:
            raise ValueError(
                f"Feature group mismatch for {feature_key}: expected {feature['feature_group']}, got {feature_group}"
            )
        return feature

    @classmethod
    def _build_decision_features(
        cls,
        detail: dict[str, Any],
        coverage_flags: dict[str, bool],
        opportunity_signals: list[dict[str, Any]],
        risk_signals: list[dict[str, Any]],
        context_signals: list[dict[str, Any]],
        product_fit: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        features: list[dict[str, Any]] = []

        growth_like = [
            item
            for item in opportunity_signals
            if item.get("signal_type") in {"growth", "expansion", "acquisition", "m&a", "management_discussion"}
        ]
        if growth_like:
            features.append(
                cls._feature(
                    feature_key="growth_activity_intensity",
                    feature_group="commercial_attractiveness",
                    value_num=float(len(growth_like)),
                    score_contribution=min(len(growth_like) * 12, 24),
                    rationale="Company-linked growth or expansion evidence suggests commercial upside.",
                    evidence_items=cls._evidence_items(growth_like),
                )
            )

        signal_count = detail["stats"].get("signal_count", 0)
        if signal_count > 0:
            features.append(
                cls._feature(
                    feature_key="market_visibility",
                    feature_group="commercial_attractiveness",
                    value_num=float(signal_count),
                    score_contribution=min(signal_count * 4, 12),
                    rationale="More linked signals increase the company’s observable market activity.",
                    evidence_items=cls._evidence_items(opportunity_signals or context_signals),
                )
            )

        business_event_count = len(detail.get("key_business_events", []))
        if business_event_count > 0:
            features.append(
                cls._feature(
                    feature_key="business_event_specificity",
                    feature_group="commercial_attractiveness",
                    value_num=float(business_event_count),
                    score_contribution=min(business_event_count * 10, 10),
                    rationale="Structured company events increase commercial specificity and outreach relevance.",
                    evidence_items=cls._evidence_items(detail["key_business_events"]),
                )
            )

        activity_momentum = signal_count + detail["stats"].get("timeline_event_count", 0)
        if activity_momentum > 0:
            features.append(
                cls._feature(
                    feature_key="recent_activity_momentum",
                    feature_group="immediacy",
                    value_num=float(activity_momentum),
                    score_contribution=min(activity_momentum * 4, 12),
                    rationale="Recent company-linked activity suggests there is a timely reason to review now.",
                    evidence_items=cls._evidence_items(opportunity_signals or context_signals),
                )
            )

        if coverage_flags.get("has_management_discussion"):
            mgmt_items = [
                item for item in opportunity_signals if item.get("signal_type") == "management_discussion"
            ] or [
                item for item in context_signals if item.get("signal_type") == "company_context"
            ]
            features.append(
                cls._feature(
                    feature_key="management_update_availability",
                    feature_group="immediacy",
                    value_num=1.0,
                    score_contribution=10,
                    rationale="Management commentary provides current strategic context for banker outreach.",
                    evidence_items=cls._evidence_items(mgmt_items),
                )
            )

        if product_fit:
            top_product = product_fit[0]
            features.append(
                cls._feature(
                    feature_key="top_product_fit_strength",
                    feature_group="product_fit",
                    value_num=float(top_product.get("fit_score", 0)),
                    score_contribution=min(max(int(top_product.get("fit_score", 0) / 10), 0), 15),
                    rationale=f"Top product fit is {top_product.get('product_name')}, indicating a plausible first banking angle.",
                    evidence_items=top_product.get("supporting_signals", [])[:3],
                )
            )

        cross_border_items = [
            item
            for item in [*opportunity_signals, *context_signals]
            if item.get("signal_type") in {"cross_border", "trade"}
            or item.get("linkage_type") == "cross_border_exposure_link"
        ]
        if cross_border_items:
            features.append(
                cls._feature(
                    feature_key="cross_border_operating_exposure",
                    feature_group="product_fit",
                    value_num=float(len(cross_border_items)),
                    score_contribution=min(len(cross_border_items) * 6, 18),
                    rationale="Cross-border or trade-linked evidence suggests transaction banking and corridor relevance.",
                    evidence_items=cls._evidence_items(cross_border_items),
                )
            )

        if risk_signals:
            severity_penalty = {"high": 35, "medium": 20, "low": 10}
            highest_penalty = max(
                severity_penalty.get((item.get("severity") or "").lower(), 15) for item in risk_signals
            )
            features.append(
                cls._feature(
                    feature_key="linked_risk_severity",
                    feature_group="risk_penalty",
                    value_num=float(len(risk_signals)),
                    score_contribution=highest_penalty,
                    rationale="Linked risk evidence should reduce or constrain outreach priority.",
                    evidence_items=cls._evidence_items(risk_signals),
                )
            )

        if coverage_flags.get("has_risk_factors"):
            features.append(
                cls._feature(
                    feature_key="structured_risk_coverage",
                    feature_group="risk_penalty",
                    value_num=float(detail["evidence_summary"].get("risk_factor_count", 0)),
                    score_contribution=10,
                    rationale="Structured risk factor coverage indicates the recommendation should include explicit caution.",
                    evidence_items=cls._evidence_items(detail.get("key_risk_factors", [])),
                )
            )

        linked_items = [*opportunity_signals, *risk_signals, *context_signals]
        if linked_items:
            direct_count = sum(1 for item in linked_items if item.get("linkage_type") == "direct_company_link")
            direct_ratio = direct_count / len(linked_items)
            if direct_ratio >= 0.75:
                confidence_points = 30
            elif direct_ratio >= 0.5:
                confidence_points = 22
            else:
                confidence_points = 12
            features.append(
                cls._feature(
                    feature_key="direct_evidence_ratio",
                    feature_group="evidence_confidence",
                    value_num=round(direct_ratio, 2),
                    score_contribution=confidence_points,
                    rationale="A higher share of direct company-linked evidence increases trust in the recommendation.",
                    evidence_items=cls._evidence_items(linked_items),
                )
            )

        structured_coverage_count = sum(
            int(coverage_flags.get(flag, False))
            for flag in (
                "has_parsed_reports",
                "has_management_discussion",
                "has_structured_metrics",
                "has_business_events",
                "has_risk_factors",
            )
        )
        if structured_coverage_count > 0:
            features.append(
                cls._feature(
                    feature_key="structured_evidence_coverage",
                    feature_group="evidence_confidence",
                    value_num=float(structured_coverage_count),
                    score_contribution=min(structured_coverage_count * 5, 25),
                    rationale="Broader structured extraction coverage makes the company view more reliable.",
                    evidence_items=[
                        item
                        for item in (
                            "parsed report",
                            "management discussion",
                            "structured metrics",
                            "business events",
                            "risk factors",
                        )
                        if item
                    ][:structured_coverage_count],
                )
            )

        unique_sources = len(
            {
                item.get("source")
                for item in [*opportunity_signals, *risk_signals, *context_signals]
                if item.get("source")
            }
        )
        if unique_sources > 0:
            features.append(
                cls._feature(
                    feature_key="source_diversity",
                    feature_group="evidence_confidence",
                    value_num=float(unique_sources),
                    score_contribution=min(unique_sources * 5, 15),
                    rationale="Multiple independent sources reduce single-source bias in the recommendation.",
                    evidence_items=sorted(
                        {
                            item.get("source")
                            for item in [*opportunity_signals, *risk_signals, *context_signals]
                            if item.get("source")
                        }
                    )[:3],
                )
            )

        return features

    @staticmethod
    def _score_feature_groups(features: list[dict[str, Any]]) -> dict[str, int]:
        caps = {
            "commercial_attractiveness": 40,
            "immediacy": 25,
            "product_fit": 35,
            "risk_penalty": 100,
            "evidence_confidence": 100,
        }
        scores: dict[str, int] = {key: 0 for key in caps}
        for feature in features:
            group = feature["feature_group"]
            if group not in scores:
                continue
            scores[group] += int(feature.get("score_contribution", 0))
        return {key: min(value, caps[key]) for key, value in scores.items()}

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

    def _build_latest_state(self, detail: dict[str, Any]) -> dict[str, Any]:
        evidence_summary = detail["evidence_summary"]
        coverage_flags = self._build_coverage_flags(detail)
        focus_tags = self._build_focus_tags(detail)
        opportunity_signals = self._build_opportunity_signals(detail)
        risk_signals = self._build_risk_signals(detail)
        context_signals = self._build_context_signals(detail)
        product_fit = self._build_product_fit(detail, focus_tags, opportunity_signals, context_signals, risk_signals)
        decision_features = self._build_decision_features(
            detail,
            coverage_flags,
            opportunity_signals,
            risk_signals,
            context_signals,
            product_fit,
        )
        feature_scores = self._score_feature_groups(decision_features)
        status = self._derive_status(detail, coverage_flags, opportunity_signals, risk_signals)
        fusion = FusionService.build_company_fusion(
            company_name=detail["company"].get("display_name") or detail["company"].get("canonical_name"),
            company_status=status,
            opportunity_signals=opportunity_signals,
            context_signals=context_signals,
            risk_signals=risk_signals,
            product_fit=product_fit,
            decision_features=decision_features,
            commercial_attractiveness_score=feature_scores["commercial_attractiveness"],
            immediacy_score=feature_scores["immediacy"],
            product_fit_score=feature_scores["product_fit"],
            risk_penalty_score=feature_scores["risk_penalty"],
            evidence_confidence_score=feature_scores["evidence_confidence"],
        )

        return {
            "activity_at": self._activity_at(detail),
            "status": status,
            "state_summary": self._build_state_summary(detail, coverage_flags, status),
            "why_now": fusion.get("why_now"),
            "fusion_summary": fusion.get("summary"),
            "fusion": fusion,
            "recommended_next_step": fusion.get("recommended_next_step"),
            "commercial_attractiveness_score": feature_scores["commercial_attractiveness"],
            "immediacy_score": feature_scores["immediacy"],
            "product_fit_score": feature_scores["product_fit"],
            "risk_penalty_score": feature_scores["risk_penalty"],
            "evidence_confidence_score": feature_scores["evidence_confidence"],
            "focus_tags": focus_tags,
            "signal_highlights": self._build_signal_highlights(detail, coverage_flags),
            "opportunity_signals": opportunity_signals,
            "risk_signals": risk_signals,
            "context_signals": context_signals,
            "product_fit": product_fit,
            "recommended_entry_angles": fusion.get("recommended_entry_angles", []),
            "decision_features": decision_features,
            "decision_answers": fusion.get("decision_answers", []),
            "coverage_flags": coverage_flags,
            "evidence_summary": evidence_summary,
        }

    def get_company_detail(self, company_id: str) -> dict[str, Any] | None:
        detail = self.repo.get_company_detail(company_id)
        if not detail:
            return None
        detail["latest_state"] = self._build_latest_state(detail)
        return detail
