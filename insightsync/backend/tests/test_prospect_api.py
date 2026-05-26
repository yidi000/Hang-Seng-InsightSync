from __future__ import annotations

from unittest.mock import patch

from insightsync.backend.tests.test_company_api import _test_client


def test_list_prospects_returns_ranked_business_view() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 20
    assert payload["offset"] == 0
    assert len(payload["items"]) == 2

    top = payload["items"][0]
    assert top["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert top["company_id"] == "hkg-alpha-fintech"
    assert top["status"] == "actionable"
    assert top["priority_level"] == "high"
    assert top["priority_score"] >= payload["items"][1]["priority_score"]
    assert top["opportunity_score"] > top["risk_score"]
    assert "growth" in top["focus_tags"]
    assert "cross-border payments" in top["recommended_product_themes"]
    assert top["product_fit"][0]["product_name"] == "cross-border payments"
    assert top["recommended_entry_angles"][0].startswith("Lead with the company event:")
    assert top["recommended_next_step"].startswith("review latest risk factors")
    assert len(top["decision_answers"]) >= 4
    assert top["decision_answers"][0]["question_key"] == "priority"
    assert top["decision_answers"][0]["question"] == "Is this company worth prioritizing now?"
    assert top["evidence_confidence_score"] > 0
    assert top["commercial_attractiveness_score"] > 0
    assert top["immediacy_score"] > 0
    assert top["product_fit_score"] > 0
    assert top["risk_penalty_score"] > 0
    assert len(top["decision_features"]) >= 4
    assert top["decision_features"][0]["feature_label"] is not None
    assert top["decision_features"][0]["business_question"] is not None
    assert top["fusion"]["primary_lens_key"] in {"acquisition", "financing", "cross_border"}
    assert len(top["fusion"]["opportunity_lenses"]) == 3
    assert len(top["why_prioritized"]) >= 2
    assert len(top["score_breakdown"]["opportunity_components"]) >= 1
    assert len(top["score_breakdown"]["risk_components"]) >= 1
    assert len(top["score_breakdown"]["priority_components"]) >= 3
    assert top["score_breakdown"]["scorecard_version"] == "prospect-scorecard-v0.2"
    assert top["score_breakdown"]["calibration_status"] == "expert_defined_unvalidated_v0"
    assert top["score_breakdown"]["llm_score_assignment"] == "not_used_for_final_score"
    assert top["score_breakdown"]["score_inputs"]["priority_score"] == top["priority_score"]
    assert top["score_breakdown"]["score_inputs"]["opportunity_score"] == top["opportunity_score"]
    assert top["score_breakdown"]["score_inputs"]["risk_score"] == top["risk_score"]
    assert top["score_breakdown"]["score_inputs"]["evidence_confidence_score"] == top["evidence_confidence_score"]
    assert top["score_breakdown"]["linkage_quality"]["linked_evidence_count"] >= 1
    assert top["score_breakdown"]["linkage_quality"]["direct_evidence_ratio"] >= 0.5
    assert "priority_score" in top["score_breakdown"]["score_interpretation"]
    assert top["workflow_state"]["stage"] == "new"
    assert top["workflow_state"]["status"] == "open"
    assert top["workflow_state"]["review_status"] == "not_reviewed"


def test_list_prospects_supports_priority_filter() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects?priority_level=high")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["prospect_id"] == "prospect:hkg-alpha-fintech"


def test_compact_prospect_list_uses_official_scorecard() -> None:
    with _test_client() as client:
        compact_response = client.get("/api/prospects?view=compact&limit=100")
        detail_response = client.get("/api/prospects/prospect:hkg-alpha-fintech")

    assert compact_response.status_code == 200
    assert detail_response.status_code == 200
    payload = compact_response.json()
    detail_payload = detail_response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2
    alpha = next(
        item for item in payload["items"] if item["prospect_id"] == "prospect:hkg-alpha-fintech"
    )
    assert alpha["priority_score"] == detail_payload["prospect"]["priority_score"]
    assert alpha["priority_level"] == detail_payload["prospect"]["priority_level"]
    assert alpha["score_breakdown"]["score_inputs"] == detail_payload["prospect"]["score_breakdown"]["score_inputs"]
    assert alpha["score_breakdown"]["scorecard_version"] == "prospect-scorecard-v0.2"
    assert alpha["workflow_state"]["stage"] == "new"


def test_get_prospect_detail_returns_company_backed_detail() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect"]["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["prospect"]["priority_level"] == "high"
    assert payload["prospect"]["recommended_product_themes"][0] == "cross-border payments"
    assert payload["prospect"]["product_fit"][0]["fit_score"] >= 80
    assert len(payload["prospect"]["decision_answers"]) >= 4
    assert payload["prospect"]["decision_answers"][0]["question_key"] == "priority"
    assert any(
        "direct company evidence points to" in item.lower() or "opportunity:" in item.lower()
        for item in payload["prospect"]["why_prioritized"]
    )
    assert payload["prospect"]["score_breakdown"]["priority_components"][0]["name"] == "opportunity_weighted"
    assert payload["prospect"]["score_breakdown"]["priority_components"][1]["name"] == "evidence_confidence_weighted"
    assert payload["prospect"]["score_breakdown"]["priority_components"][2]["name"] == "risk_buffer"
    assert payload["prospect"]["score_breakdown"]["priority_policy"]["opportunity_weight"] == 0.6
    assert payload["prospect"]["score_breakdown"]["linkage_quality"]["scoreable_evidence_count"] >= 1
    assert payload["prospect"]["score_breakdown"]["linkage_quality"]["context_only_count"] == 0
    assert payload["prospect"]["score_breakdown"]["linkage_quality"]["linkage_type_counts"]["direct_company_link"] >= 1
    assert isinstance(payload["prospect"]["score_breakdown"]["governance_flags"], list)
    assert payload["prospect"]["workflow_state"]["stage"] == "new"
    assert payload["workflow_state"]["stage"] == "new"
    assert payload["prospect"]["decision_features"][0]["feature_key"] is not None
    assert payload["prospect"]["fusion"]["primary_lens_key"] in {"acquisition", "financing", "cross_border"}
    assert payload["company"]["company_id"] == "hkg-alpha-fintech"
    assert payload["latest_state"]["status"] == "actionable"
    assert payload["recent_signals"][0]["signal_key"] == "signal-alpha-growth"
    assert payload["recent_documents"][0]["title"] == "Alpha Fintech Annual Report 2025"
    assert payload["key_metrics"][0]["name"] == "revenue_growth"


def test_get_prospect_detail_returns_404_for_unknown_prospect() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:missing-company")

    assert response.status_code == 404
    assert response.json()["detail"] == "Prospect not found"


def test_get_prospect_signals_returns_linked_signals() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech/signals?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["signal_key"] == "signal-alpha-growth"


def test_get_prospect_timeline_returns_linked_events() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["headline"] == "Alpha Fintech expands into UAE"
    assert payload["items"][0]["company_id"] == "hkg-alpha-fintech"


def test_get_prospect_insights_returns_generated_history() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech/insights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 20
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1
    assert payload["items"][0]["title"] == "Engage Alpha Fintech"
    assert payload["items"][0]["insight_type"] == "action"
    assert payload["items"][0]["confidence"] == 0.81


def test_get_prospect_insights_supports_type_filter() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech/insights?insight_type=risk")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []


def test_get_prospect_workflow_returns_default_state() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech/workflow")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["company_id"] == "hkg-alpha-fintech"
    assert payload["owner"] is None
    assert payload["stage"] == "new"
    assert payload["status"] == "open"
    assert payload["review_status"] == "not_reviewed"
    assert payload["updated_at"] is None


def test_put_prospect_workflow_persists_state_and_updates_summary() -> None:
    update = {
        "owner": "RM Team A",
        "stage": "contacted",
        "status": "in_progress",
        "last_action": "Sent introductory email",
        "next_action": "Schedule treasury discovery call",
        "review_status": "reviewed",
        "notes": "Prioritize cross-border payments discussion.",
    }
    with _test_client() as client:
        response = client.put("/api/prospects/prospect:hkg-alpha-fintech/workflow", json=update)
        detail_response = client.get("/api/prospects/prospect:hkg-alpha-fintech")

    assert response.status_code == 200
    payload = response.json()
    assert payload["owner"] == "RM Team A"
    assert payload["stage"] == "contacted"
    assert payload["status"] == "in_progress"
    assert payload["next_action"] == "Schedule treasury discovery call"
    assert payload["review_status"] == "reviewed"
    assert payload["updated_at"] is not None

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["prospect"]["workflow_state"]["owner"] == "RM Team A"
    assert detail["workflow_state"]["stage"] == "contacted"


def test_get_prospect_evidence_returns_parsed_evidence_bundle() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["company_id"] == "hkg-alpha-fintech"
    assert payload["coverage_flags"]["has_parsed_reports"] is True
    assert payload["evidence_summary"]["parsed_document_count"] == 1
    assert payload["recent_documents"][0]["title"] == "Alpha Fintech Annual Report 2025"
    assert payload["recent_documents"][0]["genai_extraction"]["prompt_version"] == "genai-section-extraction-v0.1"
    assert payload["recent_documents"][0]["genai_extraction"]["rejected_reason_counts"] == {
        "duplicate_existing_fact": 1
    }
    assert payload["key_metrics"][0]["name"] == "revenue_growth"
    assert payload["key_risk_factors"][0]["category"] == "regulatory"
    assert payload["key_business_events"][0]["event_type"] == "expansion"


def test_get_prospect_brief_returns_banker_facing_summary() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech/brief")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["priority_level"] == "high"
    assert payload["title"] == "Alpha Fintech Holdings brief"
    assert "high priority" in payload["summary"]
    assert payload["recommended_product_themes"][0] == "cross-border payments"
    assert payload["recommended_entry_angles"][0].startswith("Lead with the company event:")
    assert len(payload["decision_answers"]) >= 4
    assert payload["fusion_explanation"]["primary_lens_key"] in {"acquisition", "financing", "cross_border"}
    assert len(payload["top_opportunities"]) >= 1
    assert len(payload["evidence_highlights"]) >= 1


def test_post_prospect_question_returns_evidence_grounded_answer() -> None:
    fake_result = {
        "answer": "Alpha Fintech shows recent cross-border expansion evidence.",
        "status": "ok",
        "retrieval_run_id": 42,
        "citations": [
            {
                "chunk_id": 1,
                "document_id": 41,
                "score": 0.9,
                "source": "hkex_disclosure",
                "dataset": "annual_report_publication",
                "record_key": "hkex-annual-1",
                "signal_key": "signal-alpha-growth",
                "evidence_url": "https://alpha.example.com/reports/annual-2025.pdf",
                "text": "Alpha Fintech expands into UAE",
            }
        ],
        "structured_insight": {
            "title": "Evidence-grounded summary",
            "summary": "Alpha Fintech shows recent cross-border expansion evidence.",
        },
    }

    with patch(
        "insightsync.backend.services.prospect_service.InsightGenerator.answer_question",
        return_value=fake_result,
    ):
        with _test_client() as client:
            response = client.post(
                "/api/prospects/prospect:hkg-alpha-fintech/question",
                json={"question": "What recent expansion signals does this company have?", "include_chunks": True},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["company_id"] == "hkg-alpha-fintech"
    assert payload["status"] == "ok"
    assert payload["retrieval_run_id"] == 42
    assert payload["citations"][0]["signal_key"] == "signal-alpha-growth"
    assert payload["citations"][0]["text"] == "Alpha Fintech expands into UAE"
    assert payload["structured_insight"]["summary"] == "Alpha Fintech shows recent cross-border expansion evidence."


def test_get_prospect_copilot_returns_workspace_payload() -> None:
    fake_explanation = {
        "status": "fallback",
        "headline": "Alpha Fintech Holdings shows an acquisition-first opportunity",
        "why_now": "Recent company-linked evidence supports timely outreach.",
        "lens_summary": "Client acquisition is the main lens.",
        "risk_note": "Cross-border licensing remains a watch point.",
        "action_note": "Review latest risk factors alongside business signals before RM outreach.",
        "primary_lens_key": "acquisition",
        "recommended_entry_angles": ["Lead with the company event: Alpha Fintech expands into UAE"],
        "recommended_products": ["cross-border payments"],
        "company_id": "hkg-alpha-fintech",
        "prospect_priority": "high",
    }

    with patch(
        "insightsync.backend.services.prospect_service.FusionExplainer.explain",
        return_value=fake_explanation,
    ):
        with _test_client() as client:
            response = client.get("/api/prospects/prospect:hkg-alpha-fintech/copilot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect"]["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["prospect"]["priority_level"] == "high"
    assert payload["brief"]["title"] == "Alpha Fintech Holdings brief"
    assert payload["evidence"]["coverage_flags"]["has_parsed_reports"] is True
    assert payload["evidence"]["key_metrics"][0]["name"] == "revenue_growth"
    assert payload["fusion_explanation"]["headline"] is not None
    assert len(payload["suggested_questions"]) >= 2
    assert "Alpha Fintech Holdings" in payload["suggested_questions"][0]


def test_get_prospect_review_returns_llm_review_payload() -> None:
    fake_review = {
        "status": "fallback",
        "review_summary": "Alpha Fintech review generated in fallback mode.",
        "linkage_reviews": [
            {
                "item_key": "signal_1",
                "title": "Growth signal",
                "evidence_text": "Alpha Fintech expands into UAE",
                "current_linkage_type": "direct_company_link",
                "current_linkage_strength": "strong",
                "suggested_linkage_type": "direct_company_link",
                "suggested_linkage_strength": "strong",
                "review_status": "confirm",
                "confidence": 0.6,
                "reason": "Current linkage is reasonable based on the available structured evidence.",
                "should_affect_scoring": True,
            }
        ],
        "audit_findings": [
            {
                "finding_key": "cross_border_product_overreach",
                "severity": "medium",
                "area": "product_fit",
                "issue": "Cross-border product hypothesis may be too eager.",
                "reason": "Cross-border evidence should be checked carefully.",
                "affected_feature_keys": ["top_product_fit_strength"],
                "suggested_action": "Check direct cross-border evidence before outreach.",
            }
        ],
        "extraction_opportunities": [
            {
                "area": "structured_metrics",
                "why": "More metrics would improve confidence.",
                "suggested_output": "Extract growth, capex, and debt metrics.",
            }
        ],
        "model_name": None,
    }

    with patch(
        "insightsync.backend.services.prospect_service.DecisionReviewService.review",
        return_value=fake_review,
    ):
        with _test_client() as client:
            response = client.get("/api/prospects/prospect:hkg-alpha-fintech/review")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["company_id"] == "hkg-alpha-fintech"
    assert payload["review_summary"] == "Alpha Fintech review generated in fallback mode."
    assert payload["linkage_reviews"][0]["review_status"] == "confirm"
    assert payload["audit_findings"][0]["finding_key"] == "cross_border_product_overreach"
    assert payload["extraction_opportunities"][0]["area"] == "structured_metrics"
