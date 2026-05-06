from insightsync.backend.services.prospect_scoring import (
    EvidenceRef,
    ProspectScoreInput,
    assign_percentile_tier,
    build_score_reasons,
    calculate_score,
    recommended_products_for_subtypes,
)


def test_calculate_score_prioritizes_cross_border_funding_and_recency() -> None:
    item = ProspectScoreInput(
        prospect_id="p1",
        signal_counts={"cross_border": 2, "funding": 1, "growth": 5},
        evidence_count=8,
        evidence_refs=[
            EvidenceRef(evidence_id="ev_cross", subtype="cross_border", title="Cross-border expansion"),
            EvidenceRef(evidence_id="ev_fund", subtype="funding", title="Bond issuance"),
        ],
        days_since_last_activity=10,
    )

    score = calculate_score(item)

    assert 65 <= score <= 100


def test_assign_percentile_tier_creates_business_separation() -> None:
    ordered = [
        ("p1", 99.0),
        ("p2", 90.0),
        ("p3", 80.0),
        ("p4", 70.0),
        ("p5", 60.0),
        ("p6", 50.0),
        ("p7", 40.0),
        ("p8", 30.0),
        ("p9", 20.0),
        ("p10", 10.0),
    ]

    tiers = assign_percentile_tier(ordered)

    assert tiers["p1"] == "A"
    assert tiers["p2"] == "B"
    assert tiers["p5"] == "C"
    assert tiers["p10"] == "D"


def test_build_score_reasons_requires_evidence_ids() -> None:
    item = ProspectScoreInput(
        prospect_id="p1",
        signal_counts={"cross_border": 1, "funding": 1},
        evidence_count=2,
        evidence_refs=[
            EvidenceRef(evidence_id="ev1", subtype="cross_border", title="New overseas sales office"),
            EvidenceRef(evidence_id="ev2", subtype="funding", title="New loan facility"),
        ],
        days_since_last_activity=3,
    )

    reasons = build_score_reasons(item)

    assert reasons
    assert all(reason["evidence_ids"] for reason in reasons)
    assert {"trade_finance", "cash_management"} & set(recommended_products_for_subtypes({"cross_border"}))


def test_build_score_reasons_does_not_borrow_unrelated_evidence() -> None:
    item = ProspectScoreInput(
        prospect_id="p1",
        signal_counts={"cross_border": 1, "funding": 1},
        evidence_count=1,
        evidence_refs=[
            EvidenceRef(evidence_id="ev_growth", subtype="growth", title="Revenue growth update"),
        ],
        days_since_last_activity=3,
    )

    reasons = build_score_reasons(item)

    assert {reason["signal_subtype"] for reason in reasons} == set()
