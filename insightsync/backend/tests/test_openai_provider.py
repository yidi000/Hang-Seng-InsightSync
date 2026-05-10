from __future__ import annotations

import sys
import types
from typing import Any

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings


def test_fallback_embeddings_are_deterministic() -> None:
    settings = Settings(OPENAI_API_KEY="", EMBEDDING_DIMENSIONS=8)
    provider = OpenAIProvider(settings)

    first = provider.embed_texts(["same text"])[0]
    second = provider.embed_texts(["same text"])[0]

    assert first == second
    assert len(first) == 8


def test_fallback_generation_requires_evidence() -> None:
    settings = Settings(OPENAI_API_KEY="", ENABLE_LLM_GENERATION=False)
    provider = OpenAIProvider(settings)

    output = provider.generate_json(question="What changed?", evidence=[], insight_type="risk")

    assert output["status"] == "insufficient_evidence"
    assert output["citations"] == []


def test_llm_settings_use_glm_compatible_defaults() -> None:
    settings = Settings(ENABLE_LLM_GENERATION=True, LLM_API_KEY="test-key")

    assert settings.llm_enabled is True
    assert settings.chat_model == "glm-4.7-flash"
    assert settings.llm_base_url == "https://open.bigmodel.cn/api/paas/v4"


def test_llm_settings_include_throttle_and_retry_defaults() -> None:
    settings = Settings()

    assert settings.llm_min_interval_seconds == 2.0
    assert settings.llm_max_retries == 3


def test_structured_generation_retries_rate_limit_with_backoff(monkeypatch: Any) -> None:
    class FakeRateLimitError(Exception):
        status_code = 429

    class FakeMessage:
        content = '{"answer":"ok","citations":[{"evidence_id":"ev_1"}]}'

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    attempts = {"count": 0}

    class FakeCompletions:
        def create(self, **_kwargs: Any) -> FakeResponse:
            attempts["count"] += 1
            if attempts["count"] < 4:
                raise FakeRateLimitError("rate limited")
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = FakeChat()

    sleeps: list[float] = []
    fake_openai = types.SimpleNamespace(OpenAI=FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    provider = OpenAIProvider(
        Settings(
            ENABLE_LLM_GENERATION=True,
            LLM_API_KEY="test-key",
            LLM_MIN_INTERVAL_SECONDS=0,
            LLM_MAX_RETRIES=3,
        ),
        sleeper=sleeps.append,
    )

    output = provider.generate_structured_json(system="system", payload={"message": "hello", "evidence": []})

    assert output["answer"] == "ok"
    assert attempts["count"] == 4
    assert sleeps == [2.0, 5.0, 10.0]


def test_structured_generation_returns_controlled_rate_limit_error(monkeypatch: Any) -> None:
    class FakeRateLimitError(Exception):
        status_code = 429

    class FakeCompletions:
        def create(self, **_kwargs: Any) -> None:
            raise FakeRateLimitError("rate limited")

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = FakeChat()

    fake_openai = types.SimpleNamespace(OpenAI=FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    provider = OpenAIProvider(
        Settings(
            ENABLE_LLM_GENERATION=True,
            LLM_API_KEY="test-key",
            LLM_MIN_INTERVAL_SECONDS=0,
            LLM_MAX_RETRIES=1,
        ),
        sleeper=lambda _seconds: None,
    )

    output = provider.generate_structured_json(system="system", payload={"message": "hello", "evidence": []})

    assert output == {
        "status": "error",
        "error_code": "LLM_RATE_LIMITED",
        "answer": "",
        "citations": [],
        "requires_human_review": True,
    }
