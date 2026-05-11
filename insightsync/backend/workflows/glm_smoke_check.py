from __future__ import annotations

import json
import sys

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import get_settings


def main() -> int:
    settings = get_settings()
    if not settings.llm_enabled:
        print(
            "GLM smoke check skipped: set ENABLE_LLM_GENERATION=true and LLM_API_KEY first.",
            file=sys.stderr,
        )
        return 2

    provider = OpenAIProvider(settings)
    payload = provider.chat_json(
        system_prompt=(
            "You are a health-check endpoint. Return exactly one JSON object and no markdown. "
            "The JSON object must include status, model, and summary."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    '{"status":"ok","model":"glm-4.7-flash","summary":"InsightSync GLM integration is reachable."}'
                ),
            }
        ],
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("status") not in {"ok", "success", "ready"}:
        print("GLM smoke check completed but response status was not an expected ok value.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
