from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_API_BASE = "http://127.0.0.1:8000"


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: dict[str, Any]
    latency_ms: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a live InsightSync backend/frontend acceptance check."
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("INSIGHTSYNC_API_BASE", DEFAULT_API_BASE),
        help="Backend API base URL.",
    )
    parser.add_argument(
        "--frontend-base",
        default=os.getenv("INSIGHTSYNC_FRONTEND_BASE"),
        help="Optional frontend base URL to smoke-check routes.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    parser.add_argument(
        "--include-review",
        action="store_true",
        help="Also call the advisory LLM review endpoint.",
    )
    parser.add_argument(
        "--include-rag",
        action="store_true",
        help="Also call the prospect-scoped RAG question endpoint.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any required check fails.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api_base = args.api_base.rstrip("/")
    frontend_base = args.frontend_base.rstrip("/") if args.frontend_base else None

    results: list[CheckResult] = []
    context: dict[str, Any] = {}

    _run(results, "healthz", lambda: _check_health(api_base, args.timeout_seconds))
    _run(results, "metadata_filters", lambda: _check_metadata(api_base, args.timeout_seconds))
    _run(results, "dashboard_summary", lambda: _check_dashboard(api_base, args.timeout_seconds))
    _run(results, "signals_and_timeline", lambda: _check_signals_timeline(api_base, args.timeout_seconds))
    _run(
        results,
        "prospect_list_scorecard",
        lambda: _check_prospect_list(api_base, args.timeout_seconds, context),
    )
    _run(
        results,
        "prospect_detail_contract",
        lambda: _check_prospect_detail(api_base, args.timeout_seconds, context),
    )
    _run(
        results,
        "prospect_evidence_brief_copilot",
        lambda: _check_prospect_workspace(api_base, args.timeout_seconds, context),
    )
    if args.include_review:
        _run(
            results,
            "prospect_review_optional",
            lambda: _check_prospect_review(api_base, args.timeout_seconds, context),
        )
    if args.include_rag:
        _run(
            results,
            "prospect_rag_optional",
            lambda: _check_prospect_rag(api_base, args.timeout_seconds, context),
        )
    if frontend_base:
        _run(
            results,
            "frontend_routes",
            lambda: _check_frontend(frontend_base, args.timeout_seconds, context),
        )

    summary = {
        "api_base": api_base,
        "frontend_base": frontend_base,
        "passed": all(result.passed for result in results),
        "passed_count": sum(1 for result in results if result.passed),
        "failed": [result.name for result in results if not result.passed],
        "results": [asdict(result) for result in results],
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.strict and summary["failed"]:
        return 1
    return 0


def _run(results: list[CheckResult], name: str, fn: Any) -> None:
    started = time.perf_counter()
    try:
        result = fn()
        latency_ms = round((time.perf_counter() - started) * 1000)
        results.append(
            CheckResult(
                name=name,
                passed=bool(result.get("passed")),
                details=result.get("details", {}),
                latency_ms=latency_ms,
            )
        )
    except Exception as exc:  # noqa: BLE001 - acceptance output should capture all failures.
        latency_ms = round((time.perf_counter() - started) * 1000)
        results.append(
            CheckResult(
                name=name,
                passed=False,
                details={"error": str(exc)},
                latency_ms=latency_ms,
            )
        )


def _check_health(api_base: str, timeout: float) -> dict[str, Any]:
    payload = _get_json(api_base, "/healthz", timeout)
    return _assert("status is ok", payload.get("status") == "ok", payload)


def _check_metadata(api_base: str, timeout: float) -> dict[str, Any]:
    payload = _get_json(api_base, "/api/metadata/filters", timeout)
    required = ["regions", "industries", "signal_types", "sources", "datasets"]
    missing = [key for key in required if not isinstance(payload.get(key), list)]
    empty = [key for key in required if isinstance(payload.get(key), list) and not payload[key]]
    return _assert(
        "metadata filters are populated",
        not missing and not empty,
        {"missing": missing, "empty": empty, "counts": {key: len(payload.get(key, [])) for key in required}},
    )


def _check_dashboard(api_base: str, timeout: float) -> dict[str, Any]:
    summary = _get_json(api_base, "/api/dashboard/summary", timeout)
    overview = _get_json(api_base, "/api/dashboard/overview", timeout)
    checks = {
        "lead_pool_positive": summary.get("lead_pool", 0) > 0,
        "overview_counts_present": all(
            key in overview
            for key in [
                "ingestion_runs",
                "intelligence_records",
                "trigger_signals",
                "timeline_events",
                "generated_insights",
            ]
        ),
        "overview_distributions_present": isinstance(overview.get("source_distribution"), list)
        and isinstance(overview.get("signal_type_distribution"), list),
    }
    return _assert("dashboard endpoints respond", all(checks.values()), {"checks": checks, "summary": summary})


def _check_signals_timeline(api_base: str, timeout: float) -> dict[str, Any]:
    signals = _get_json(api_base, "/api/signals?limit=5", timeout)
    timeline = _get_json(api_base, "/api/timeline?limit=5", timeout)
    checks = {
        "signals_items": isinstance(signals.get("items"), list),
        "timeline_items": isinstance(timeline.get("items"), list),
    }
    return _assert(
        "signals and timeline endpoints respond",
        all(checks.values()),
        {
            "checks": checks,
            "signal_count": len(signals.get("items", [])),
            "timeline_count": len(timeline.get("items", [])),
        },
    )


def _check_prospect_list(api_base: str, timeout: float, context: dict[str, Any]) -> dict[str, Any]:
    payload = _get_json(api_base, "/api/prospects?limit=5", timeout)
    items = payload.get("items") or []
    top = items[0] if items else {}
    score_breakdown = top.get("score_breakdown") or {}
    score_inputs = score_breakdown.get("score_inputs") or {}
    context["prospect_id"] = top.get("prospect_id")

    checks = {
        "has_prospects": bool(items),
        "has_decision_answers": bool(top.get("decision_answers")),
        "has_workflow_state": isinstance(top.get("workflow_state"), dict),
        "scorecard_version": bool(score_breakdown.get("scorecard_version")),
        "llm_not_final_scorer": score_breakdown.get("llm_score_assignment") == "not_used_for_final_score",
        "calibration_status_present": bool(score_breakdown.get("calibration_status")),
        "score_inputs_match": score_inputs.get("priority_score") == top.get("priority_score"),
        "linkage_quality_present": isinstance(score_breakdown.get("linkage_quality"), dict),
        "governance_flags_present": isinstance(score_breakdown.get("governance_flags"), list),
    }
    return _assert(
        "prospect list exposes auditable scorecard",
        all(checks.values()),
        {
            "checks": checks,
            "prospect_id": top.get("prospect_id"),
            "priority_level": top.get("priority_level"),
            "priority_score": top.get("priority_score"),
            "scorecard_version": score_breakdown.get("scorecard_version"),
            "calibration_status": score_breakdown.get("calibration_status"),
        },
    )


def _check_prospect_detail(api_base: str, timeout: float, context: dict[str, Any]) -> dict[str, Any]:
    prospect_id = _require_prospect_id(context)
    payload = _get_json(api_base, f"/api/prospects/{quote(prospect_id, safe='')}", timeout)
    latest_state = payload.get("latest_state") or {}
    prospect = payload.get("prospect") or {}
    checks = {
        "company_profile": isinstance(payload.get("company"), dict),
        "latest_state": isinstance(latest_state, dict),
        "coverage_flags": isinstance(latest_state.get("coverage_flags"), dict),
        "decision_answers": bool(prospect.get("decision_answers") or latest_state.get("decision_answers")),
        "recent_signals_list": isinstance(payload.get("recent_signals"), list),
        "recent_timeline_list": isinstance(payload.get("recent_timeline"), list),
        "recent_insights_list": isinstance(payload.get("recent_insights"), list),
        "recent_documents_list": isinstance(payload.get("recent_documents"), list),
        "workflow_state": isinstance(payload.get("workflow_state"), dict),
    }
    return _assert(
        "prospect detail exposes company, evidence, workflow, and decision state",
        all(checks.values()),
        {
            "checks": checks,
            "prospect_id": prospect_id,
            "company_id": prospect.get("company_id"),
            "status": latest_state.get("status"),
            "recent_signal_count": len(payload.get("recent_signals", [])),
            "recent_document_count": len(payload.get("recent_documents", [])),
            "recent_insight_count": len(payload.get("recent_insights", [])),
        },
    )


def _check_prospect_workspace(api_base: str, timeout: float, context: dict[str, Any]) -> dict[str, Any]:
    prospect_id = _require_prospect_id(context)
    encoded = quote(prospect_id, safe="")
    evidence = _get_json(api_base, f"/api/prospects/{encoded}/evidence", timeout)
    brief = _get_json(api_base, f"/api/prospects/{encoded}/brief", timeout)
    copilot = _get_json(api_base, f"/api/prospects/{encoded}/copilot", timeout)
    checks = {
        "evidence_summary": isinstance(evidence.get("evidence_summary"), dict),
        "coverage_flags": isinstance(evidence.get("coverage_flags"), dict),
        "brief_summary": bool(brief.get("summary")),
        "brief_decision_answers": isinstance(brief.get("decision_answers"), list),
        "copilot_questions": bool(copilot.get("suggested_questions")),
    }
    return _assert(
        "prospect workspace endpoints are frontend-ready",
        all(checks.values()),
        {
            "checks": checks,
            "prospect_id": prospect_id,
            "parsed_document_count": evidence.get("evidence_summary", {}).get("parsed_document_count"),
            "copilot_question_count": len(copilot.get("suggested_questions", [])),
        },
    )


def _check_prospect_review(api_base: str, timeout: float, context: dict[str, Any]) -> dict[str, Any]:
    prospect_id = _require_prospect_id(context)
    payload = _get_json(api_base, f"/api/prospects/{quote(prospect_id, safe='')}/review", timeout)
    checks = {
        "review_summary": bool(payload.get("review_summary")),
        "linkage_reviews": isinstance(payload.get("linkage_reviews"), list),
        "audit_findings": isinstance(payload.get("audit_findings"), list),
    }
    return _assert("review endpoint responds", all(checks.values()), {"checks": checks})


def _check_prospect_rag(api_base: str, timeout: float, context: dict[str, Any]) -> dict[str, Any]:
    prospect_id = _require_prospect_id(context)
    payload = _post_json(
        api_base,
        f"/api/prospects/{quote(prospect_id, safe='')}/question",
        {"question": "Why is this company worth reviewing now?", "include_chunks": False},
        timeout,
    )
    checks = {
        "status_present": bool(payload.get("status")),
        "answer_present": bool(payload.get("answer")),
        "citations_list": isinstance(payload.get("citations"), list),
    }
    return _assert("prospect RAG endpoint responds", all(checks.values()), {"checks": checks})


def _check_frontend(frontend_base: str, timeout: float, context: dict[str, Any]) -> dict[str, Any]:
    prospect_id = context.get("prospect_id") or "p1"
    routes = [
        "/",
        "/prospects",
        "/signals",
        f"/prospects/{quote(str(prospect_id), safe='')}",
    ]
    statuses = {route: _get_status(frontend_base, route, timeout) for route in routes}
    return _assert(
        "frontend routes return 200",
        all(status == 200 for status in statuses.values()),
        {"statuses": statuses},
    )


def _require_prospect_id(context: dict[str, Any]) -> str:
    prospect_id = context.get("prospect_id")
    if not prospect_id:
        raise RuntimeError("No prospect_id found from prospect list check.")
    return str(prospect_id)


def _assert(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"passed": passed, "details": {"name": name, **details}}


def _get_json(base: str, path: str, timeout: float) -> dict[str, Any]:
    data = _request(base, path, timeout=timeout)
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} returned invalid JSON: {exc}") from exc


def _post_json(base: str, path: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = _request(
        base,
        path,
        timeout=timeout,
        method="POST",
        body=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} returned invalid JSON: {exc}") from exc


def _get_status(base: str, path: str, timeout: float) -> int:
    _request(base, path, timeout=timeout)
    return 200


def _request(
    base: str,
    path: str,
    *,
    timeout: float,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    url = f"{base.rstrip('/')}{path}"
    request = Request(url, data=body, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local/dev acceptance URL is user supplied.
            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                raise RuntimeError(f"{url} returned HTTP {status}")
            return response.read()
    except HTTPError as exc:
        raise RuntimeError(f"{url} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"{url} is unreachable: {exc.reason}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
