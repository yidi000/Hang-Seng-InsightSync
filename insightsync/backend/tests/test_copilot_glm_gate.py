from __future__ import annotations

import sys
import types
from typing import Any

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings
from insightsync.backend.services.copilot_service import CopilotService


def test_validate_citations_rejects_ids_not_retrieved() -> None:
    service = object.__new__(CopilotService)
    evidence = [{"evidence_id": "ev_allowed", "title": "Allowed", "summary": "Allowed summary"}]
    output = {"citations": [{"evidence_id": "ev_fake"}]}

    citations = CopilotService._validate_citations(service, output, evidence)

    assert citations == []


def test_validate_citations_keeps_retrieved_ids() -> None:
    service = object.__new__(CopilotService)
    evidence = [
        {
            "evidence_id": "ev_allowed",
            "title": "Allowed",
            "summary": "Allowed summary",
            "source": "hkgov",
        }
    ]
    output = {"citations": [{"evidence_id": "ev_allowed"}]}

    citations = CopilotService._validate_citations(service, output, evidence)

    assert citations[0]["evidence_id"] == "ev_allowed"
    assert citations[0]["source"] == "hkgov"


def test_provider_returns_controlled_error_for_invalid_json(monkeypatch: Any) -> None:
    class FakeMessage:
        content = "not json"

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **_kwargs: Any) -> FakeResponse:
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = FakeChat()

    fake_openai = types.SimpleNamespace(OpenAI=FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    provider = OpenAIProvider(Settings(ENABLE_LLM_GENERATION=True, LLM_API_KEY="test-key"))

    output = provider.generate_structured_json(system="system", payload={"message": "hello", "evidence": []})

    assert output == {
        "status": "error",
        "error_code": "LLM_JSON_PARSE_ERROR",
        "answer": "",
        "citations": [],
        "requires_human_review": True,
    }


def test_copilot_chat_treats_provider_error_as_insufficient_evidence() -> None:
    class FakeResult:
        rowcount = 1

    class FakeDB:
        def execute(self, *_args: Any, **_kwargs: Any) -> FakeResult:
            return FakeResult()

    class FakeProvider:
        def generate_structured_json(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "status": "error",
                "error_code": "LLM_JSON_PARSE_ERROR",
                "answer": "",
                "citations": [],
                "requires_human_review": True,
            }

    service = CopilotService(FakeDB(), Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3))  # type: ignore[arg-type]
    service.provider = FakeProvider()  # type: ignore[assignment]
    service.retrieve_evidence = lambda **_kwargs: [  # type: ignore[method-assign]
        {
            "evidence_id": "ev_allowed",
            "title": "Allowed",
            "summary": "Allowed summary",
            "source": "hkgov",
        }
    ]

    result = service.chat(
        message="What evidence exists?",
        conversation_id=None,
        context="global",
        filters={},
        top_k=1,
    )

    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []
    assert result["structured_insight"] == {
        "status": "insufficient_evidence",
        "error_code": "LLM_JSON_PARSE_ERROR",
        "requires_human_review": True,
    }


def test_copilot_prompt_requires_exact_allowed_evidence_ids() -> None:
    class FakeResult:
        rowcount = 1

    class FakeDB:
        def execute(self, *_args: Any, **_kwargs: Any) -> FakeResult:
            return FakeResult()

    captured: dict[str, Any] = {}

    class FakeProvider:
        def generate_structured_json(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {
                "answer": "The prospect shows cross-border activity.",
                "citations": [{"evidence_id": "ev_allowed", "reason": "Directly retrieved evidence."}],
            }

    service = CopilotService(FakeDB(), Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=3))  # type: ignore[arg-type]
    service.provider = FakeProvider()  # type: ignore[assignment]
    service.retrieve_evidence = lambda **_kwargs: [  # type: ignore[method-assign]
        {
            "evidence_id": "ev_allowed",
            "title": "Allowed",
            "summary": "Allowed summary",
            "source": "hkgov",
        }
    ]

    result = service.chat(
        message="Which prospects show cross-border opportunity?",
        conversation_id=None,
        context="global",
        filters={},
        top_k=1,
    )

    payload = captured["payload"]
    assert result["status"] == "ok"
    assert payload["language_policy"] == "Answer in the same language as the user's original message."
    assert payload["allowed_evidence_ids"] == ["ev_allowed"]
    assert payload["required_output_schema"]["citations"][0]["evidence_id"] == "one of allowed_evidence_ids"
    assert "insightful financial analyst" in captured["system"]
