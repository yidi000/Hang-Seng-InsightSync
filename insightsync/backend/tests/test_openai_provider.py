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


def test_llm_enabled_uses_llm_credentials() -> None:
    settings = Settings(
        OPENAI_API_KEY="",
        LLM_API_KEY="test-key",
        LLM_BASE_URL="https://example.com/v1",
        LLM_CHAT_MODEL="glm-4.7-flash",
        ENABLE_LLM_GENERATION=True,
    )

    assert settings.llm_enabled is True
    assert settings.llm_chat_model == "glm-4.7-flash"
