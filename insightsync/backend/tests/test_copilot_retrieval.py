from __future__ import annotations

from typing import Any

from insightsync.backend.core.config import Settings
from insightsync.backend.schemas.copilot import CopilotFilters
from insightsync.backend.services.copilot_retrieval import RetrievalRequest, build_retrieval_plan
from insightsync.backend.services.copilot_service import CopilotService


def test_prospect_context_retrieves_structured_and_vector_sources() -> None:
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="What makes this prospect actionable?",
            context="prospect",
            filters={"prospect_id": "002129"},
            top_k=5,
        )
    )

    assert "prospect_evidence_items" in plan.sql_sources
    assert "prospect_signals" in plan.sql_sources
    assert "prospect_scores" in plan.sql_sources
    assert "client_one_view_timeline" in plan.sql_sources
    assert plan.use_vector is True
    assert plan.required_filters["prospect_id"] == "002129"


def test_market_context_includes_market_snapshots_and_policy_evidence() -> None:
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which GBA policy signals create opportunities?",
            context="market",
            filters={"region": "Hong Kong"},
            top_k=8,
        )
    )

    assert "market_opportunity_snapshots" in plan.sql_sources
    assert "prospect_evidence_items" in plan.sql_sources
    assert plan.use_vector is True


def test_signal_context_scopes_to_signal_sources_and_filters() -> None:
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which signal is strongest?",
            context="signal",
            filters={"signal_type": "policy", "prospect_id": "002129"},
            top_k=3,
        )
    )

    assert plan.sql_sources == ("prospect_signals", "prospect_evidence_items")
    assert plan.required_filters["signal_type"] == "policy"
    assert plan.required_filters["prospect_id"] == "002129"
    assert plan.top_k == 3


def test_global_context_uses_broad_structured_and_vector_sources() -> None:
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="What should RMs know today?",
            context="global",
            filters={},
            top_k=10,
        )
    )

    assert plan.sql_sources == (
        "prospect_evidence_items",
        "prospect_signals",
        "market_opportunity_snapshots",
    )
    assert plan.required_filters == {}
    assert plan.use_vector is True


def test_copilot_filters_preserve_supported_service_scopes() -> None:
    filters = CopilotFilters(
        dataset="gba",
        company_id="company-1",
        signal_subtype="cross_border",
        size_band="mid",
    )

    assert filters.model_dump(exclude_none=True) == {
        "dataset": "gba",
        "company_id": "company-1",
        "signal_subtype": "cross_border",
        "size_band": "mid",
    }


def test_copilot_filters_accept_camel_case_aliases_but_dump_snake_case() -> None:
    filters = CopilotFilters.model_validate(
        {
            "prospectId": "002129",
            "dataset": "gba",
            "companyId": "company-1",
            "signalType": "policy",
            "signalSubtype": "cross_border",
            "sizeBand": "mid",
            "dateFrom": "2026-01-01",
            "dateTo": "2026-05-01",
        }
    )

    assert filters.model_dump(exclude_none=True) == {
        "prospect_id": "002129",
        "dataset": "gba",
        "company_id": "company-1",
        "signal_type": "policy",
        "signal_subtype": "cross_border",
        "size_band": "mid",
        "date_from": "2026-01-01",
        "date_to": "2026-05-01",
    }


def test_prospect_structured_retrieval_returns_score_and_timeline_evidence() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, _params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            if "FROM prospect_scores ps" in sql:
                return FakeResult(
                    [
                        {
                            "prospect_id": "002129",
                            "company_id": "company-1",
                            "score": 88.0,
                            "tier": "A",
                            "reasons_json": ["high cross-border activity"],
                            "recommended_products_json": ["trade finance"],
                            "recommended_entry_angle": "Lead with GBA expansion support.",
                            "updated_at": None,
                        }
                    ]
                )
            if "FROM client_one_view_timeline cot" in sql:
                return FakeResult(
                    [
                        {
                            "id": 99,
                            "source": "crm",
                            "company_id": "company-1",
                            "entity": "Acme HK",
                            "event_time": None,
                            "event_type": "meeting",
                            "headline": "Treasury review",
                            "detail": "Client asked about FX and cash pooling.",
                            "evidence_url": "https://example.test/timeline/99",
                            "score": 1.0,
                        }
                    ]
                )
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="What makes this prospect actionable?",
            context="prospect",
            filters={"prospect_id": "002129"},
            top_k=5,
        )
    )

    evidence = service._retrieve_structured_evidence(plan)

    evidence_ids = [item["evidence_id"] for item in evidence]
    assert "score:002129" in evidence_ids
    assert "timeline:99" in evidence_ids
    assert any("88.0" in item["summary"] for item in evidence)
    assert any("Treasury review" in item["summary"] for item in evidence)


def test_service_deduplicates_vector_and_structured_evidence() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, _params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            if "FROM prospect_evidence_items pei" in sql and "rag_documents" not in sql:
                return FakeResult(
                    [
                        {
                            "evidence_id": "ev-1",
                            "title": "Structured hit",
                            "summary": "Structured summary",
                            "source": "curated",
                            "dataset": "prospects",
                            "event_time": None,
                            "url": None,
                            "prospect_id": "002129",
                            "evidence_type": "signal",
                            "score": 1.0,
                        }
                    ]
                )
            if "FROM rag_documents rd" in sql:
                return FakeResult(
                    [
                        {
                            "evidence_id": "ev-1",
                            "title": "Vector duplicate",
                            "summary": "Vector summary",
                            "source": "curated",
                            "dataset": "prospects",
                            "event_time": None,
                            "url": None,
                            "prospect_id": "002129",
                            "evidence_type": "signal",
                            "score": 0.99,
                        },
                        {
                            "evidence_id": "ev-2",
                            "title": "Vector hit",
                            "summary": "Vector-only summary",
                            "source": "curated",
                            "dataset": "prospects",
                            "event_time": None,
                            "url": None,
                            "prospect_id": "002129",
                            "evidence_type": "signal",
                            "score": 0.95,
                        },
                    ]
                )
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]

    evidence = service.retrieve_evidence(
        message="What makes this prospect actionable?",
        context="prospect",
        filters={"prospect_id": "002129"},
        top_k=5,
    )

    assert [item["evidence_id"] for item in evidence] == ["ev-1", "ev-2"]
    assert evidence[0]["title"] == "Structured hit"


def test_structured_retrieval_uses_signal_plan_sources() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, _params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            if "FROM prospect_signals ps" in sql:
                return FakeResult(
                    [
                        {
                            "signal_id": "sig-1",
                            "prospect_id": "002129",
                            "company_id": "c-1",
                            "signal_type": "policy",
                            "signal_subtype": "gba",
                            "signal_text": "GBA expansion policy signal",
                            "event_time": None,
                            "evidence_ids_json": [],
                            "score": 1.0,
                        }
                    ]
                )
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which signal is strongest?",
            context="signal",
            filters={"signal_type": "policy", "prospect_id": "002129"},
            top_k=5,
        )
    )

    evidence = service._retrieve_structured_evidence(plan)

    assert evidence[0]["evidence_id"] == "signal:sig-1"
    assert evidence[0]["evidence_type"] == "signal"
    assert "GBA expansion policy signal" in evidence[0]["summary"]


def test_structured_retrieval_uses_market_plan_sources() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, _params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            if "FROM market_opportunity_snapshots mos" in sql:
                return FakeResult(
                    [
                        {
                            "id": 42,
                            "snapshot_date": None,
                            "region": "Hong Kong",
                            "industry": "logistics",
                            "size_band": "mid",
                            "signal_type": "policy",
                            "lead_count": 7,
                            "signal_count": 9,
                            "avg_score": 81.5,
                            "trend_summary": "Policy demand is rising",
                            "score": 1.0,
                        }
                    ]
                )
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which GBA policy signals create opportunities?",
            context="market",
            filters={"region": "Hong Kong"},
            top_k=5,
        )
    )

    evidence = service._retrieve_structured_evidence(plan)

    assert evidence[0]["evidence_id"] == "market:42"
    assert evidence[0]["evidence_type"] == "market_opportunity_snapshot"
    assert "Policy demand is rising" in evidence[0]["summary"]


def test_market_structured_source_is_not_starved_by_prospect_evidence() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, _params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            if "FROM prospect_evidence_items pei" in sql and "rag_documents" not in sql:
                return FakeResult(
                    [
                        {
                            "evidence_id": f"ev-{idx}",
                            "title": f"PEI {idx}",
                            "summary": f"Prospect evidence {idx}",
                            "source": "curated",
                            "dataset": "prospects",
                            "event_time": None,
                            "url": None,
                            "prospect_id": f"p-{idx}",
                            "evidence_type": "policy",
                            "score": 1.0,
                        }
                        for idx in range(5)
                    ]
                )
            if "FROM market_opportunity_snapshots mos" in sql:
                return FakeResult(
                    [
                        {
                            "id": 42,
                            "snapshot_date": None,
                            "region": "Hong Kong",
                            "industry": "logistics",
                            "size_band": "mid",
                            "signal_type": "policy",
                            "lead_count": 7,
                            "signal_count": 9,
                            "avg_score": 81.5,
                            "trend_summary": "Policy demand is rising",
                            "score": 1.0,
                        }
                    ]
                )
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which GBA policy signals create opportunities?",
            context="market",
            filters={"region": "Hong Kong"},
            top_k=5,
        )
    )

    evidence = service._retrieve_structured_evidence(plan)

    assert evidence[0]["evidence_id"] == "market:42"
    assert "market:42" in [item["evidence_id"] for item in evidence]


def test_signal_structured_source_is_not_starved_by_prospect_evidence() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, _params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            if "FROM prospect_evidence_items pei" in sql and "rag_documents" not in sql:
                return FakeResult(
                    [
                        {
                            "evidence_id": f"ev-{idx}",
                            "title": f"PEI {idx}",
                            "summary": f"Prospect evidence {idx}",
                            "source": "curated",
                            "dataset": "prospects",
                            "event_time": None,
                            "url": None,
                            "prospect_id": "002129",
                            "evidence_type": "policy",
                            "score": 1.0,
                        }
                        for idx in range(5)
                    ]
                )
            if "FROM prospect_signals ps" in sql:
                return FakeResult(
                    [
                        {
                            "signal_id": "sig-1",
                            "prospect_id": "002129",
                            "company_id": "c-1",
                            "signal_type": "policy",
                            "signal_subtype": "gba",
                            "signal_text": "GBA expansion policy signal",
                            "event_time": None,
                            "evidence_ids_json": [],
                            "score": 1.0,
                        }
                    ]
                )
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which signal is strongest?",
            context="signal",
            filters={"signal_type": "policy", "prospect_id": "002129"},
            top_k=5,
        )
    )

    evidence = service._retrieve_structured_evidence(plan)

    assert evidence[0]["evidence_id"] == "signal:sig-1"
    assert "signal:sig-1" in [item["evidence_id"] for item in evidence]


def test_vector_retrieval_overfetches_and_deduplicates_evidence_ids() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, _statement: Any, params: dict[str, Any]) -> FakeResult:
            rows = [
                {
                    "evidence_id": "ev-1",
                    "title": "Duplicate chunk",
                    "summary": "Duplicate chunk",
                    "source": "curated",
                    "dataset": "prospects",
                    "event_time": None,
                    "url": None,
                    "prospect_id": "002129",
                    "evidence_type": "signal",
                    "score": 0.99,
                },
                {
                    "evidence_id": "ev-1",
                    "title": "Duplicate chunk",
                    "summary": "Duplicate chunk",
                    "source": "curated",
                    "dataset": "prospects",
                    "event_time": None,
                    "url": None,
                    "prospect_id": "002129",
                    "evidence_type": "signal",
                    "score": 0.98,
                },
                {
                    "evidence_id": "ev-2",
                    "title": "Second evidence",
                    "summary": "Second evidence",
                    "source": "curated",
                    "dataset": "prospects",
                    "event_time": None,
                    "url": None,
                    "prospect_id": "002129",
                    "evidence_type": "signal",
                    "score": 0.97,
                },
                {
                    "evidence_id": "ev-3",
                    "title": "Third evidence",
                    "summary": "Third evidence",
                    "source": "curated",
                    "dataset": "prospects",
                    "event_time": None,
                    "url": None,
                    "prospect_id": "002129",
                    "evidence_type": "signal",
                    "score": 0.96,
                },
            ]
            return FakeResult(rows[: params["limit"]])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="What makes this prospect actionable?",
            context="prospect",
            filters={"prospect_id": "002129"},
            top_k=3,
        )
    )

    evidence = service._retrieve_vector_evidence(plan)

    assert [item["evidence_id"] for item in evidence] == ["ev-1", "ev-2", "ev-3"]


def test_synthetic_signal_citation_validates_when_retrieved() -> None:
    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(db=None, settings=settings)  # type: ignore[arg-type]

    citations = service._validate_citations(
        {"citations": [{"evidence_id": "signal:sig-1"}]},
        [
            {
                "evidence_id": "signal:sig-1",
                "title": "gba signal",
                "summary": "GBA expansion policy signal",
                "source": "prospect_signals",
                "dataset": "curated",
                "event_time": None,
                "url": None,
            }
        ],
    )

    assert citations == [
        {
            "evidence_id": "signal:sig-1",
            "title": "gba signal",
            "source": "prospect_signals",
            "dataset": "curated",
            "event_time": None,
            "url": None,
            "snippet": "GBA expansion policy signal",
        }
    ]


def test_signal_structured_source_applies_source_dataset_filters() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            assert "ps.metadata_json->>'source' = :source" in sql
            assert "ps.metadata_json->>'dataset' = :dataset" in sql
            assert params["source"] == "policy_feed"
            assert params["dataset"] == "gba"
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which signal is strongest?",
            context="signal",
            filters={"source": "policy_feed", "dataset": "gba"},
            top_k=5,
        )
    )

    service._retrieve_prospect_signals(plan)


def test_signal_structured_source_applies_size_band_filter() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def execute(self, statement: Any, params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            assert "LEFT JOIN prospects p ON p.prospect_id = ps.prospect_id" in sql
            assert "p.size_band = :size_band" in sql
            assert params["size_band"] == "mid"
            return FakeResult([])

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which signal is strongest?",
            context="signal",
            filters={"size_band": "mid"},
            top_k=5,
        )
    )

    service._retrieve_prospect_signals(plan)


def test_market_snapshots_are_skipped_for_source_or_dataset_scope() -> None:
    class FakeDB:
        def execute(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("market snapshots should be skipped when source or dataset is scoped")

    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(FakeDB(), settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which GBA policy signals create opportunities?",
            context="market",
            filters={"region": "Hong Kong", "source": "policy_feed"},
            top_k=5,
        )
    )

    assert service._retrieve_market_opportunity_snapshots(plan) == []


def test_linked_signal_evidence_reapplies_prospect_evidence_filters() -> None:
    class FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeMappings:
            return FakeMappings(self._rows)

    class FakeDB:
        def __init__(self) -> None:
            self.checked_linked_query = False

        def execute(self, statement: Any, params: dict[str, Any]) -> FakeResult:
            sql = str(statement)
            if "FROM prospect_signals ps" in sql:
                return FakeResult(
                    [
                        {
                            "signal_id": "sig-1",
                            "prospect_id": "002129",
                            "company_id": "c-1",
                            "signal_type": "policy",
                            "signal_subtype": "gba",
                            "signal_text": "GBA expansion policy signal",
                            "event_time": None,
                            "evidence_ids_json": ["ev-linked"],
                            "score": 1.0,
                        }
                    ]
                )
            if "WHERE pei.evidence_id = ANY(:evidence_ids)" in sql:
                self.checked_linked_query = True
                assert "pei.source = :source" in sql
                assert "pei.dataset = :dataset" in sql
                assert "pei.event_time >= :date_from" in sql
                assert "pei.event_time <= :date_to" in sql
                assert "p.region = :region" in sql
                assert "p.industry = :industry" in sql
                assert "pei.prospect_id = :prospect_id" in sql
                assert params["source"] == "policy_feed"
                assert params["dataset"] == "gba"
                assert params["date_from"] == "2026-01-01"
                assert params["date_to"] == "2026-05-01"
                assert params["region"] == "Hong Kong"
                assert params["industry"] == "logistics"
                assert params["prospect_id"] == "002129"
                return FakeResult(
                    [
                        {
                            "evidence_id": "ev-linked",
                            "title": "Linked evidence",
                            "summary": "Linked evidence summary",
                            "source": "policy_feed",
                            "dataset": "gba",
                            "event_time": None,
                            "url": None,
                            "prospect_id": "002129",
                            "evidence_type": "policy",
                            "score": 1.0,
                        }
                    ]
                )
            if "FROM prospect_evidence_items pei" in sql:
                return FakeResult([])
            return FakeResult([])

    db = FakeDB()
    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3)
    service = CopilotService(db, settings)  # type: ignore[arg-type]
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which signal is strongest?",
            context="signal",
            filters={
                "source": "policy_feed",
                "dataset": "gba",
                "date_from": "2026-01-01",
                "date_to": "2026-05-01",
                "region": "Hong Kong",
                "industry": "logistics",
                "prospect_id": "002129",
            },
            top_k=5,
        )
    )

    evidence = service._retrieve_structured_evidence(plan)

    assert db.checked_linked_query is True
    assert "ev-linked" in [item["evidence_id"] for item in evidence]
