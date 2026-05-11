from insightsync.backend.ai.providers.openai_client import LLMProviderError, OpenAIProvider
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


def test_llm_enabled_uses_llm_credentials() -> None:
    settings = Settings(
        OPENAI_API_KEY="",
        LLM_API_KEY="test-key",
        LLM_BASE_URL="https://api.z.ai/api/paas/v4/",
        LLM_CHAT_MODEL="glm-4.7-flash",
        ENABLE_LLM_GENERATION=True,
    )

    assert settings.llm_enabled is True
    assert settings.llm_base_url == "https://api.z.ai/api/paas/v4/"
    assert settings.llm_chat_model == "glm-4.7-flash"
    assert settings.llm_enable_thinking is False


def test_glm_provider_uses_explicit_thinking_control() -> None:
    glm_provider = OpenAIProvider(
        Settings(
            LLM_BASE_URL="https://api.z.ai/api/paas/v4/",
            LLM_CHAT_MODEL="glm-4.7-flash",
        )
    )
    generic_provider = OpenAIProvider(
        Settings(
            LLM_BASE_URL="https://api.openai.com/v1",
            LLM_CHAT_MODEL="gpt-4o-mini",
        )
    )

    assert glm_provider._uses_glm_thinking_control() is True
    assert generic_provider._uses_glm_thinking_control() is False


def test_parse_json_content_extracts_json_from_wrapped_text() -> None:
    parsed = OpenAIProvider._parse_json_content('Here is JSON: {"status": "ok", "answer": "done"}')

    assert parsed == {"status": "ok", "answer": "done"}


def test_parse_json_content_returns_structured_error_for_invalid_content() -> None:
    try:
        OpenAIProvider._parse_json_content("not json")
    except LLMProviderError as exc:
        assert exc.error_code == "LLM_JSON_PARSE_ERROR"
    else:
        raise AssertionError("Expected LLMProviderError")


def test_to_llm_error_classifies_rate_limit_messages() -> None:
    error = OpenAIProvider._to_llm_error(RuntimeError("429: service temporarily overloaded"))

    assert error.error_code == "LLM_RATE_LIMITED"
