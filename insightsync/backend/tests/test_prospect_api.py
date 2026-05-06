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
    assert top["recommended_next_step"].startswith("review latest risk factors")
    assert len(top["why_prioritized"]) >= 2
    assert len(top["score_breakdown"]["opportunity_components"]) >= 1
    assert len(top["score_breakdown"]["risk_components"]) >= 1
    assert len(top["score_breakdown"]["priority_components"]) >= 2


def test_list_prospects_supports_priority_filter() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects?priority_level=high")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["prospect_id"] == "prospect:hkg-alpha-fintech"


def test_get_prospect_detail_returns_company_backed_detail() -> None:
    with _test_client() as client:
        response = client.get("/api/prospects/prospect:hkg-alpha-fintech")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect"]["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert payload["prospect"]["priority_level"] == "high"
    assert payload["prospect"]["recommended_product_themes"][0] == "cross-border payments"
    assert payload["prospect"]["score_breakdown"]["priority_components"][0]["name"] == "opportunity_weighted"
    assert payload["prospect"]["score_breakdown"]["priority_components"][1]["name"] == "risk_buffer"
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
