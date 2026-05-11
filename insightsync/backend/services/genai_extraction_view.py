from __future__ import annotations

import json
from typing import Any


def build_genai_extraction_view(metadata_json: Any) -> dict[str, Any] | None:
    """Build the API-facing GenAI extraction audit view from parsed document metadata."""

    metadata = _json_field(metadata_json, {})
    if not isinstance(metadata, dict):
        return None
    return build_genai_extraction_view_from_raw(metadata.get("genai_extraction"))


def build_genai_extraction_view_from_raw(raw: Any) -> dict[str, Any] | None:
    """Build the API-facing GenAI extraction audit view from raw run metadata."""

    if not isinstance(raw, dict):
        return None
    accepted_facts = raw.get("accepted_facts") if isinstance(raw.get("accepted_facts"), list) else []
    rejected_facts = raw.get("rejected_facts") if isinstance(raw.get("rejected_facts"), list) else []
    eligible_counts: dict[str, int] = {}
    context_only_count = 0
    for fact in accepted_facts:
        if not isinstance(fact, dict):
            continue
        fact_type = str(fact.get("fact_type") or "unknown")
        eligibility = fact.get("scoring_eligibility") if isinstance(fact.get("scoring_eligibility"), dict) else {}
        if eligibility.get("eligible") is True:
            eligible_counts[fact_type] = eligible_counts.get(fact_type, 0) + 1
        else:
            context_only_count += 1

    rejected_reason_counts: dict[str, int] = {}
    for fact in rejected_facts:
        if not isinstance(fact, dict):
            continue
        reasons = fact.get("reasons") if isinstance(fact.get("reasons"), list) else []
        for reason in reasons:
            reason_key = str(reason)
            rejected_reason_counts[reason_key] = rejected_reason_counts.get(reason_key, 0) + 1

    return {
        "status": raw.get("status"),
        "prompt_version": raw.get("prompt_version"),
        "candidate_count": _int_field(raw.get("candidate_count")),
        "accepted_count": _int_field(raw.get("accepted_count")),
        "rejected_count": _int_field(raw.get("rejected_count")),
        "scoring_eligible_counts": eligible_counts,
        "context_only_count": context_only_count,
        "rejected_reason_counts": rejected_reason_counts,
        "accepted_facts": [fact for fact in accepted_facts if isinstance(fact, dict)],
        "rejected_facts": [fact for fact in rejected_facts if isinstance(fact, dict)],
    }


def _json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _int_field(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
