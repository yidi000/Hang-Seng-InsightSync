from __future__ import annotations

from typing import Any

LINKAGE_TAXONOMY: dict[str, dict[str, Any]] = {
    "direct_company_link": {
        "label": "Direct company link",
        "description": "Evidence explicitly names or uniquely identifies the company.",
        "default_strength": "strong",
        "supports_company_scoring": True,
        "context_only": False,
    },
    "industry_link": {
        "label": "Industry link",
        "description": "Evidence is relevant through the company's industry or sector exposure.",
        "default_strength": "medium",
        "supports_company_scoring": True,
        "context_only": False,
    },
    "region_link": {
        "label": "Region link",
        "description": "Evidence is relevant through the company's operating geography.",
        "default_strength": "medium",
        "supports_company_scoring": True,
        "context_only": False,
    },
    "cross_border_exposure_link": {
        "label": "Cross-border exposure link",
        "description": "Evidence is relevant through the company's overseas, treasury, or trade corridor exposure.",
        "default_strength": "medium",
        "supports_company_scoring": True,
        "context_only": False,
    },
    "macro_context_link": {
        "label": "Macro context link",
        "description": "Evidence provides market background context but is not company-specific.",
        "default_strength": "weak",
        "supports_company_scoring": False,
        "context_only": True,
    },
}

FEATURE_DICTIONARY: dict[str, dict[str, Any]] = {
    "growth_activity_intensity": {
        "label": "Growth activity intensity",
        "feature_group": "commercial_attractiveness",
        "description": "How much direct growth or expansion activity is visible for the company.",
        "business_question": "Is this company worth prioritizing now?",
        "preferred_linkage_types": ["direct_company_link", "industry_link"],
        "max_score_contribution": 24,
    },
    "market_visibility": {
        "label": "Market visibility",
        "feature_group": "commercial_attractiveness",
        "description": "How observable the company is across linked market signals.",
        "business_question": "Is this company worth prioritizing now?",
        "preferred_linkage_types": ["direct_company_link", "industry_link", "region_link"],
        "max_score_contribution": 12,
    },
    "business_event_specificity": {
        "label": "Business event specificity",
        "feature_group": "commercial_attractiveness",
        "description": "Whether specific structured company events exist to support outreach.",
        "business_question": "Is this company worth prioritizing now?",
        "preferred_linkage_types": ["direct_company_link"],
        "max_score_contribution": 10,
    },
    "recent_activity_momentum": {
        "label": "Recent activity momentum",
        "feature_group": "immediacy",
        "description": "Whether the linked evidence indicates a timely reason to act now.",
        "business_question": "Why now?",
        "preferred_linkage_types": ["direct_company_link", "industry_link", "region_link"],
        "max_score_contribution": 12,
    },
    "management_update_availability": {
        "label": "Management update availability",
        "feature_group": "immediacy",
        "description": "Whether current management commentary is available to guide outreach timing.",
        "business_question": "Why now?",
        "preferred_linkage_types": ["direct_company_link"],
        "max_score_contribution": 10,
    },
    "top_product_fit_strength": {
        "label": "Top product fit strength",
        "feature_group": "product_fit",
        "description": "How strong the best current product angle appears to be.",
        "business_question": "What is the best business entry angle?",
        "preferred_linkage_types": ["direct_company_link", "cross_border_exposure_link"],
        "max_score_contribution": 15,
    },
    "cross_border_operating_exposure": {
        "label": "Cross-border operating exposure",
        "feature_group": "product_fit",
        "description": "Whether cross-border or trade evidence supports transaction-banking relevance.",
        "business_question": "What is the best business entry angle?",
        "preferred_linkage_types": ["direct_company_link", "cross_border_exposure_link"],
        "max_score_contribution": 18,
    },
    "linked_risk_severity": {
        "label": "Linked risk severity",
        "feature_group": "risk_penalty",
        "description": "How much linked risk evidence should reduce outreach priority.",
        "business_question": "What risks or uncertainties should be surfaced before action?",
        "preferred_linkage_types": ["direct_company_link", "industry_link", "region_link"],
        "max_score_contribution": 35,
    },
    "structured_risk_coverage": {
        "label": "Structured risk coverage",
        "feature_group": "risk_penalty",
        "description": "Whether structured risk extraction indicates a need for explicit caution.",
        "business_question": "What risks or uncertainties should be surfaced before action?",
        "preferred_linkage_types": ["direct_company_link"],
        "max_score_contribution": 10,
    },
    "direct_evidence_ratio": {
        "label": "Direct evidence ratio",
        "feature_group": "evidence_confidence",
        "description": "How much of the evidence is directly linked to the company.",
        "business_question": "How reliable is the current view?",
        "preferred_linkage_types": ["direct_company_link"],
        "max_score_contribution": 30,
    },
    "structured_evidence_coverage": {
        "label": "Structured evidence coverage",
        "feature_group": "evidence_confidence",
        "description": "How complete the structured extraction coverage is for this company.",
        "business_question": "How reliable is the current view?",
        "preferred_linkage_types": [
            "direct_company_link",
            "industry_link",
            "region_link",
            "cross_border_exposure_link",
        ],
        "max_score_contribution": 25,
    },
    "source_diversity": {
        "label": "Source diversity",
        "feature_group": "evidence_confidence",
        "description": "How many independent sources support the current story.",
        "business_question": "How reliable is the current view?",
        "preferred_linkage_types": [
            "direct_company_link",
            "industry_link",
            "region_link",
            "cross_border_exposure_link",
            "macro_context_link",
        ],
        "max_score_contribution": 15,
    },
}

FEATURE_GROUP_CAPS: dict[str, int] = {
    "commercial_attractiveness": 40,
    "immediacy": 25,
    "product_fit": 35,
    "risk_penalty": 100,
    "evidence_confidence": 100,
}

PRIORITY_SCORE_POLICY: dict[str, float | int] = {
    "opportunity_weight": 0.60,
    "evidence_confidence_weight": 0.15,
    "risk_buffer_weight": 0.25,
    "risk_headroom_cap": 40,
    "high_priority_threshold": 50,
    "medium_priority_threshold": 38,
}

PRODUCT_FIT_CATALOG: dict[str, dict[str, Any]] = {
    "cross-border payments": {
        "fit_score": 88,
        "rationale": "Cross-border signals and regional context suggest transaction banking demand.",
        "trigger_signal_types": ["cross_border", "trade"],
        "trigger_linkage_types": ["cross_border_exposure_link"],
    },
    "trade finance": {
        "fit_score": 80,
        "rationale": "Cross-border expansion and market context indicate trade or settlement needs.",
        "trigger_signal_types": ["cross_border", "trade"],
        "trigger_linkage_types": ["cross_border_exposure_link"],
    },
    "treasury": {
        "fit_score": 78,
        "rationale": "Cross-border activity and market exposure suggest FX and liquidity management needs.",
        "trigger_signal_types": ["cross_border", "trade"],
        "trigger_linkage_types": ["cross_border_exposure_link"],
    },
    "working capital": {
        "fit_score": 76,
        "rationale": "Growth and expansion signals suggest near-term funding and liquidity demand.",
        "trigger_signal_types": ["growth", "expansion", "financing", "management_discussion"],
        "trigger_linkage_types": [],
    },
    "term loan": {
        "fit_score": 73,
        "rationale": "Expansion or capex-style signals point to medium-term financing needs.",
        "trigger_signal_types": ["financing", "expansion", "acquisition", "m&a"],
        "trigger_linkage_types": [],
    },
    "cash management": {
        "fit_score": 72,
        "rationale": "Business growth and operating complexity suggest daily cash management needs.",
        "trigger_signal_types": ["growth", "expansion", "financing", "cross_border", "management_discussion"],
        "trigger_linkage_types": ["cross_border_exposure_link"],
    },
    "capital markets": {
        "fit_score": 68,
        "rationale": "Market-facing evidence suggests possible capital markets relevance.",
        "trigger_signal_types": ["market", "acquisition", "m&a"],
        "trigger_linkage_types": [],
    },
    "risk review": {
        "fit_score": 64,
        "rationale": "Risk signals suggest a defensive advisory and review conversation is needed.",
        "requires_risk": True,
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
        "linkage_label": definition["label"],
        "linkage_strength": linkage_strength or definition["default_strength"],
        "linkage_rationale": linkage_rationale or definition["description"],
        "supports_company_scoring": definition["supports_company_scoring"],
        "context_only": definition["context_only"],
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
        "feature_label": definition["label"],
        "feature_group": definition["feature_group"],
        "feature_description": definition["description"],
        "business_question": definition["business_question"],
        "preferred_linkage_types": definition["preferred_linkage_types"],
        "max_score_contribution": definition["max_score_contribution"],
        "value_num": value_num,
        "score_contribution": score_contribution,
        "rationale": rationale,
        "evidence_items": evidence_items,
    }


def linkage_supports_company_scoring(linkage_type: str | None) -> bool:
    if not linkage_type:
        return True
    definition = LINKAGE_TAXONOMY.get(linkage_type)
    if not definition:
        return True
    return bool(definition["supports_company_scoring"])


def feature_definition(feature_key: str) -> dict[str, Any]:
    return FEATURE_DICTIONARY[feature_key]


def feature_cap(feature_key: str) -> int:
    return int(FEATURE_DICTIONARY[feature_key]["max_score_contribution"])


def priority_score_policy() -> dict[str, float | int]:
    return dict(PRIORITY_SCORE_POLICY)


def score_feature_groups(features: list[dict[str, Any]]) -> dict[str, int]:
    scores: dict[str, int] = {key: 0 for key in FEATURE_GROUP_CAPS}
    for feature in features:
        group = feature["feature_group"]
        if group not in scores:
            continue
        scores[group] += int(feature.get("score_contribution", 0))
    return {key: min(value, FEATURE_GROUP_CAPS[key]) for key, value in scores.items()}
