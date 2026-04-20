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
