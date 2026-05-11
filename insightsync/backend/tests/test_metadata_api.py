from __future__ import annotations

from insightsync.backend.tests.test_company_api import _test_client


def test_metadata_filters_returns_available_options() -> None:
    with _test_client() as client:
        response = client.get("/api/metadata/filters")

    assert response.status_code == 200
    payload = response.json()
    assert payload["regions"][0]["name"] == "Hong Kong"
    assert payload["regions"][0]["count"] == 2
    assert any(item["name"] == "fintech" for item in payload["segments"])
    assert any(item["name"] == "Payments" for item in payload["industries"])
    assert any(item["name"] == "growth" for item in payload["signal_types"])
    assert any(item["name"] == "investhk_news" for item in payload["sources"])
    assert any(item["name"] == "news_signals" for item in payload["datasets"])
