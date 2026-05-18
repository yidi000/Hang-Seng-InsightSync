from __future__ import annotations

from unittest.mock import patch

from insightsync.backend.tests.test_company_api import _test_client


def test_dashboard_summary_returns_homepage_cards() -> None:
    with _test_client() as client:
        response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["lead_pool"] == 2
    assert payload["high_priority"] == 1
    assert payload["cross_border"] == 1
    assert payload["financing_signals"] >= 1
    assert payload["last_updated"] is not None


def test_dashboard_priority_prospects_returns_compact_cards() -> None:
    with _test_client() as client:
        response = client.get("/api/dashboard/priority-prospects")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2

    top = payload["items"][0]
    assert top["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert top["display_name"] == "Alpha Fintech Holdings"
    assert top["priority_level"] == "high"
    assert top["priority_score"] >= payload["items"][1]["priority_score"]
    assert "growth" in top["focus_tags"]
    assert len(top["why_prioritized"]) >= 1


def test_dashboard_trigger_signals_returns_homepage_cards() -> None:
    with _test_client() as client:
        response = client.get("/api/dashboard/trigger-signals")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) >= 3

    top = payload["items"][0]
    assert top["signal_id"] == 11
    assert top["company_id"] == "hkg-alpha-fintech"
    assert top["prospect_id"] == "prospect:hkg-alpha-fintech"
    assert top["signal_type"] == "growth"
    assert "growth" in top["focus_tags"]
    assert "Alpha Fintech expands into UAE" in top["title"]


def test_dashboard_market_overview_returns_industry_and_region_breakdowns() -> None:
    with _test_client() as client:
        response = client.get("/api/dashboard/market-overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["industry_breakdown"][0]["name"] in {"Banking", "Payments"}
    assert payload["industry_breakdown"][0]["count"] >= 1
    assert payload["region_breakdown"][0]["name"] == "Hong Kong"
    assert payload["region_breakdown"][0]["count"] == 2
    assert payload["company_size_breakdown"] == []


def test_dashboard_summary_and_market_overview_avoid_full_prospect_list() -> None:
    with _test_client() as client:
        with patch(
            "insightsync.backend.api.dashboard.ProspectService.list_prospects",
            side_effect=AssertionError("full prospect list should not run for dashboard rollups"),
        ):
            summary_response = client.get("/api/dashboard/summary")
            market_response = client.get("/api/dashboard/market-overview")

    assert summary_response.status_code == 200
    assert market_response.status_code == 200
