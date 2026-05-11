from __future__ import annotations

from typing import Any

from insightsync.backend.core.config import Settings
from insightsync.backend.services.insight_generator import InsightGenerator


def _generator_without_init() -> InsightGenerator:
    generator = object.__new__(InsightGenerator)
    generator.settings = Settings(OPENAI_API_KEY="", ENABLE_LLM_GENERATION=False)
    return generator


def test_validate_citations_rejects_chunk_ids_not_retrieved() -> None:
    generator = _generator_without_init()
    evidence = [
        {
            "chunk_id": 1,
            "document_id": 10,
            "score": 0.9,
            "source": "annual_report",
            "dataset": "reports",
            "record_key": "record-1",
            "signal_key": None,
            "evidence_url": "https://example.test/report.pdf",
            "chunk_text": "Allowed evidence",
        }
    ]
    output = {"citations": [{"chunk_id": 999, "reason": "not retrieved"}]}

    citations = generator._validate_citations(output, evidence)

    assert citations == []


def test_validate_citations_keeps_only_retrieved_chunk_ids() -> None:
    generator = _generator_without_init()
    evidence = [
        {
            "chunk_id": 1,
            "document_id": 10,
            "score": 0.9,
            "source": "annual_report",
            "dataset": "reports",
            "record_key": "record-1",
            "signal_key": "signal-1",
            "evidence_url": "https://example.test/report.pdf",
            "chunk_text": "Allowed evidence",
        }
    ]
    output = {"citations": [{"chunk_id": "1", "reason": "retrieved"}, {"chunk_id": "fake"}]}

    citations = generator._validate_citations(output, evidence)

    assert len(citations) == 1
    assert citations[0]["chunk_id"] == 1
    assert citations[0]["signal_key"] == "signal-1"


def test_answer_question_preserves_llm_error_fallback_status() -> None:
    class FakeRetrieval:
        def retrieve(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "retrieval_run_id": 7,
                "evidence": [
                    {
                        "chunk_id": 1,
                        "document_id": 10,
                        "score": 0.9,
                        "source": "annual_report",
                        "dataset": "reports",
                        "record_key": "record-1",
                        "signal_key": None,
                        "evidence_url": "https://example.test/report.pdf",
                        "chunk_text": "Allowed evidence",
                    }
                ],
            }

    class FakeProvider:
        def generate_json(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "status": "llm_error_fallback",
                "summary": "Fallback summary",
                "citations": [{"chunk_id": 1}],
                "llm_error_code": "LLM_RATE_LIMITED",
            }

    class FakeDB:
        def __init__(self) -> None:
            self.params: dict[str, Any] | None = None

        def execute(self, _statement: Any, params: dict[str, Any]) -> None:
            self.params = params

    fake_db = FakeDB()
    generator = object.__new__(InsightGenerator)
    generator.db = fake_db
    generator.settings = Settings(OPENAI_API_KEY="", ENABLE_LLM_GENERATION=False)
    generator.retrieval = FakeRetrieval()
    generator.provider = FakeProvider()

    result = generator.answer_question(question="What changed?", filters={})

    assert result["status"] == "llm_error_fallback"
    assert result["structured_insight"]["llm_error_code"] == "LLM_RATE_LIMITED"
    assert result["citations"][0]["chunk_id"] == 1
    assert fake_db.params is not None
    assert fake_db.params["status"] == "llm_error_fallback"
