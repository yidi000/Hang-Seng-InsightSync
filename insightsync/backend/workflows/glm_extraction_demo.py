from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import get_settings
from insightsync.backend.services.genai_extraction_view import build_genai_extraction_view_from_raw
from insightsync.parsing import GenAIExtractionConfig, ParseRequest, parse_content, run_genai_extraction
from insightsync.parsing.genai_extractor import CandidateParagraph
from insightsync.parsing.utils import normalize_text

CASE_PATH = Path("insightsync/data/evaluation/genai_extraction_cases.json")

ChatJSONCallable = Callable[..., dict[str, Any]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GLM-assisted extraction against multilingual eval cases.")
    parser.add_argument("--cases-path", type=Path, default=CASE_PATH)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--mock", action="store_true", help="Use fixture model outputs instead of calling GLM.")
    parser.add_argument("--include-raw", action="store_true", help="Include raw model JSON in output.")
    parser.add_argument("--api-preview", action="store_true", help="Include API-shaped genai_extraction metadata.")
    parser.add_argument("--delay-seconds", type=float, default=0.0, help="Sleep between live cases.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when expected checks fail.")
    return parser


def load_cases(path: Path = CASE_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(
    case: dict[str, Any],
    *,
    chat_json: ChatJSONCallable,
    max_candidates: int = 8,
    include_raw: bool = False,
    api_preview: bool = False,
) -> dict[str, Any]:
    parsed = parse_content(
        ParseRequest(
            source_name=case.get("source_name") or "genai_extraction_eval",
            dataset=case.get("dataset") or "company_reports",
            title=case["title"],
            language=case["language"],
            content=case["content"],
            metadata={
                "document_id": case["case_id"],
                "language": case["language"],
            },
        )
    )
    before_counts = _parsed_counts(parsed)

    started = time.perf_counter()
    run = run_genai_extraction(
        parsed,
        chat_json=chat_json,
        config=GenAIExtractionConfig(max_candidates=max_candidates),
    )
    latency_ms = round((time.perf_counter() - started) * 1000)

    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "language": case["language"],
        "title": case["title"],
        "status": run.status,
        "latency_ms": latency_ms,
        "native_parser_counts_before_genai": before_counts,
        "candidate_count": len(run.candidates),
        "candidates": [_candidate_payload(candidate) for candidate in run.candidates],
        "accepted_facts": run.accepted_facts,
        "rejected_facts": run.rejected_facts,
        "eligible_merge_counts": _eligible_merge_counts(run.accepted_facts),
    }
    if run.error:
        result["error"] = run.error
    if run.reason:
        result["reason"] = run.reason
    if include_raw:
        result["raw_response"] = run.raw_response
    if api_preview:
        result["api_preview"] = build_genai_extraction_view_from_raw(
            run.as_metadata(include_raw_response=include_raw)
        )

    result["checks"] = evaluate_result(case, result)
    result["passed"] = run.status == "ok" and all(check["passed"] for check in result["checks"])
    return result


def evaluate_result(case: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    expected = case.get("expected", {})
    candidates = result.get("candidates", [])
    facts = _normalized_facts(result)
    checks: list[dict[str, Any]] = [
        {
            "name": "candidate_sections_found",
            "passed": bool(candidates),
            "details": {"candidate_count": len(candidates)},
        }
    ]
    checks.append(
        _subset_check(
            "expected_quote_substrings_in_candidates",
            expected.get("quote_substrings", []),
            _candidate_text(candidates),
        )
    )
    checks.append(
        _set_subset_check(
            "expected_fact_types_extracted",
            expected.get("fact_types", []),
            [fact.get("fact_type") for fact in facts],
        )
    )
    checks.append(
        _set_subset_check(
            "expected_metric_names_extracted",
            expected.get("metric_names", []),
            [fact.get("name") for fact in facts if fact.get("fact_type") == "metric"],
        )
    )
    checks.append(
        _set_subset_check(
            "expected_business_event_types_extracted",
            expected.get("business_event_types", []),
            [fact.get("event_type") for fact in facts if fact.get("fact_type") == "business_event"],
        )
    )
    checks.append(
        _set_subset_check(
            "expected_risk_categories_extracted",
            expected.get("risk_categories", []),
            [fact.get("category") for fact in facts if fact.get("fact_type") == "risk_factor"],
        )
    )
    checks.append(_evidence_check("normalized_evidence_quotes_valid", facts, candidates))
    checks.append(_eligibility_gate_check(result.get("accepted_facts", [])))
    checks.append(
        _context_only_check(
            "context_only_fact_types_not_scoring_eligible",
            expected.get("context_only_fact_types", []),
            facts,
        )
    )
    return checks


def mock_chat_json_for_case(case: dict[str, Any]) -> ChatJSONCallable:
    def _chat_json(**kwargs: Any) -> dict[str, Any]:
        messages = kwargs.get("messages") or []
        prompt = json.loads(messages[0]["content"]) if messages else {}
        evidence_spans = prompt.get("allowed_evidence_spans") or []
        primary_chunk_id = evidence_spans[0]["chunk_id"] if evidence_spans else ""
        return _replace_placeholders(case["mock_model_output"], primary_chunk_id=primary_chunk_id)

    return _chat_json


def main() -> int:
    args = build_parser().parse_args()
    cases = load_cases(args.cases_path)
    if args.case_id:
        wanted = set(args.case_id)
        cases = [case for case in cases if case["case_id"] in wanted]
    if not cases:
        print("No matching GenAI extraction eval cases.", file=sys.stderr)
        return 2

    provider: OpenAIProvider | None = None
    if not args.mock:
        settings = get_settings()
        if not settings.llm_enabled:
            print(
                "GLM extraction demo skipped: set ENABLE_LLM_GENERATION=true and LLM_API_KEY first, or pass --mock.",
                file=sys.stderr,
            )
            return 2
        provider = OpenAIProvider(settings)

    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        chat_json = mock_chat_json_for_case(case) if args.mock else provider.chat_json  # type: ignore[union-attr]
        results.append(
            run_case(
                case,
                chat_json=chat_json,
                max_candidates=max(1, int(args.max_candidates)),
                include_raw=args.include_raw,
                api_preview=args.api_preview,
            )
        )
        if not args.mock and args.delay_seconds > 0 and index < len(cases) - 1:
            time.sleep(args.delay_seconds)

    summary = {
        "mode": "mock" if args.mock else "live_glm",
        "case_count": len(results),
        "passed_count": sum(1 for result in results if result["passed"]),
        "failed_case_ids": [result["case_id"] for result in results if not result["passed"]],
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.strict and summary["failed_case_ids"]:
        return 1
    return 0


def _parsed_counts(parsed: Any) -> dict[str, int]:
    return {
        "sections": len(parsed.sections),
        "metrics": len(parsed.metrics),
        "risk_factors": len(parsed.risk_factors),
        "business_events": len(parsed.business_events),
        "has_management_discussion": int(parsed.management_discussion is not None),
    }


def _candidate_payload(candidate: CandidateParagraph) -> dict[str, Any]:
    payload = candidate.prompt_payload()
    payload["score"] = candidate.score
    payload["text_preview"] = _truncate(candidate.text, 500)
    payload.pop("text", None)
    return payload


def _eligible_merge_counts(accepted_facts: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        fact["fact_type"]
        for fact in accepted_facts
        if fact.get("scoring_eligibility", {}).get("eligible")
    )
    return {
        "metrics": counts.get("metric", 0),
        "risk_factors": counts.get("risk_factor", 0),
        "business_events": counts.get("business_event", 0),
    }


def _normalized_facts(result: dict[str, Any]) -> list[dict[str, Any]]:
    facts = list(result.get("accepted_facts", []))
    for rejected in result.get("rejected_facts", []):
        normalized = rejected.get("normalized")
        if isinstance(normalized, dict) and "duplicate_existing_fact" in rejected.get("reasons", []):
            facts.append(normalized)
    return facts


def _candidate_text(candidates: list[dict[str, Any]]) -> str:
    return "\n".join(
        normalize_text(candidate.get("quoted_text") or candidate.get("text_preview"))
        for candidate in candidates
    )


def _candidate_text_by_chunk(candidates: list[dict[str, Any]]) -> dict[str, str]:
    return {
        normalize_text(candidate.get("chunk_id")): normalize_text(candidate.get("quoted_text") or candidate.get("text_preview"))
        for candidate in candidates
    }


def _subset_check(name: str, expected: list[str], text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    missing = [item for item in expected if normalize_text(item) not in normalized]
    return {
        "name": name,
        "passed": not missing,
        "details": {"expected": expected, "missing": missing},
    }


def _set_subset_check(name: str, expected: list[str], actual: list[Any]) -> dict[str, Any]:
    expected_set = {normalize_text(item).lower() for item in expected if normalize_text(item)}
    actual_set = {normalize_text(item).lower() for item in actual if normalize_text(item)}
    missing = sorted(expected_set - actual_set)
    return {
        "name": name,
        "passed": not missing,
        "details": {"expected": sorted(expected_set), "actual": sorted(actual_set), "missing": missing},
    }


def _evidence_check(name: str, facts: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_chunk = _candidate_text_by_chunk(candidates)
    errors: list[dict[str, str]] = []
    for fact in facts:
        span = fact.get("evidence_span") or {}
        chunk_id = normalize_text(span.get("chunk_id"))
        quote = normalize_text(span.get("quoted_text"))
        candidate_text = by_chunk.get(chunk_id, "")
        if not chunk_id or not quote or quote not in candidate_text:
            errors.append(
                {
                    "fact_type": normalize_text(fact.get("fact_type")),
                    "chunk_id": chunk_id,
                    "quote": quote,
                }
            )
    return {"name": name, "passed": not errors, "details": {"errors": errors}}


def _eligibility_gate_check(accepted_facts: list[dict[str, Any]]) -> dict[str, Any]:
    scoring_types = {"metric", "risk_factor", "business_event"}
    context_types = {"management_statement", "opportunity_signal_candidate"}
    errors: list[dict[str, str]] = []
    for fact in accepted_facts:
        fact_type = normalize_text(fact.get("fact_type"))
        eligible = bool(fact.get("scoring_eligibility", {}).get("eligible"))
        if fact_type in scoring_types and not eligible:
            errors.append({"fact_type": fact_type, "reason": "scoring_fact_not_eligible"})
        if fact_type in context_types and eligible:
            errors.append({"fact_type": fact_type, "reason": "context_fact_marked_eligible"})
    return {"name": "scoring_eligibility_gate_valid", "passed": not errors, "details": {"errors": errors}}


def _context_only_check(name: str, expected_types: list[str], facts: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    for fact_type in expected_types:
        matching = [fact for fact in facts if normalize_text(fact.get("fact_type")) == fact_type]
        if not matching:
            errors.append({"fact_type": fact_type, "reason": "missing"})
            continue
        if any(fact.get("scoring_eligibility", {}).get("eligible") for fact in matching):
            errors.append({"fact_type": fact_type, "reason": "marked_eligible"})
    return {"name": name, "passed": not errors, "details": {"errors": errors}}


def _replace_placeholders(value: Any, *, primary_chunk_id: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_placeholders(item, primary_chunk_id=primary_chunk_id) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_placeholders(item, primary_chunk_id=primary_chunk_id) for item in value]
    if isinstance(value, str):
        return value.replace("$primary_chunk_id", primary_chunk_id)
    return copy.deepcopy(value)


def _truncate(value: str, limit: int) -> str:
    normalized = normalize_text(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main())
