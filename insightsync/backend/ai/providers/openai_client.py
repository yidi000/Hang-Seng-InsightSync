from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any

from insightsync.backend.core.config import Settings
from insightsync.backend.utils import stable_hash

logger = logging.getLogger(__name__)

MAX_GENERATION_EVIDENCE_ITEMS = 5
MAX_GENERATION_EVIDENCE_TEXT_CHARS = 700


class OpenAIProvider:
    """OpenAI-backed provider with deterministic local fallbacks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for input texts."""

        if not self.settings.openai_api_key:
            return [self._fallback_embedding(text) for text in texts]

        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key, base_url=self.settings.openai_base_url)
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

        compact_evidence = self._compact_evidence_for_generation(evidence)
        prompt = {
            "question": question,
            "insight_type": insight_type,
            "evidence": compact_evidence,
            "rules": [
                "Use only the supplied evidence.",
                "Every conclusion must cite at least one evidence item.",
                "Cite every evidence item that materially affects the summary, reasoning, action, limitations, or human-review decision.",
                "If a regulatory, compliance, liquidity, or execution risk is mentioned, cite the risk evidence item.",
                "If regulatory or compliance risk evidence is cited, limitations must name the risk and requires_human_review must be true.",
                "Never write that there are no limitations when any cited evidence contains risk, regulatory, compliance, licensing, KYC, liquidity, debt, or execution concerns.",
                "Do not recommend action if the cited evidence is weak or only contextual.",
                "Return one compact JSON object only.",
            ],
            "required_schema": {
                "status": "ok",
                "insight_type": insight_type,
                "title": "short title",
                "summary": "2-3 sentence evidence-grounded answer",
                "business_reasoning": "why the evidence matters commercially",
                "recommended_action": "specific next best action for a Hang Seng Bank RM",
                "citations": [{"chunk_id": "integer from evidence", "used_for": "opportunity/risk/action", "reason": "why cited"}],
                "confidence": "number from 0 to 1",
                "limitations": "material caveats",
                "requires_human_review": "boolean",
            },
        }
        try:
            return self.chat_json(
                system_prompt=(
                    "You produce concise evidence-grounded commercial banking insights for Hang Seng Bank. "
                    "Return valid JSON only, with no markdown. Keep output compact."
                ),
                messages=[
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM insight generation failed; using fallback generation: %s", exc)
            fallback = self._fallback_generation(question=question, evidence=evidence, insight_type=insight_type)
            fallback["status"] = "llm_error_fallback"
            fallback["llm_error"] = str(exc)
            return fallback

    def chat_json(self, *, system_prompt: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Call an OpenAI-compatible chat model and parse strict JSON output."""

        if not self.settings.llm_enabled:
            return {}

        from openai import OpenAI

        client = OpenAI(api_key=self.settings.llm_api_key, base_url=self.settings.llm_base_url)
        extra_body: dict[str, Any] = {}
        if self.settings.llm_enable_thinking:
            extra_body["thinking"] = {"type": "enabled"}
        request = {
            "model": self.settings.llm_chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
        }
        if extra_body:
            request["extra_body"] = extra_body

        errors: list[Exception] = []
        use_response_format_plan = [True, False, False]
        for attempt_index, use_response_format in enumerate(use_response_format_plan):
            try:
                call_request = dict(request)
                if use_response_format:
                    call_request["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**call_request)
                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise ValueError("LLM returned empty content")
                return self._parse_json_content(content)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
                if attempt_index < len(use_response_format_plan) - 1:
                    time.sleep(0.8 * (attempt_index + 1))
                    continue
                raise RuntimeError("; ".join(str(error) for error in errors)) from exc

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        text = content.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                raise
            parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _compact_evidence_for_generation(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compact_items: list[dict[str, Any]] = []
        for item in evidence[:MAX_GENERATION_EVIDENCE_ITEMS]:
            raw_text = str(item.get("text") or item.get("chunk_text") or item.get("summary") or "")
            text = " ".join(raw_text.split())
            if len(text) > MAX_GENERATION_EVIDENCE_TEXT_CHARS:
                text = f"{text[:MAX_GENERATION_EVIDENCE_TEXT_CHARS].rstrip()}..."
            compact_items.append(
                {
                    "chunk_id": item.get("chunk_id"),
                    "record_key": item.get("record_key"),
                    "signal_key": item.get("signal_key"),
                    "source": item.get("source"),
                    "dataset": item.get("dataset"),
                    "score": item.get("score"),
                    "text": text,
                }
            )
        return compact_items

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
