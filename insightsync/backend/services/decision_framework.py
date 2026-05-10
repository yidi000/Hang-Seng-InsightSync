from __future__ import annotations

from typing import Any

LINKAGE_TAXONOMY: dict[str, dict[str, Any]] = {
    "direct_company_link": {
        "description": "Evidence explicitly names or uniquely identifies the company.",
        "default_strength": "strong",
    },
    "industry_link": {
        "description": "Evidence is relevant through the company's industry or sector exposure.",
        "default_strength": "medium",
    },
    "region_link": {
        "description": "Evidence is relevant through the company's operating geography.",
        "default_strength": "medium",
    },
    "cross_border_exposure_link": {
        "description": "Evidence is relevant through the company's overseas, treasury, or trade corridor exposure.",
        "default_strength": "medium",
    },
    "macro_context_link": {
        "description": "Evidence provides market background context but is not company-specific.",
        "default_strength": "weak",
    },
}

FEATURE_DICTIONARY: dict[str, dict[str, Any]] = {
    "growth_activity_intensity": {
        "feature_group": "commercial_attractiveness",
        "description": "How much direct growth or expansion activity is visible for the company.",
    },
    "market_visibility": {
        "feature_group": "commercial_attractiveness",
        "description": "How observable the company is across linked market signals.",
    },
    "business_event_specificity": {
        "feature_group": "commercial_attractiveness",
        "description": "Whether specific structured company events exist to support outreach.",
    },
    "recent_activity_momentum": {
        "feature_group": "immediacy",
        "description": "Whether the linked evidence indicates a timely reason to act now.",
    },
    "management_update_availability": {
        "feature_group": "immediacy",
        "description": "Whether current management commentary is available to guide outreach timing.",
    },
    "top_product_fit_strength": {
        "feature_group": "product_fit",
        "description": "How strong the best current product angle appears to be.",
    },
    "cross_border_operating_exposure": {
        "feature_group": "product_fit",
        "description": "Whether cross-border or trade evidence supports transaction-banking relevance.",
    },
    "linked_risk_severity": {
        "feature_group": "risk_penalty",
        "description": "How much linked risk evidence should reduce outreach priority.",
    },
    "structured_risk_coverage": {
        "feature_group": "risk_penalty",
        "description": "Whether structured risk extraction indicates a need for explicit caution.",
    },
    "direct_evidence_ratio": {
        "feature_group": "evidence_confidence",
        "description": "How much of the evidence is directly linked to the company.",
    },
    "structured_evidence_coverage": {
        "feature_group": "evidence_confidence",
        "description": "How complete the structured extraction coverage is for this company.",
    },
    "source_diversity": {
        "feature_group": "evidence_confidence",
        "description": "How many independent sources support the current story.",
    },
}

FEATURE_GROUP_CAPS: dict[str, int] = {
    "commercial_attractiveness": 40,
    "immediacy": 25,
    "product_fit": 35,
    "risk_penalty": 100,
    "evidence_confidence": 100,
}

PRODUCT_FIT_CATALOG: dict[str, dict[str, Any]] = {
    "cross-border payments": {
        "fit_score": 88,
        "rationale": "Cross-border signals and regional context suggest transaction banking demand.",
    },
    "trade finance": {
        "fit_score": 80,
        "rationale": "Cross-border expansion and market context indicate trade or settlement needs.",
    },
    "treasury": {
        "fit_score": 78,
        "rationale": "Cross-border activity and market exposure suggest FX and liquidity management needs.",
    },
    "working capital": {
        "fit_score": 76,
        "rationale": "Growth and expansion signals suggest near-term funding and liquidity demand.",
    },
    "term loan": {
        "fit_score": 73,
        "rationale": "Expansion or capex-style signals point to medium-term financing needs.",
    },
    "cash management": {
        "fit_score": 72,
        "rationale": "Business growth and operating complexity suggest daily cash management needs.",
    },
    "capital markets": {
        "fit_score": 68,
        "rationale": "Market-facing evidence suggests possible capital markets relevance.",
    },
    "risk review": {
        "fit_score": 64,
        "rationale": "Risk signals suggest a defensive advisory and review conversation is needed.",
    },
}


def build_linkage(
    linkage_type: str,
    *,
    linkage_strength: str | None = None,
    linkage_rationale: str | None = None,
) -> dict[str, str]:
    definition = LINKAGE_TAXONOMY[linkage_type]
    return {
        "linkage_type": linkage_type,
        "linkage_strength": linkage_strength or definition["default_strength"],
        "linkage_rationale": linkage_rationale or definition["description"],
    }


def build_feature(
    *,
    feature_key: str,
    value_num: float | None,
    score_contribution: int,
    rationale: str,
    evidence_items: list[str],
) -> dict[str, Any]:
    definition = FEATURE_DICTIONARY[feature_key]
    return {
        "feature_key": feature_key,
        "feature_group": definition["feature_group"],
        "value_num": value_num,
        "score_contribution": score_contribution,
        "rationale": rationale,
        "evidence_items": evidence_items,
    }
