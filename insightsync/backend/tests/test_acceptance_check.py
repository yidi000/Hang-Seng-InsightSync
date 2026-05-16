from __future__ import annotations

from typing import Any

from insightsync.backend.workflows import acceptance_check


def test_acceptance_check_validates_core_prospect_contract(monkeypatch) -> None:
    calls: list[str] = []

    def fake_get_json(base: str, path: str, timeout: float) -> dict[str, Any]:
        calls.append(path)
        if path == "/api/prospects?limit=5":
            return {
                "items": [
                    {
                        "prospect_id": "prospect:alpha",
                        "company_id": "alpha",
                        "priority_level": "high",
                        "priority_score": 72,
                        "opportunity_score": 84,
                        "risk_score": 15,
                        "evidence_confidence_score": 70,
                        "decision_answers": [{"question_key": "priority", "answer": "yes"}],
                        "workflow_state": {"stage": "new"},
                        "score_breakdown": {
                            "scorecard_version": "prospect-scorecard-v0.2",
                            "calibration_status": "expert_defined_unvalidated_v0",
                            "llm_score_assignment": "not_used_for_final_score",
                            "score_inputs": {
                                "priority_score": 72,
                                "opportunity_score": 84,
                                "risk_score": 15,
                                "evidence_confidence_score": 70,
                            },
                            "linkage_quality": {"direct_evidence_ratio": 1.0},
                            "governance_flags": [],
                        },
                    }
                ]
            }
        if path == "/api/prospects/prospect%3Aalpha":
            return {
                "prospect": {
                    "prospect_id": "prospect:alpha",
                    "company_id": "alpha",
                    "decision_answers": [{"question_key": "priority", "answer": "yes"}],
                },
                "workflow_state": {"stage": "new"},
                "company": {"company_id": "alpha"},
                "latest_state": {
                    "status": "actionable",
                    "coverage_flags": {},
                    "decision_answers": [],
                },
                "recent_signals": [],
                "recent_timeline": [],
                "recent_insights": [],
                "recent_documents": [],
            }
        if path == "/api/prospects/prospect%3Aalpha/evidence":
            return {"coverage_flags": {}, "evidence_summary": {"parsed_document_count": 1}}
        if path == "/api/prospects/prospect%3Aalpha/brief":
            return {"summary": "Alpha brief", "decision_answers": []}
        if path == "/api/prospects/prospect%3Aalpha/copilot":
            return {"suggested_questions": ["Why now?"]}
        raise AssertionError(path)

    monkeypatch.setattr(acceptance_check, "_get_json", fake_get_json)

    context: dict[str, Any] = {}
    list_result = acceptance_check._check_prospect_list("http://test", 1.0, context)
    detail_result = acceptance_check._check_prospect_detail("http://test", 1.0, context)
    workspace_result = acceptance_check._check_prospect_workspace("http://test", 1.0, context)

    assert list_result["passed"] is True
    assert detail_result["passed"] is True
    assert workspace_result["passed"] is True
    assert context["prospect_id"] == "prospect:alpha"
    assert "/api/prospects/prospect%3Aalpha/brief" in calls
