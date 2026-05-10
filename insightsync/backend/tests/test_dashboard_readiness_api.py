from __future__ import annotations

from sqlalchemy.sql.elements import TextClause
from fastapi.testclient import TestClient

from insightsync.backend.api.dashboard import _evidence_ids, _product_fit, _score_reason_items
from insightsync.backend.main import app
from insightsync.backend.repositories.read_repository import ReadRepository


def test_priority_prospects_include_score_reasons_and_evidence_ids(monkeypatch) -> None:
    def priority_prospects(self: ReadRepository, *, limit: int = 10) -> list[dict]:
        return [
            {
                "prospect_id": "prospect-alpha",
                "display_name": "Alpha Limited",
                "score": 91.5,
                "tier": "A",
                "industry": "Fintech",
                "region": "Hong Kong",
                "recommended_products": ["Cash management"],
                "recommended_entry_angle": "Open with expansion financing.",
                "score_reasons": [
                    {
                        "reason": "Recent funding event",
                        "signal_subtype": "funding",
                        "evidence_ids": ["ev-funding-1"],
                    }
                ],
                "score_inputs": {
                    "evidence_refs": [
                        {"evidence_id": "ev-funding-1"},
                        {"evidence_id": "ev-cross-border-1"},
                    ]
                },
            }
        ][:limit]

    monkeypatch.setattr(ReadRepository, "priority_prospects", priority_prospects)

    response = TestClient(app).get("/api/dashboard/priority-prospects?limit=1")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["scoreReasons"] == [
        {
            "reason": "Recent funding event",
            "signalSubtype": "funding",
            "evidenceIds": ["ev-funding-1"],
        }
    ]
    assert items[0]["evidenceIds"] == ["ev-funding-1", "ev-cross-border-1"]


def test_market_overview_chart_items_include_drilldown_when_present(monkeypatch) -> None:
    def chart_breakdown(self: ReadRepository, column: str) -> list[dict]:
        if column != "industry":
            return []
        return [
            {
                "key": "Fintech",
                "label": "Fintech",
                "value": 2,
                "drilldown": {
                    "prospectIds": ["prospect-alpha", "prospect-beta"],
                    "evidenceIds": ["ev-funding-1"],
                },
            }
        ]

    def signal_breakdown(self: ReadRepository) -> list[dict]:
        return []

    monkeypatch.setattr(ReadRepository, "chart_breakdown", chart_breakdown)
    monkeypatch.setattr(ReadRepository, "signal_breakdown", signal_breakdown)

    response = TestClient(app).get("/api/dashboard/market-overview")

    assert response.status_code == 200
    industry_items = response.json()["industryBreakdown"]
    assert industry_items == [
        {
            "key": "Fintech",
            "label": "Fintech",
            "value": 2,
            "drilldown": {
                "prospectIds": ["prospect-alpha", "prospect-beta"],
                "evidenceIds": ["ev-funding-1"],
            },
        }
    ]


def test_evidence_ids_ignore_malformed_non_list_shapes() -> None:
    assert _evidence_ids({"score_inputs": {"evidence_refs": {"evidence_id": "ev-dict"}}}) == []
    assert _evidence_ids({"score_inputs": {"evidence_refs": "ev-string"}}) == []
    assert _evidence_ids({"score_inputs": {"evidence_refs": [{"evidence_id": "ev-ok"}, {"missing": "id"}, 7]}}) == [
        "ev-ok"
    ]


def test_score_reason_items_ignore_malformed_non_list_shapes() -> None:
    row = {
        "score_reasons": [
            {"reason": "Valid", "signal_subtype": "funding", "evidence_ids": ["ev-ok", 42]},
            {"reason": "Camel subtype", "signalSubtype": "cross_border", "evidence_ids": []},
            {"reason": "Non-string subtype", "signal_subtype": 123, "evidence_ids": []},
            {"reason": "Dict evidence", "signal_subtype": "risk", "evidence_ids": {"evidence_id": "ev-dict"}},
            {"reason": "String evidence", "signal_subtype": "growth", "evidence_ids": "ev-string"},
            "not-a-dict",
        ]
    }

    assert _score_reason_items(row) == [
        {"reason": "Valid", "signalSubtype": "funding", "evidenceIds": ["ev-ok"]},
        {"reason": "Camel subtype", "signalSubtype": "cross_border", "evidenceIds": []},
        {"reason": "Non-string subtype", "signalSubtype": None, "evidenceIds": []},
        {"reason": "Dict evidence", "signalSubtype": "risk", "evidenceIds": []},
        {"reason": "String evidence", "signalSubtype": "growth", "evidenceIds": []},
    ]


def test_product_fit_accepts_only_string_lists() -> None:
    assert _product_fit({"recommended_products": "Cash management"}) == []
    assert _product_fit({"recommended_products": {"product": "Cash management"}}) == []
    assert _product_fit({"recommended_products": ["Cash management", 123, None, "Trade finance"]}) == [
        "Cash management",
        "Trade finance",
    ]


def test_priority_prospects_filters_invalid_product_fit_items(monkeypatch) -> None:
    def priority_prospects(self: ReadRepository, *, limit: int = 10) -> list[dict]:
        return [
            {
                "prospect_id": "prospect-alpha",
                "display_name": "Alpha Limited",
                "score": 91.5,
                "tier": "A",
                "recommended_products": ["Cash management", 123, {"product": "Invalid"}],
                "recommended_entry_angle": None,
                "score_reasons": [],
                "score_inputs": {},
            }
        ][:limit]

    monkeypatch.setattr(ReadRepository, "priority_prospects", priority_prospects)

    response = TestClient(app).get("/api/dashboard/priority-prospects?limit=1")

    assert response.status_code == 200
    assert response.json()["items"][0]["productFit"] == ["Cash management"]


def test_chart_breakdown_uses_db_side_aggregation_and_bounded_drilldown_ids() -> None:
    class Result:
        def mappings(self) -> list[dict]:
            return [
                {
                    "key": "Fintech",
                    "label": "Fintech",
                    "value": 50,
                    "prospect_ids": [f"prospect-{index}" for index in range(12)],
                    "evidence_ids": "not-a-list",
                }
            ]

    class DB:
        query = ""

        def execute(self, statement: TextClause) -> Result:
            self.query = str(statement)
            return Result()

    db = DB()

    items = ReadRepository(db).chart_breakdown("industry")

    assert "COUNT(*) AS value" in db.query
    assert "LIMIT 10" in db.query
    assert "SELECT prospect_id, COALESCE" not in db.query
    assert items == [
        {
            "key": "Fintech",
            "label": "Fintech",
            "value": 50,
            "drilldown": {"prospectIds": [f"prospect-{index}" for index in range(10)], "evidenceIds": []},
        }
    ]
