from __future__ import annotations

from insightsync.backend.tests.test_company_api import _test_client


def test_get_signal_returns_single_trigger_signal() -> None:
    with _test_client() as client:
        response = client.get("/api/signals/11")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 11
    assert payload["company_id"] == "hkg-alpha-fintech"
    assert payload["signal_type"] == "growth"
    assert payload["signal_text"] == "Alpha Fintech expands into UAE"
    assert payload["evidence_refs"] == ["https://alpha.example.com/news"]
    assert payload["extra"] == {"language": "en"}


def test_get_signal_returns_404_for_missing_signal() -> None:
    with _test_client() as client:
        response = client.get("/api/signals/99999")

    assert response.status_code == 404
