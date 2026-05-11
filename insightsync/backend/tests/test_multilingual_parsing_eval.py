from __future__ import annotations

import json
from pathlib import Path

from insightsync.parsing import ParseRequest, parse_content


CASE_PATH = Path("insightsync/data/evaluation/multilingual_parsing_cases.json")


def _cases() -> list[dict]:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def test_multilingual_parsing_evaluation_cases() -> None:
    cases = _cases()
    assert cases

    for case in cases:
        parsed = parse_content(
            ParseRequest(
                source_name="multilingual_eval",
                dataset="parsing_cases",
                title=case["title"],
                language=case["language"],
                content=case["content"],
            )
        )
        expected = case["expected"]
        metric_names = {metric.name for metric in parsed.metrics}
        risk_categories = {risk.category for risk in parsed.risk_factors}
        event_types = {event.event_type for event in parsed.business_events}

        assert expected["has_management_discussion"] == (parsed.management_discussion is not None), case["case_id"]
        assert set(expected["metrics"]).issubset(metric_names), case["case_id"]
        assert set(expected["risk_categories"]).issubset(risk_categories), case["case_id"]
        assert set(expected["business_events"]).issubset(event_types), case["case_id"]
