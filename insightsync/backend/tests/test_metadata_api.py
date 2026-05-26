from __future__ import annotations

from unittest.mock import patch

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


def test_metadata_filters_avoid_heavy_company_list() -> None:
    with _test_client() as client:
        with patch(
            "insightsync.backend.repositories.read_repository.ReadRepository.list_companies",
            side_effect=AssertionError("metadata filters should not hydrate the company list"),
        ):
            response = client.get("/api/metadata/filters")

    assert response.status_code == 200
    assert response.json()["regions"][0]["name"] == "Hong Kong"
