from __future__ import annotations

from typing import Any

from insightsync.parsing.genai_extractor import (
    GenAIExtractionConfig,
    enhance_parsed_document_with_genai,
    normalize_genai_extraction,
    select_candidate_paragraphs,
)
from insightsync.parsing.models import ParsedDocument, ParsedSection


def _parsed_report() -> ParsedDocument:
    return ParsedDocument(
        parser_name="text",
        backend_name="native",
        title="Alpha Fintech Annual Report 2025",
        text="",
        sections=[
            ParsedSection(
                heading="Management Discussion",
                text=(
                    "Management sees strong GCC expansion momentum after entering the UAE market. "
                    "The company needs tighter KYC and settlement controls for cross-border merchants."
                ),
                page_number=7,
            ),
            ParsedSection(
                heading="Operations",
                text="The company refreshed internal policies and continued daily platform maintenance.",
                page_number=9,
            ),
        ],
        metadata={"source_id": 42, "language": "en"},
    )


def test_candidate_selection_uses_title_keyword_and_light_semantic_matches() -> None:
    parsed = _parsed_report()

    candidates = select_candidate_paragraphs(parsed)

    assert candidates
    top = candidates[0]
    assert top.heading == "Management Discussion"
    assert top.evidence.document_id == "42"
    assert top.evidence.section_id == 0
    assert top.evidence.paragraph_id == 0
    assert top.evidence.page == 7
    assert "title_match" in top.selection_reasons
    assert "keyword_match" in top.selection_reasons
    assert "light_semantic_match" in top.selection_reasons


def test_normalization_rejects_unknown_or_unquoted_evidence() -> None:
    parsed = _parsed_report()
    candidates = select_candidate_paragraphs(parsed)
    raw = {
        "business_events": [
            {
                "event_type": "expansion",
                "summary": "Alpha entered the UAE market.",
                "confidence": 0.91,
                "evidence_span": {
                    "chunk_id": "missing",
                    "quoted_text": "entering the UAE market",
                },
            },
            {
                "event_type": "expansion",
                "summary": "Alpha entered the UAE market.",
                "confidence": 0.91,
                "evidence_span": {
                    "chunk_id": candidates[0].evidence.chunk_id,
                    "quoted_text": "text that does not exist in the candidate paragraph",
                },
            },
        ]
    }

    accepted, rejected = normalize_genai_extraction(raw, candidates=candidates, parsed=parsed)

    assert accepted == []
    assert len(rejected) == 2
    assert rejected[0]["reasons"] == ["unknown_chunk_id"]
    assert rejected[1]["reasons"] == ["quote_not_found_in_candidate"]


def test_management_statement_is_normalized_but_not_scoring_eligible() -> None:
    parsed = _parsed_report()
    candidates = select_candidate_paragraphs(parsed)
    raw = {
        "management_statements": [
            {
                "statement_type": "cross_border",
                "summary": "Management sees GCC expansion momentum.",
                "confidence": 0.88,
                "evidence_span": {
                    "chunk_id": candidates[0].evidence.chunk_id,
                    "quoted_text": "Management sees strong GCC expansion momentum",
                },
            }
        ]
    }

    accepted, rejected = normalize_genai_extraction(raw, candidates=candidates, parsed=parsed)

    assert rejected == []
    assert accepted[0]["fact_type"] == "management_statement"
    assert accepted[0]["scoring_eligibility"]["eligible"] is False
    assert "context_only_not_scoring_input" in accepted[0]["scoring_eligibility"]["reasons"]


def test_enhancement_merges_only_eligible_existing_parser_objects() -> None:
    parsed = _parsed_report()

    def fake_chat_json(**_kwargs: Any) -> dict[str, Any]:
        chunk_id = "s0:p0"
        return {
            "business_events": [
                {
                    "event_type": "expansion",
                    "summary": "Alpha entered the UAE market.",
                    "confidence": 0.9,
                    "evidence_span": {
                        "chunk_id": chunk_id,
                        "quoted_text": "entering the UAE market",
                    },
                }
            ],
            "management_statements": [
                {
                    "statement_type": "cross_border",
                    "summary": "Management sees GCC expansion momentum.",
                    "confidence": 0.88,
                    "evidence_span": {
                        "chunk_id": chunk_id,
                        "quoted_text": "Management sees strong GCC expansion momentum",
                    },
                }
            ],
        }

    enhanced = enhance_parsed_document_with_genai(
        parsed,
        chat_json=fake_chat_json,
        config=GenAIExtractionConfig(max_candidates=4),
    )

    assert len(enhanced.business_events) == 1
    assert enhanced.business_events[0].event_type == "expansion"
    meta = enhanced.metadata["genai_extraction"]
    assert meta["status"] == "ok"
    assert meta["accepted_count"] == 2
    statement = [item for item in meta["accepted_facts"] if item["fact_type"] == "management_statement"][0]
    assert statement["scoring_eligibility"]["eligible"] is False
