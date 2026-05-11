from __future__ import annotations

from insightsync.backend.workflows.glm_extraction_demo import load_cases, mock_chat_json_for_case, run_case


def test_genai_extraction_eval_cases_pass_with_fixture_outputs() -> None:
    cases = load_cases()
    assert {case["language"] for case in cases} == {"en", "zh-Hans", "zh-Hant", "yue-Hant"}

    for case in cases:
        result = run_case(
            case,
            chat_json=mock_chat_json_for_case(case),
            max_candidates=8,
            include_raw=True,
            api_preview=True,
        )

        assert result["status"] == "ok", case["case_id"]
        assert result["candidate_count"] >= 1, case["case_id"]
        assert result["raw_response"], case["case_id"]
        assert result["api_preview"]["status"] == "ok", case["case_id"]
        assert "accepted_facts" in result["api_preview"], case["case_id"]
        assert "raw_response" not in result["api_preview"], case["case_id"]
        assert result["passed"], result


def test_genai_extraction_eval_keeps_context_facts_out_of_scoring() -> None:
    case = next(item for item in load_cases() if item["case_id"] == "yue_hant_gba_payment_financing")

    result = run_case(
        case,
        chat_json=mock_chat_json_for_case(case),
        max_candidates=8,
    )

    context_facts = [
        fact
        for fact in result["accepted_facts"]
        if fact["fact_type"] in {"management_statement", "opportunity_signal_candidate"}
    ]
    assert context_facts
    assert all(not fact["scoring_eligibility"]["eligible"] for fact in context_facts)
    assert result["eligible_merge_counts"] == {
        "metrics": 0,
        "risk_factors": 2,
        "business_events": 2,
    }
    assert any(
        rejected.get("fact_type") == "metric" and "duplicate_existing_fact" in rejected.get("reasons", [])
        for rejected in result["rejected_facts"]
    )
