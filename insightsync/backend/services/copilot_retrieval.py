from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CopilotContext = Literal["prospect", "market", "signal", "global"]


@dataclass(frozen=True)
class RetrievalRequest:
    message: str
    context: str
    filters: dict[str, Any]
    top_k: int


@dataclass(frozen=True)
class RetrievalPlan:
    message: str
    context: CopilotContext
    sql_sources: tuple[str, ...]
    required_filters: dict[str, Any]
    top_k: int
    use_vector: bool


def build_retrieval_plan(request: RetrievalRequest) -> RetrievalPlan:
    """Build a structured/vector retrieval plan for Copilot evidence lookup."""

    context = _normalize_context(request.context)
    filters = {key: value for key, value in request.filters.items() if value not in (None, "")}
    sql_sources = _sql_sources_for_context(context)
    required_filters = _required_filters_for_context(context=context, filters=filters)
    return RetrievalPlan(
        message=request.message,
        context=context,
        sql_sources=sql_sources,
        required_filters=required_filters,
        top_k=max(1, request.top_k),
        use_vector=True,
    )


def _normalize_context(context: str) -> CopilotContext:
    if context in {"prospect", "market", "signal", "global"}:
        return context  # type: ignore[return-value]
    return "global"


def _sql_sources_for_context(context: CopilotContext) -> tuple[str, ...]:
    if context == "prospect":
        return ("prospect_evidence_items", "prospect_signals", "prospect_scores", "client_one_view_timeline")
    if context == "market":
        return ("market_opportunity_snapshots", "prospect_evidence_items")
    if context == "signal":
        return ("prospect_signals", "prospect_evidence_items")
    return ("prospect_evidence_items", "prospect_signals", "market_opportunity_snapshots")


def _required_filters_for_context(*, context: CopilotContext, filters: dict[str, Any]) -> dict[str, Any]:
    allowed_by_context = {
        "prospect": (
            "prospect_id",
            "company_id",
            "source",
            "dataset",
            "date_from",
            "date_to",
            "industry",
            "region",
            "size_band",
        ),
        "market": (
            "region",
            "industry",
            "size_band",
            "signal_type",
            "source",
            "dataset",
            "date_from",
            "date_to",
        ),
        "signal": (
            "prospect_id",
            "company_id",
            "signal_type",
            "signal_subtype",
            "source",
            "dataset",
            "date_from",
            "date_to",
            "industry",
            "region",
            "size_band",
        ),
        "global": ("source", "dataset", "date_from", "date_to", "industry", "region", "signal_type"),
    }
    return {key: filters[key] for key in allowed_by_context[context] if key in filters}
