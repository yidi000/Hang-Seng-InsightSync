from __future__ import annotations

import json
from typing import Any

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings


class FusionExplainer:
    """Generate evidence-grounded explanations from structured fusion output."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = OpenAIProvider(settings)

    def explain(
        self,
        *,
        company: dict[str, Any],
        latest_state: dict[str, Any],
        prospect: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fusion = latest_state.get("fusion") or {}
        prompt = {
            "company": {
                "company_id": company.get("company_id"),
                "display_name": company.get("display_name") or company.get("canonical_name"),
                "region": company.get("region"),
                "industries": company.get("industries", []),
                "segments": company.get("segments", []),
            },
            "prospect": {
                "priority_level": prospect.get("priority_level") if prospect else None,
                "priority_score": prospect.get("priority_score") if prospect else None,
                "opportunity_score": prospect.get("opportunity_score") if prospect else None,
                "risk_score": prospect.get("risk_score") if prospect else None,
                "recommended_product_themes": prospect.get("recommended_product_themes", []) if prospect else [],
            },
            "fusion": fusion,
            "instructions": [
                "Explain the fusion in structured JSON only.",
                "Do not invent facts beyond the provided fusion object.",
                "Use the fusion.primary_lens_key as the main explanation anchor.",
                "Return sections for headline, why_now, lens_summary, risk_note, and action_note.",
            ],
        }
        if self.settings.llm_enabled:
            try:
                payload = self.provider.chat_json(
                    system_prompt="You explain structured commercial banking fusion outputs as strict JSON.",
                    messages=[
                        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                    ],
                )
                return self._normalize(payload, fusion=fusion, company=company, prospect=prospect)
            except Exception as exc:  # noqa: BLE001
                fallback = self._fallback(fusion=fusion, company=company, prospect=prospect)
                fallback["status"] = "llm_error_fallback"
                fallback["llm_error"] = str(exc)
                return fallback

        return self._fallback(fusion=fusion, company=company, prospect=prospect)

    @staticmethod
    def _fallback(*, fusion: dict[str, Any], company: dict[str, Any], prospect: dict[str, Any] | None) -> dict[str, Any]:
        display_name = company.get("display_name") or company.get("canonical_name") or "This company"
        primary_lens = fusion.get("primary_lens_key") or "acquisition"
        headline_map = {
            "acquisition": f"{display_name} shows an acquisition-first opportunity",
            "financing": f"{display_name} shows a financing-led opportunity",
            "cross_border": f"{display_name} shows a cross-border opportunity",
        }
        return {
            "status": "fallback",
            "headline": headline_map.get(primary_lens, f"{display_name} shows a structured opportunity"),
            "why_now": fusion.get("why_now"),
            "lens_summary": fusion.get("summary"),
            "risk_note": fusion.get("key_risk"),
            "action_note": fusion.get("recommended_next_step"),
            "primary_lens_key": primary_lens,
            "recommended_entry_angles": fusion.get("recommended_entry_angles", []),
            "recommended_products": fusion.get("opportunity_lenses", [{}])[0].get("recommended_products", []) if fusion.get("opportunity_lenses") else [],
            "prospect_priority": prospect.get("priority_level") if prospect else None,
        }

    @staticmethod
    def _normalize(
        payload: dict[str, Any],
        *,
        fusion: dict[str, Any],
        company: dict[str, Any],
        prospect: dict[str, Any] | None,
    ) -> dict[str, Any]:
        fallback = FusionExplainer._fallback(fusion=fusion, company=company, prospect=prospect)
        return {
            "status": payload.get("status", "ok"),
            "headline": payload.get("headline") or payload.get("title") or payload.get("summary") or fallback["headline"],
            "why_now": payload.get("why_now") or fusion.get("why_now") or fallback["why_now"],
            "lens_summary": payload.get("lens_summary") or payload.get("summary") or fusion.get("summary") or fallback["lens_summary"],
            "risk_note": payload.get("risk_note") or fusion.get("key_risk") or fallback["risk_note"],
            "action_note": payload.get("action_note") or fusion.get("recommended_next_step") or fallback["action_note"],
            "primary_lens_key": payload.get("primary_lens_key") or fusion.get("primary_lens_key") or fallback["primary_lens_key"],
            "recommended_entry_angles": payload.get("recommended_entry_angles") or fusion.get("recommended_entry_angles", []) or fallback["recommended_entry_angles"],
            "recommended_products": payload.get("recommended_products")
            or (fusion.get("opportunity_lenses", [{}])[0].get("recommended_products", []) if fusion.get("opportunity_lenses") else [])
            or fallback["recommended_products"],
            "company_id": company.get("company_id"),
            "prospect_priority": prospect.get("priority_level") if prospect else None,
        }
