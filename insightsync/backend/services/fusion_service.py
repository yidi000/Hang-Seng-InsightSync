from __future__ import annotations

from typing import Any


class FusionService:
    """Build structured fusion output from linked evidence, features, and score layers."""

    _LENS_LABELS = {
        "acquisition": "Client Acquisition",
        "financing": "Financing Need",
        "cross_border": "Cross-border Opportunity",
    }
    _LENS_PRODUCTS = {
        "acquisition": {"working capital", "cash management", "capital markets", "cross-border payments"},
        "financing": {"working capital", "term loan", "cash management"},
        "cross_border": {"cross-border payments", "trade finance", "treasury"},
    }

    @staticmethod
    def _clamp_score(value: float) -> int:
        return max(0, min(int(round(value)), 100))

    @staticmethod
    def _dedupe_texts(items: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    @classmethod
    def _evidence_texts(cls, items: list[dict[str, Any]], *, max_items: int = 3) -> list[str]:
        texts = cls._dedupe_texts(
            [item.get("detail") or item.get("title") for item in items if item.get("detail") or item.get("title")]
        )
        return texts[:max_items]

    @staticmethod
    def _first_text(items: list[dict[str, Any]]) -> str | None:
        for item in items:
            text = item.get("detail") or item.get("title")
            if text:
                return text
        return None

    @staticmethod
    def _feature_keys(features: list[dict[str, Any]], group: str | None = None) -> list[str]:
        keys = []
        for feature in features:
            if group and feature.get("feature_group") != group:
                continue
            key = feature.get("feature_key")
            if key and key not in keys:
                keys.append(key)
        return keys

    @classmethod
    def _recommended_products(cls, product_fit: list[dict[str, Any]], lens_key: str) -> list[str]:
        allowed = cls._LENS_PRODUCTS[lens_key]
        products = [item["product_name"] for item in product_fit if item.get("product_name") in allowed]
        return products[:3]

    @staticmethod
    def _top_product_name(product_fit: list[dict[str, Any]]) -> str | None:
        return product_fit[0]["product_name"] if product_fit else None

    @classmethod
    def _context_alignment(cls, context_signals: list[dict[str, Any]]) -> str | None:
        if not context_signals:
            return None
        top_context = context_signals[0]
        detail = top_context.get("detail")
        if not detail:
            return None

        linkage_type = top_context.get("linkage_type")
        if linkage_type == "direct_company_link":
            return f"Directly linked context reinforces the company evidence: {detail}"
        if linkage_type == "cross_border_exposure_link":
            return f"Cross-border context supports the overseas angle: {detail}"
        if linkage_type == "region_link":
            return f"Regional context supports timing and relevance: {detail}"
        if linkage_type == "industry_link":
            return f"Industry context supports the commercial case: {detail}"
        return f"Macro context provides background support: {detail}"

    @classmethod
    def _build_reasoning_steps(
        cls,
        *,
        opportunity_signals: list[dict[str, Any]],
        context_signals: list[dict[str, Any]],
        risk_signals: list[dict[str, Any]],
        product_fit: list[dict[str, Any]],
        decision_features: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []

        opportunity_evidence = cls._evidence_texts(opportunity_signals)
        if opportunity_evidence:
            steps.append(
                {
                    "step_key": "company_evidence",
                    "title": "Company Evidence",
                    "summary": "Direct company-linked activity creates the primary commercial hypothesis.",
                    "feature_keys": cls._feature_keys(decision_features, "commercial_attractiveness")
                    + cls._feature_keys(decision_features, "immediacy"),
                    "linkage_types": cls._dedupe_texts(
                        [item.get("linkage_type") for item in opportunity_signals if item.get("linkage_type")]
                    )[:3],
                    "evidence_items": opportunity_evidence,
                }
            )

        context_evidence = cls._evidence_texts(context_signals)
        if context_evidence:
            steps.append(
                {
                    "step_key": "context_linkage",
                    "title": "Context Linkage",
                    "summary": "External context is linked explicitly before it is allowed to support the company case.",
                    "feature_keys": cls._feature_keys(decision_features, "evidence_confidence"),
                    "linkage_types": cls._dedupe_texts(
                        [item.get("linkage_type") for item in context_signals if item.get("linkage_type")]
                    )[:3],
                    "evidence_items": context_evidence,
                }
            )

        if product_fit:
            steps.append(
                {
                    "step_key": "product_match",
                    "title": "Product Match",
                    "summary": f"Current evidence most strongly aligns with {product_fit[0]['product_name']} as the first banking angle.",
                    "feature_keys": cls._feature_keys(decision_features, "product_fit"),
                    "linkage_types": [],
                    "evidence_items": cls._dedupe_texts(product_fit[0].get("supporting_signals", []))[:3],
                }
            )

        risk_evidence = cls._evidence_texts(risk_signals)
        if risk_evidence:
            steps.append(
                {
                    "step_key": "risk_constraint",
                    "title": "Risk Constraint",
                    "summary": "Risk evidence does not cancel the opportunity, but it should constrain outreach and framing.",
                    "feature_keys": cls._feature_keys(decision_features, "risk_penalty"),
                    "linkage_types": cls._dedupe_texts(
                        [item.get("linkage_type") for item in risk_signals if item.get("linkage_type")]
                    )[:3],
                    "evidence_items": risk_evidence,
                }
            )

        return steps

    @classmethod
    def _build_opportunity_lenses(
        cls,
        *,
        opportunity_signals: list[dict[str, Any]],
        context_signals: list[dict[str, Any]],
        risk_signals: list[dict[str, Any]],
        product_fit: list[dict[str, Any]],
        commercial_attractiveness_score: int,
        immediacy_score: int,
        product_fit_score: int,
        risk_penalty_score: int,
        evidence_confidence_score: int,
    ) -> list[dict[str, Any]]:
        financing_evidence = [
            item for item in opportunity_signals if item.get("signal_type") in {"financing", "growth", "expansion"}
        ]
        cross_border_evidence = [
            item
            for item in [*opportunity_signals, *context_signals]
            if item.get("signal_type") in {"cross_border", "trade"}
            or item.get("linkage_type") == "cross_border_exposure_link"
        ]
        acquisition_evidence = [
            item
            for item in opportunity_signals
            if item.get("signal_type") in {"growth", "expansion", "acquisition", "m&a", "management_discussion", "market"}
        ]
        acquisition_products = cls._recommended_products(product_fit, "acquisition")
        financing_products = cls._recommended_products(product_fit, "financing")
        cross_border_products = cls._recommended_products(product_fit, "cross_border")

        acquisition_score = cls._clamp_score(
            commercial_attractiveness_score
            + immediacy_score * 0.8
            + min(evidence_confidence_score / 4, 20)
            - risk_penalty_score / 3
            + (8 if acquisition_products else 0)
        )
        financing_score = cls._clamp_score(
            product_fit_score * 1.2
            + immediacy_score * 0.6
            + len(financing_evidence) * 6
            + evidence_confidence_score / 5
            - risk_penalty_score / 3
            + (6 if financing_products else 0)
        )
        if cross_border_evidence or cross_border_products:
            cross_border_score = cls._clamp_score(
                len(cross_border_evidence) * 18
                + (18 if cross_border_products else 0)
                + immediacy_score * 0.5
                + evidence_confidence_score / 5
                - risk_penalty_score / 4
            )
        else:
            cross_border_score = 0

        lenses = [
            {
                "lens_key": "acquisition",
                "label": cls._LENS_LABELS["acquisition"],
                "lens_score": acquisition_score,
                "rationale": "Direct commercial activity and current timing support proactive new-client outreach.",
                "supporting_evidence": cls._evidence_texts(acquisition_evidence),
                "recommended_products": acquisition_products,
            },
            {
                "lens_key": "financing",
                "label": cls._LENS_LABELS["financing"],
                "lens_score": financing_score,
                "rationale": "Growth, expansion, and product-fit evidence suggest near-term financing or liquidity needs may be emerging.",
                "supporting_evidence": cls._evidence_texts(financing_evidence or opportunity_signals),
                "recommended_products": financing_products,
            },
            {
                "lens_key": "cross_border",
                "label": cls._LENS_LABELS["cross_border"],
                "lens_score": cross_border_score,
                "rationale": "Cross-border or trade-linked evidence suggests transaction banking and corridor opportunities.",
                "supporting_evidence": cls._evidence_texts(cross_border_evidence or context_signals),
                "recommended_products": cross_border_products,
            },
        ]
        return sorted(lenses, key=lambda item: (item["lens_score"], item["lens_key"]), reverse=True)

    @classmethod
    def _build_entry_angles(
        cls,
        *,
        primary_lens_key: str | None,
        primary_opportunity: str | None,
        context_alignment: str | None,
        key_risk: str | None,
        product_fit: list[dict[str, Any]],
    ) -> list[str]:
        angles: list[str] = []
        top_product = cls._top_product_name(product_fit)

        if primary_opportunity:
            angles.append(f"Lead with the company event: {primary_opportunity}")
        if primary_lens_key == "cross_border" and top_product:
            angles.append(f"Position the discussion around cross-border execution needs, starting with {top_product}.")
        elif primary_lens_key == "financing" and top_product:
            angles.append(f"Anchor the conversation on near-term funding or liquidity planning, starting with {top_product}.")
        elif primary_lens_key == "acquisition":
            angles.append("Open with the current growth window and frame the outreach around why this company merits attention now.")

        if context_alignment:
            angles.append(context_alignment)
        if key_risk:
            angles.append(f"Keep the pitch evidence-led and acknowledge the main caution point: {key_risk}")
        return cls._dedupe_texts(angles)[:4]

    @classmethod
    def _build_next_step(
        cls,
        *,
        primary_lens_key: str | None,
        risk_signals: list[dict[str, Any]],
        product_fit: list[dict[str, Any]],
    ) -> str:
        if risk_signals:
            severities = {item.get("severity") for item in risk_signals if item.get("severity")}
            if "high" in severities:
                return "review high-severity risks before outreach and decide whether escalation is required"
            return "review latest risk factors alongside business signals before RM outreach"

        top_product = cls._top_product_name(product_fit)
        if primary_lens_key == "cross_border" and top_product:
            return f"prepare RM outreach anchored on {top_product} and validate the cross-border evidence path"
        if primary_lens_key == "financing" and top_product:
            return f"prepare financing-focused outreach anchored on {top_product} and confirm timing through recent filings"
        if primary_lens_key == "acquisition" and top_product:
            return f"prepare acquisition outreach anchored on {top_product} and validate the supporting evidence"
        if top_product:
            return f"prepare RM outreach anchored on {top_product} and validate the supporting evidence"
        return "review linked evidence and prepare RM follow-up"

    @classmethod
    def _build_decision_answers(
        cls,
        *,
        company_name: str | None,
        company_status: str | None,
        primary_lens_key: str | None,
        primary_opportunity: str | None,
        context_alignment: str | None,
        key_risk: str | None,
        product_fit: list[dict[str, Any]],
        why_now: str | None,
        recommended_next_step: str | None,
        evidence_confidence_score: int,
    ) -> list[dict[str, Any]]:
        display_name = company_name or "This company"
        top_product = cls._top_product_name(product_fit)
        primary_lens_label = cls._LENS_LABELS.get(primary_lens_key or "", "structured opportunity")

        answers: list[dict[str, Any]] = [
            {
                "question_key": "priority",
                "question": "这家公司值不值得优先跟进？",
                "answer": f"{display_name} 目前是 {company_status or 'monitor'}，当前证据主要指向 {primary_lens_label.lower()}。",
                "supporting_evidence": cls._dedupe_texts([primary_opportunity] if primary_opportunity else []),
            },
            {
                "question_key": "why_now",
                "question": "为什么是现在？",
                "answer": why_now or "当前证据还不够强，暂时不建议立即行动。",
                "supporting_evidence": cls._dedupe_texts([why_now] if why_now else []),
            },
            {
                "question_key": "entry_angle",
                "question": "最适合从什么业务切入？",
                "answer": recommended_next_step
                or (
                    f"先从 {top_product} 切入。"
                    if top_product
                    else "先从最强的证据切入，再验证商业需求。"
                ),
                "supporting_evidence": cls._dedupe_texts([top_product] if top_product else []),
            },
            {
                "question_key": "risk_watch",
                "question": "有哪些风险或不确定性要先知道？",
                "answer": key_risk or "当前没有明显的高风险信号，但证据还不完整。",
                "supporting_evidence": cls._dedupe_texts([key_risk] if key_risk else []),
            },
        ]
        if context_alignment:
            answers.append(
                {
                    "question_key": "context",
                    "question": "外部环境提供了什么背景？",
                    "answer": context_alignment,
                    "supporting_evidence": cls._dedupe_texts([context_alignment]),
                }
            )
        answers.append(
            {
                "question_key": "confidence",
                "question": "这套判断有多可靠？",
                "answer": f"当前证据可信度是 {evidence_confidence_score}/100，所以这更像一个起点，不是最终结论。",
                "supporting_evidence": [],
            }
        )
        return answers

    @classmethod
    def build_company_fusion(
        cls,
        *,
        company_name: str | None = None,
        company_status: str | None = None,
        opportunity_signals: list[dict[str, Any]],
        context_signals: list[dict[str, Any]],
        risk_signals: list[dict[str, Any]],
        product_fit: list[dict[str, Any]],
        decision_features: list[dict[str, Any]],
        commercial_attractiveness_score: int,
        immediacy_score: int,
        product_fit_score: int,
        risk_penalty_score: int,
        evidence_confidence_score: int,
    ) -> dict[str, Any]:
        primary_opportunity = cls._first_text(opportunity_signals)
        key_risk = cls._first_text(risk_signals)
        context_alignment = cls._context_alignment(context_signals)
        opportunity_lenses = cls._build_opportunity_lenses(
            opportunity_signals=opportunity_signals,
            context_signals=context_signals,
            risk_signals=risk_signals,
            product_fit=product_fit,
            commercial_attractiveness_score=commercial_attractiveness_score,
            immediacy_score=immediacy_score,
            product_fit_score=product_fit_score,
            risk_penalty_score=risk_penalty_score,
            evidence_confidence_score=evidence_confidence_score,
        )
        primary_lens_key = opportunity_lenses[0]["lens_key"] if opportunity_lenses else None
        top_product = cls._top_product_name(product_fit)

        why_parts = []
        if primary_opportunity:
            why_parts.append(f"opportunity: {primary_opportunity}")
        if context_alignment:
            why_parts.append(f"context: {context_alignment}")
        if key_risk:
            why_parts.append(f"risk watch: {key_risk}")
        why_now = "; ".join(why_parts) if why_parts else None

        summary_parts = []
        if primary_opportunity:
            summary_parts.append(f"Direct company evidence points to {primary_opportunity}")
        if primary_lens_key:
            summary_parts.append(f"the strongest current lens is {cls._LENS_LABELS[primary_lens_key].lower()}")
        if top_product:
            summary_parts.append(f"with {top_product} as the leading product hypothesis")
        if context_alignment:
            summary_parts.append(context_alignment.lower())
        if key_risk:
            summary_parts.append(f"while keeping in view that {key_risk.lower()}")
        summary = "; ".join(summary_parts) if summary_parts else None

        return {
            "why_now": why_now,
            "summary": summary,
            "primary_lens_key": primary_lens_key,
            "primary_opportunity": primary_opportunity,
            "context_alignment": context_alignment,
            "key_risk": key_risk,
            "reasoning_steps": cls._build_reasoning_steps(
                opportunity_signals=opportunity_signals,
                context_signals=context_signals,
                risk_signals=risk_signals,
                product_fit=product_fit,
                decision_features=decision_features,
            ),
            "opportunity_lenses": opportunity_lenses,
            "decision_answers": cls._build_decision_answers(
                company_name=company_name,
                company_status=company_status,
                primary_lens_key=primary_lens_key,
                primary_opportunity=primary_opportunity,
                context_alignment=context_alignment,
                key_risk=key_risk,
                product_fit=product_fit,
                why_now=why_now,
                recommended_next_step=cls._build_next_step(
                    primary_lens_key=primary_lens_key,
                    risk_signals=risk_signals,
                    product_fit=product_fit,
                ),
                evidence_confidence_score=evidence_confidence_score,
            ),
            "recommended_entry_angles": cls._build_entry_angles(
                primary_lens_key=primary_lens_key,
                primary_opportunity=primary_opportunity,
                context_alignment=context_alignment,
                key_risk=key_risk,
                product_fit=product_fit,
            ),
            "recommended_next_step": cls._build_next_step(
                primary_lens_key=primary_lens_key,
                risk_signals=risk_signals,
                product_fit=product_fit,
            ),
        }
