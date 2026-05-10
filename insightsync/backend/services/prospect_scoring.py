from __future__ import annotations

from dataclasses import dataclass


IMPORTANT_SUBTYPES = {"growth", "expansion", "funding", "cross_border", "market_attention"}


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    subtype: str
    title: str | None = None


@dataclass(frozen=True)
class ProspectScoreInput:
    prospect_id: str
    signal_counts: dict[str, int]
    evidence_count: int
    evidence_refs: list[EvidenceRef]
    days_since_last_activity: int | None


def calculate_score(item: ProspectScoreInput) -> float:
    subtype_weights = {
        "funding": 22.0,
        "cross_border": 20.0,
        "expansion": 18.0,
        "growth": 10.0,
        "market_attention": 8.0,
        "policy": 8.0,
        "trade": 12.0,
        "risk": -10.0,
        "hiring": 5.0,
    }
    score = 10.0
    for subtype, count in item.signal_counts.items():
        score += min(count, 5) * subtype_weights.get(subtype, 4.0)
    score += min(item.evidence_count, 10) * 2.0
    if item.days_since_last_activity is not None:
        if item.days_since_last_activity <= 30:
            score += 15.0
        elif item.days_since_last_activity <= 90:
            score += 8.0
        elif item.days_since_last_activity > 365:
            score -= 15.0
    if not item.evidence_refs:
        score = min(score, 39.0)
    return round(max(0.0, min(100.0, score)), 2)


def assign_percentile_tier(ordered_scores: list[tuple[str, float]]) -> dict[str, str]:
    if not ordered_scores:
        return {}
    count = len(ordered_scores)
    a_cutoff = max(1, int(count * 0.15))
    b_cutoff = max(a_cutoff + 1, int(count * 0.45))
    c_cutoff = max(b_cutoff + 1, int(count * 0.80))
    tiers: dict[str, str] = {}
    for idx, (prospect_id, score) in enumerate(ordered_scores):
        if score < 40:
            tiers[prospect_id] = "D"
        elif idx < a_cutoff:
            tiers[prospect_id] = "A"
        elif idx < b_cutoff:
            tiers[prospect_id] = "B"
        elif idx < c_cutoff:
            tiers[prospect_id] = "C"
        else:
            tiers[prospect_id] = "D"
    return tiers


def build_score_reasons(item: ProspectScoreInput) -> list[dict[str, object]]:
    refs_by_subtype: dict[str, list[EvidenceRef]] = {}
    for ref in item.evidence_refs:
        refs_by_subtype.setdefault(ref.subtype, []).append(ref)
    reasons: list[dict[str, object]] = []
    for subtype in ("funding", "cross_border", "expansion", "growth", "market_attention", "policy", "trade"):
        if item.signal_counts.get(subtype, 0) <= 0:
            continue
        refs = refs_by_subtype.get(subtype)
        if not refs:
            continue
        reasons.append(
            {
                "reason": f"{item.signal_counts[subtype]} {subtype.replace('_', ' ')} signal(s)",
                "signal_subtype": subtype,
                "weight": item.signal_counts[subtype],
                "evidence_ids": [ref.evidence_id for ref in refs[:3]],
            }
        )
    return reasons


def recommended_products_for_subtypes(subtypes: set[str]) -> list[str]:
    mapping = {
        "cross_border": ["trade_finance", "cash_management", "cross_border_services"],
        "trade": ["trade_finance", "fx_services"],
        "funding": ["corporate_lending", "capital_markets", "working_capital"],
        "expansion": ["cash_management", "working_capital", "treasury_services"],
        "policy": ["treasury_services", "cross_border_services", "advisory"],
        "growth": ["cash_management", "working_capital"],
        "market_attention": ["capital_markets", "rm_review"],
        "risk": ["risk_review"],
    }
    products: list[str] = []
    for subtype in sorted(subtypes):
        for product in mapping.get(subtype, []):
            if product not in products:
                products.append(product)
    return products[:5]


def entry_angle_for_subtypes(subtypes: set[str], products: list[str]) -> str:
    if "cross_border" in subtypes:
        return "Lead with cross-border cash management and trade finance support backed by recent evidence."
    if "funding" in subtypes:
        return "Lead with financing and working-capital needs evidenced by recent funding signals."
    if "expansion" in subtypes:
        return "Lead with cash management and working capital for expansion plans."
    if "policy" in subtypes:
        return "Lead with a policy-aware treasury and cross-border services review."
    if products:
        return f"Lead with {products[0].replace('_', ' ')} based on cited recent evidence."
    return "Start with a needs-discovery conversation grounded in recent cited evidence."
