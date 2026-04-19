from __future__ import annotations

import json
import random
from typing import Any

from insightsync.backend.core.config import Settings
from insightsync.backend.utils import stable_hash


class OpenAIProvider:
    """OpenAI-backed provider with deterministic local fallbacks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for input texts."""

        if not self.settings.openai_api_key:
            return [self._fallback_embedding(text) for text in texts]

        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=texts,
            dimensions=self.settings.embedding_dimensions,
        )
        return [item.embedding for item in response.data]

    def generate_json(self, *, question: str, evidence: list[dict[str, Any]], insight_type: str) -> dict[str, Any]:
        """Generate a structured JSON insight grounded in supplied evidence."""

        if not self.settings.llm_enabled:
            return self._fallback_generation(question=question, evidence=evidence, insight_type=insight_type)

        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key)
        prompt = {
            "question": question,
            "insight_type": insight_type,
            "evidence": evidence,
            "rules": [
                "Use only the supplied evidence.",
                "Every conclusion must cite at least one evidence item.",
                "Return JSON only.",
            ],
        }
        response = client.chat.completions.create(
            model=self.settings.openai_chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "You produce evidence-grounded commercial banking insights as strict JSON.",
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _fallback_embedding(self, text: str) -> list[float]:
        seed = int(stable_hash(text)[:16], 16)
        rng = random.Random(seed)
        values = [rng.uniform(-1.0, 1.0) for _ in range(self.settings.embedding_dimensions)]
        norm = sum(value * value for value in values) ** 0.5 or 1.0
        return [value / norm for value in values]

    def _fallback_generation(self, *, question: str, evidence: list[dict[str, Any]], insight_type: str) -> dict[str, Any]:
        citations = [
            {
                "chunk_id": item["chunk_id"],
                "record_key": item.get("record_key"),
                "signal_key": item.get("signal_key"),
            }
            for item in evidence
        ]
        if not citations:
            return {
                "status": "insufficient_evidence",
                "insight_type": insight_type,
                "title": "Insufficient evidence",
                "summary": "No retrieved evidence was available for this question.",
                "citations": [],
                "confidence": 0.0,
            }
        return {
            "status": "ok",
            "insight_type": insight_type,
            "title": "Evidence-grounded summary",
            "summary": f"Retrieved {len(citations)} evidence item(s) relevant to: {question}",
            "business_reasoning": "This fallback explanation is generated without an external LLM.",
            "recommended_action": "Review the cited evidence before taking client action.",
            "citations": citations,
            "confidence": 0.5,
            "limitations": "Fallback mode does not perform natural language reasoning.",
            "requires_human_review": True,
        }
