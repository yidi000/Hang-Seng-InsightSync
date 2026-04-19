from fastapi.testclient import TestClient

from insightsync.backend.main import app


def test_healthz() -> None:
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_signal_limit_validation() -> None:
    client = TestClient(app)

    response = client.get("/api/signals?limit=0")

    assert response.status_code == 422
