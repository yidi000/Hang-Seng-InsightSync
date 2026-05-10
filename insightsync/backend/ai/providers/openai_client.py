from __future__ import annotations

import json
import random
import threading
import time
from typing import Any

from insightsync.backend.core.config import Settings
from insightsync.backend.utils import stable_hash


class OpenAIProvider:
    """OpenAI-compatible provider with deterministic local fallbacks."""

    _chat_lock = threading.Lock()
    _last_chat_call_at = 0.0

    def __init__(self, settings: Settings, *, sleeper: Any = time.sleep) -> None:
        self.settings = settings
        self._sleep = sleeper

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for input texts."""

        if self.settings.embedding_provider == "fallback" or not self.settings.openai_api_key:
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

        client = OpenAI(api_key=self.settings.chat_api_key, base_url=self.settings.llm_base_url)
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
        try:
            response = self._create_chat_completion(
                client,
                messages=[
                    {
                        "role": "system",
                        "content": "You produce evidence-grounded commercial banking insights as strict JSON.",
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
            )
        except Exception as exc:
            if self._is_rate_limit_error(exc):
                return self._rate_limit_error()
            raise
        content = response.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return self._json_parse_error()

    def generate_structured_json(self, *, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate strict JSON for OpenAI-compatible chat models."""

        evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
        question = str(payload.get("question") or payload.get("message") or "")
        if not self.settings.llm_enabled:
            citations = []
            for item in evidence:
                if not isinstance(item, dict):
                    continue
                if item.get("evidence_id"):
                    citations.append({"evidence_id": item.get("evidence_id"), "reason": "Matched retrieved evidence."})
                elif item.get("chunk_id"):
                    citations.append({"chunk_id": item.get("chunk_id"), "reason": "Matched retrieved evidence."})
            return {
                "status": "ok" if citations else "insufficient_evidence",
                "title": "Evidence-grounded answer" if citations else "Insufficient evidence",
                "summary": f"Retrieved {len(citations)} evidence item(s) relevant to: {question}" if citations else "No evidence was available.",
                "answer": f"Retrieved {len(citations)} evidence item(s) relevant to: {question}" if citations else "Insufficient evidence was retrieved for this question.",
                "citations": citations,
                "suggested_actions": ["Review cited evidence before outreach."] if citations else [],
                "confidence": 0.5 if citations else 0.0,
                "requires_human_review": True,
            }

        from openai import OpenAI

        client = OpenAI(api_key=self.settings.chat_api_key, base_url=self.settings.llm_base_url)
        try:
            response = self._create_chat_completion(
                client,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
                ],
            )
        except Exception as exc:
            if self._is_rate_limit_error(exc):
                return self._rate_limit_error()
            raise
        content = response.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return self._json_parse_error()

    def _fallback_embedding(self, text: str) -> list[float]:
        seed = int(stable_hash(text)[:16], 16)
        rng = random.Random(seed)
        values = [rng.uniform(-1.0, 1.0) for _ in range(self.settings.embedding_dimensions)]
        norm = sum(value * value for value in values) ** 0.5 or 1.0
        return [value / norm for value in values]

    def _json_parse_error(self) -> dict[str, Any]:
        return {
            "status": "error",
            "error_code": "LLM_JSON_PARSE_ERROR",
            "answer": "",
            "citations": [],
            "requires_human_review": True,
        }

    def _rate_limit_error(self) -> dict[str, Any]:
        return {
            "status": "error",
            "error_code": "LLM_RATE_LIMITED",
            "answer": "",
            "citations": [],
            "requires_human_review": True,
        }

    def _create_chat_completion(self, client: Any, *, messages: list[dict[str, str]]) -> Any:
        attempts = max(1, self.settings.llm_max_retries + 1)
        for attempt in range(attempts):
            try:
                with self._chat_lock:
                    self._respect_min_interval()
                    response = client.chat.completions.create(
                        model=self.settings.chat_model,
                        messages=messages,
                        response_format={"type": "json_object"},
                    )
                    type(self)._last_chat_call_at = time.monotonic()
                    return response
            except Exception as exc:
                if not self._is_rate_limit_error(exc) or attempt == attempts - 1:
                    raise
                self._sleep(self._backoff_seconds(attempt))
        raise RuntimeError("unreachable")

    def _respect_min_interval(self) -> None:
        interval = max(0.0, float(self.settings.llm_min_interval_seconds))
        if interval <= 0:
            return
        elapsed = time.monotonic() - type(self)._last_chat_call_at
        if elapsed < interval:
            self._sleep(interval - elapsed)

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code == 429:
            return True
        message = str(exc).lower()
        return "rate limit" in message or "429" in message or "速率限制" in message

    def _backoff_seconds(self, attempt: int) -> float:
        schedule = [2.0, 5.0, 10.0]
        if attempt < len(schedule):
            return schedule[attempt]
        return schedule[-1]

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
