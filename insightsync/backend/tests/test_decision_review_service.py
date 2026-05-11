from __future__ import annotations

import json
from typing import Any

from insightsync.backend.core.config import Settings
from insightsync.backend.services.decision_review_service import (
    MAX_REVIEW_FEATURES,
    MAX_REVIEW_SIGNALS,
    REVIEW_MAX_TOKENS,
    REVIEW_TIMEOUT_SECONDS,
    DecisionReviewService,
)


class _FakeProvider:
    def __init__(self) -> None:
        self.request: dict[str, Any] | None = None

    def chat_json(self, **kwargs: Any) -> dict[str, Any]:
        self.request = kwargs
        return {
            "status": "ok",
            "review_summary": "Review completed with compact LLM input.",
            "linkage_reviews": [
                {
                    "item_key": "signal_1",
                    "review_status": "confirm",
                    "suggested_linkage_type": "direct_company_link",
                    "suggested_linkage_strength": "strong",
                    "reason": "The signal is directly tied to the company.",
                    "should_affect_scoring": True,
                }
            ],
            "audit_findings": [],
            "extraction_opportunities": [],
        }


def test_decision_review_uses_bounded_llm_request() -> None:
    settings = Settings(
        LLM_API_KEY="test-key",
        ENABLE_LLM_GENERATION=True,
        LLM_TIMEOUT_SECONDS=120,
        LLM_CHAT_MODEL="glm-4.7-flash",
    )
    service = DecisionReviewService(settings)
    fake_provider = _FakeProvider()
    service.provider = fake_provider  # type: ignore[assignment]

    result = service.review(
        company={
            "company_id": "alpha",
            "canonical_name": "Alpha Fintech",
            "display_name": "Alpha Fintech",
            "region": "Hong Kong",
            "industries": ["fintech"],
            "segments": ["SME"],
        },
        latest_state=_latest_state(),
        prospect={
            "prospect_id": "prospect:alpha",
            "priority_level": "high",
            "priority_score": 72,
            "opportunity_score": 80,
            "risk_score": 25,
        },
    )

    assert result["status"] == "ok"
    assert result["model_name"] == "glm-4.7-flash"
    assert result["linkage_reviews"][0]["title"] == "Signal 0"
    assert result["linkage_reviews"][0]["current_linkage_type"] == "direct_company_link"
    assert result["linkage_reviews"][0]["evidence_text"].startswith("Alpha Fintech expands into UAE")
    assert fake_provider.request is not None
    assert fake_provider.request["max_tokens"] == REVIEW_MAX_TOKENS
    assert fake_provider.request["timeout_seconds"] == REVIEW_TIMEOUT_SECONDS
    assert fake_provider.request["use_response_format"] is False

    payload = json.loads(fake_provider.request["messages"][0]["content"])
    assert len(payload["signals_to_review"]) == MAX_REVIEW_SIGNALS
    assert len(payload["decision_features"]) == MAX_REVIEW_FEATURES
    assert "decision_answers" not in payload
    assert "latest_state" not in payload
    assert payload["rules"][0] == "Do not produce a new score or priority."


def test_decision_review_falls_back_when_llm_disabled() -> None:
    service = DecisionReviewService(Settings(ENABLE_LLM_GENERATION=False))

    result = service.review(company={"canonical_name": "Alpha"}, latest_state=_latest_state(), prospect=None)

    assert result["status"] == "fallback"
    assert result["model_name"] is None
    assert len(result["linkage_reviews"]) == MAX_REVIEW_SIGNALS


def _latest_state() -> dict[str, Any]:
    signals = [
        {
            "title": f"Signal {index}",
            "detail": "Alpha Fintech expands into UAE with direct company evidence and merchant acquiring context.",
            "signal_type": "cross_border" if index % 2 else "growth",
            "severity": "medium",
            "linkage_type": "direct_company_link",
            "linkage_strength": "strong",
            "supports_company_scoring": True,
            "context_only": False,
        }
        for index in range(10)
    ]
    features = [
        {
            "feature_key": f"feature_{index}",
            "feature_group": "commercial_attractiveness",
            "score_contribution": index,
            "rationale": "Direct company evidence supports the feature.",
        }
        for index in range(12)
    ]
    return {
        "status": "actionable",
        "recommended_next_step": "review latest risk factors before outreach",
        "commercial_attractiveness_score": 45,
        "immediacy_score": 20,
        "product_fit_score": 25,
        "risk_penalty_score": 20,
        "evidence_confidence_score": 70,
        "coverage_flags": {
            "has_management_discussion": True,
            "has_business_events": True,
            "has_structured_metrics": True,
            "has_risk_factors": True,
        },
        "opportunity_signals": signals,
        "context_signals": [],
        "risk_signals": [],
        "decision_features": features,
        "product_fit": [
            {
                "product_name": "cross-border payments",
                "fit_score": 86,
                "rationale": "Recent expansion supports cross-border payment needs.",
            }
        ],
    }
