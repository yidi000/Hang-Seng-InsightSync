from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .models import BusinessEvent, ExtractedMetric, ManagementDiscussion, ParsedDocument, ParsedSection, RiskFactor
from .utils import normalize_text

ChatJSONCallable = Callable[..., dict[str, Any]]

PROMPT_VERSION = "genai-section-extraction-v0.1"

_TITLE_MARKERS = (
    "management discussion",
    "management review",
    "business review",
    "financial review",
    "outlook",
    "strategy",
    "risk factors",
    "principal risks",
    "operating review",
    "liquidity",
    "capital",
    "\u7ba1\u7406\u5c42\u8ba8\u8bba",
    "\u7ba1\u7406\u5c64\u8a0e\u8ad6",
    "\u4e1a\u52a1\u56de\u987e",
    "\u696d\u52d9\u56de\u9867",
    "\u524d\u666f",
    "\u98ce\u9669\u56e0\u7d20",
    "\u98a8\u96aa\u56e0\u7d20",
)
_KEYWORD_MARKERS = (
    "cross-border",
    "cross border",
    "overseas",
    "new market",
    "expansion",
    "entered",
    "launched",
    "partnership",
    "funding",
    "financing",
    "liquidity",
    "capital support",
    "regulatory",
    "compliance",
    "licensing",
    "kyc",
    "\u8de8\u5883",
    "\u6d77\u5916",
    "\u6269\u5f20",
    "\u64f4\u5f35",
    "\u65b0\u5e02\u573a",
    "\u65b0\u5e02\u5834",
    "\u878d\u8d44",
    "\u878d\u8cc7",
    "\u6d41\u52a8\u6027",
    "\u6d41\u52d5\u6027",
    "\u76d1\u7ba1",
    "\u76e3\u7ba1",
    "\u5408\u89c4",
    "\u5408\u898f",
)
_SEMANTIC_INTENT_MARKERS = (
    "entered a new market",
    "served a new geography",
    "merchant settlement",
    "payment acceptance",
    "capital planning",
    "working capital",
    "funding needs",
    "settlement controls",
    "regulatory reporting",
    "\u724c\u7167",
    "\u71df\u8fd0\u8d44\u91d1",
    "\u71df\u904b\u8cc7\u91d1",
    "\u7ed3\u7b97",
    "\u7d50\u7b97",
)
_GENERIC_PHRASES = (
    "strong momentum",
    "good opportunity",
    "positive outlook",
    "market opportunities",
    "business opportunities",
    "\u826f\u597d\u673a\u9047",
    "\u826f\u597d\u6a5f\u9047",
)
_METRIC_NAME_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "revenue",
        (
            "revenue",
            "sales",
            "turnover",
            "\u8425\u4e1a\u6536\u5165",
            "\u71df\u696d\u6536\u5165",
            "\u8425\u6536",
            "\u71df\u6536",
        ),
    ),
    (
        "net profit",
        (
            "net profit",
            "net income",
            "\u51c0\u5229\u6da6",
            "\u6de8\u5229\u6f64",
        ),
    ),
)


@dataclass(slots=True)
class GenAIEvidenceSpan:
    document_id: str | None
    section_id: int
    paragraph_id: int
    chunk_id: str
    page: int | None
    quoted_text: str
    language: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "section_id": self.section_id,
            "paragraph_id": self.paragraph_id,
            "chunk_id": self.chunk_id,
            "page": self.page,
            "quoted_text": self.quoted_text,
            "language": self.language,
        }


@dataclass(slots=True)
class CandidateParagraph:
    evidence: GenAIEvidenceSpan
    heading: str
    text: str
    selection_reasons: list[str] = field(default_factory=list)
    score: int = 0

    def prompt_payload(self) -> dict[str, Any]:
        return {
            **self.evidence.as_dict(),
            "heading": self.heading,
            "text": self.text,
            "selection_reasons": self.selection_reasons,
        }


@dataclass(slots=True)
class GenAIExtractionConfig:
    max_candidates: int = 8
    max_candidate_chars: int = 1200
    min_confidence: float = 0.6
    merge_management_discussion: bool = False
    include_raw_response: bool = False
    prompt_version: str = PROMPT_VERSION


@dataclass(slots=True)
class GenAIExtractionRun:
    status: str
    prompt_version: str
    candidates: list[CandidateParagraph]
    raw_response: dict[str, Any] | None = None
    accepted_facts: list[dict[str, Any]] = field(default_factory=list)
    rejected_facts: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    reason: str | None = None

    def as_metadata(self, *, include_raw_response: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "prompt_version": self.prompt_version,
            "candidate_count": len(self.candidates),
            "accepted_count": len(self.accepted_facts),
            "rejected_count": len(self.rejected_facts),
            "accepted_facts": self.accepted_facts,
            "rejected_facts": self.rejected_facts,
        }
        if self.reason:
            payload["reason"] = self.reason
        if self.error:
            payload["error"] = self.error
        if include_raw_response:
            payload["raw_response"] = self.raw_response
        return payload


def enhance_parsed_document_with_genai(
    parsed: ParsedDocument,
    *,
    chat_json: ChatJSONCallable,
    config: GenAIExtractionConfig | None = None,
) -> ParsedDocument:
    """Enhance parsed outputs through a bounded GenAI extraction adapter.

    The adapter keeps GenAI output behind a normalization and eligibility gate.
    It never assigns scores. Eligible facts are converted only into existing
    parser dataclasses, and full evidence/eligibility records are kept in
    parsed.metadata["genai_extraction"].
    """

    cfg = config or GenAIExtractionConfig()
    run = run_genai_extraction(parsed, chat_json=chat_json, config=cfg)
    if run.status == "skipped":
        parsed.metadata["genai_extraction"] = run.as_metadata(include_raw_response=cfg.include_raw_response)
        return parsed
    if run.status == "model_error":
        parsed.warnings.append(f"GenAI extraction skipped after model error: {run.error}")
        parsed.metadata["genai_extraction"] = run.as_metadata(include_raw_response=cfg.include_raw_response)
        return parsed

    _merge_eligible_facts(parsed, run.accepted_facts, config=cfg)
    parsed.metadata["genai_extraction"] = run.as_metadata(include_raw_response=cfg.include_raw_response)
    return parsed


def run_genai_extraction(
    parsed: ParsedDocument,
    *,
    chat_json: ChatJSONCallable,
    config: GenAIExtractionConfig | None = None,
) -> GenAIExtractionRun:
    """Run bounded GenAI extraction without mutating the parsed document."""

    cfg = config or GenAIExtractionConfig()
    candidates = select_candidate_paragraphs(parsed, config=cfg)
    if not candidates:
        return GenAIExtractionRun(
            status="skipped",
            prompt_version=cfg.prompt_version,
            candidates=[],
            reason="no_candidate_sections",
        )

    payload = _build_prompt_payload(parsed, candidates=candidates, config=cfg)
    try:
        raw = chat_json(
            system_prompt=_system_prompt(),
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
    except Exception as exc:  # noqa: BLE001
        return GenAIExtractionRun(
            status="model_error",
            prompt_version=cfg.prompt_version,
            candidates=candidates,
            error=str(exc),
        )

    accepted, rejected = normalize_genai_extraction(raw, candidates=candidates, parsed=parsed, config=cfg)
    return GenAIExtractionRun(
        status="ok",
        prompt_version=cfg.prompt_version,
        candidates=candidates,
        raw_response=raw,
        accepted_facts=accepted,
        rejected_facts=rejected,
    )


def select_candidate_paragraphs(
    parsed: ParsedDocument,
    *,
    config: GenAIExtractionConfig | None = None,
) -> list[CandidateParagraph]:
    cfg = config or GenAIExtractionConfig()
    document_id = _document_id(parsed)
    language = parsed.metadata.get("language") or parsed.metadata.get("lang")
    sections = parsed.sections or [ParsedSection(heading=parsed.title or "Document", text=parsed.text)]
    candidates: list[CandidateParagraph] = []

    for section_index, section in enumerate(sections):
        heading = normalize_text(section.heading) or f"Section {section_index}"
        heading_score, heading_reasons = _score_text(heading, heading=True)
        paragraphs = _paragraphs(section.text)
        for paragraph_index, paragraph in enumerate(paragraphs):
            paragraph_score, paragraph_reasons = _score_text(paragraph, heading=False)
            score = heading_score + paragraph_score
            reasons = [*heading_reasons, *paragraph_reasons]
            if score <= 0:
                continue
            text = _truncate(normalize_text(paragraph), cfg.max_candidate_chars)
            if len(text) < 40:
                continue
            chunk_id = f"s{section_index}:p{paragraph_index}"
            evidence = GenAIEvidenceSpan(
                document_id=document_id,
                section_id=section_index,
                paragraph_id=paragraph_index,
                chunk_id=chunk_id,
                page=section.page_number,
                quoted_text=text,
                language=language,
            )
            candidates.append(
                CandidateParagraph(
                    evidence=evidence,
                    heading=heading,
                    text=text,
                    selection_reasons=sorted(set(reasons)),
                    score=score,
                )
            )

    candidates.sort(key=lambda item: (-item.score, item.evidence.section_id, item.evidence.paragraph_id))
    return candidates[: cfg.max_candidates]


def normalize_genai_extraction(
    raw: dict[str, Any],
    *,
    candidates: list[CandidateParagraph],
    parsed: ParsedDocument,
    config: GenAIExtractionConfig | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cfg = config or GenAIExtractionConfig()
    allowed = {item.evidence.chunk_id: item for item in candidates}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_keys = _existing_fact_keys(parsed)

    for fact_type, item in _iter_raw_facts(raw):
        normalized, reject_reasons = _normalize_fact(
            fact_type,
            item,
            allowed=allowed,
            config=cfg,
            seen_keys=seen_keys,
        )
        if normalized is None:
            rejected.append({"fact_type": fact_type, "raw": item, "reasons": reject_reasons})
            continue
        fact_key = _fact_key(normalized)
        if fact_key in seen_keys:
            normalized["scoring_eligibility"]["eligible"] = False
            normalized["scoring_eligibility"]["reasons"].append("duplicate_existing_fact")
            rejected.append(
                {
                    "fact_type": fact_type,
                    "raw": item,
                    "normalized": normalized,
                    "reasons": ["duplicate_existing_fact"],
                }
            )
            continue
        seen_keys.add(fact_key)
        accepted.append(normalized)

    return accepted, rejected


def _system_prompt() -> str:
    return (
        "You extract structured commercial-banking facts from supplied candidate paragraphs. "
        "Handle English, Simplified Chinese, Traditional Chinese, and Cantonese business text. "
        "Use only the supplied evidence. Do not assign scores or priorities. "
        "Every item must cite one allowed evidence span and copy quoted_text exactly from that span. "
        "Return strict JSON only."
    )


def _build_prompt_payload(
    parsed: ParsedDocument,
    *,
    candidates: list[CandidateParagraph],
    config: GenAIExtractionConfig,
) -> dict[str, Any]:
    return {
        "document": {
            "document_id": _document_id(parsed),
            "title": parsed.title,
            "source_name": parsed.metadata.get("source_name"),
            "dataset": parsed.metadata.get("dataset"),
            "language": parsed.metadata.get("language") or parsed.metadata.get("lang"),
        },
        "allowed_evidence_spans": [item.prompt_payload() for item in candidates],
        "required_schema": {
            "metrics": [
                {
                    "name": "metric name",
                    "value": "value as written",
                    "unit": "optional",
                    "period": "optional",
                    "confidence": 0.0,
                    "evidence_span": {
                        "chunk_id": "must match allowed_evidence_spans[].chunk_id",
                        "quoted_text": "exact substring from the cited span",
                    },
                }
            ],
            "risk_factors": [
                {
                    "category": "regulatory/credit/liquidity/market/operational/geopolitical/other",
                    "description": "short description",
                    "severity": "low/medium/high",
                    "confidence": 0.0,
                    "evidence_span": {"chunk_id": "allowed chunk id", "quoted_text": "exact quote"},
                }
            ],
            "business_events": [
                {
                    "event_type": "expansion/financing/partnership/acquisition/regulatory/risk_alert/other",
                    "summary": "short summary",
                    "event_date": "optional",
                    "parties": ["optional"],
                    "confidence": 0.0,
                    "evidence_span": {"chunk_id": "allowed chunk id", "quoted_text": "exact quote"},
                }
            ],
            "management_statements": [
                {
                    "statement_type": "strategy/outlook/cross_border/liquidity/risk/other",
                    "summary": "short summary",
                    "confidence": 0.0,
                    "evidence_span": {"chunk_id": "allowed chunk id", "quoted_text": "exact quote"},
                }
            ],
            "opportunity_signal_candidates": [
                {
                    "signal_type": "cross_border/financing/expansion/growth/risk/other",
                    "summary": "candidate only, not a score",
                    "confidence": 0.0,
                    "evidence_span": {"chunk_id": "allowed chunk id", "quoted_text": "exact quote"},
                }
            ],
        },
        "rules": [
            "Do not infer facts not present in the candidate paragraphs.",
            "Do not convert management optimism directly into a score.",
            "If one sentence contains multiple distinct business events, return separate business_events.",
            "For example, if a sentence says a company expanded and signed a cooperation agreement, return one expansion event and one partnership event.",
            "Use canonical English metric names when obvious, for example revenue for \u8425\u4e1a\u6536\u5165 or \u71df\u696d\u6536\u5165.",
            "For Chinese or Cantonese text, quoted_text may be a short exact phrase when it is the minimal evidence.",
            "Use opportunity_signal_candidates only for possible downstream rule review.",
            "Return empty lists when evidence is insufficient.",
            f"Only include items with extraction confidence >= {config.min_confidence}.",
        ],
    }


def _iter_raw_facts(raw: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    source = raw.get("answer") if isinstance(raw.get("answer"), dict) else raw
    key_map = {
        "metrics": "metric",
        "risk_factors": "risk_factor",
        "risks": "risk_factor",
        "business_events": "business_event",
        "events": "business_event",
        "management_statements": "management_statement",
        "opportunity_signal_candidates": "opportunity_signal_candidate",
        "opportunity_signals": "opportunity_signal_candidate",
    }
    for key, fact_type in key_map.items():
        values = source.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict):
                out.append((fact_type, item))
    return out


def _normalize_fact(
    fact_type: str,
    item: dict[str, Any],
    *,
    allowed: dict[str, CandidateParagraph],
    config: GenAIExtractionConfig,
    seen_keys: set[tuple[str, str, str]],
) -> tuple[dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    confidence = _confidence(item)
    if confidence < config.min_confidence:
        reasons.append("low_extraction_confidence")

    span, span_reasons = _validate_evidence_span(item.get("evidence_span"), allowed=allowed)
    reasons.extend(span_reasons)

    normalized = _base_normalized_fact(fact_type, item, confidence=confidence, span=span)
    if _is_generic_fact(normalized):
        reasons.append("too_generic")

    if reasons or normalized is None or span is None:
        return None, reasons or ["invalid_fact"]

    normalized["evidence_span"] = span.as_dict()
    normalized["scoring_eligibility"] = {
        "eligible": fact_type in {"metric", "risk_factor", "business_event"},
        "reasons": [
            "valid_evidence_span",
            "allowed_candidate_section",
            "not_duplicate",
            "confidence_threshold_met",
        ],
    }
    if fact_type not in {"metric", "risk_factor", "business_event"}:
        normalized["scoring_eligibility"]["reasons"].append("context_only_not_scoring_input")
    return normalized, []


def _base_normalized_fact(
    fact_type: str,
    item: dict[str, Any],
    *,
    confidence: float,
    span: GenAIEvidenceSpan | None,
) -> dict[str, Any] | None:
    quote = span.quoted_text if span else normalize_text((item.get("evidence_span") or {}).get("quoted_text"))
    if fact_type == "metric":
        name = _normalize_metric_name(item.get("name"))
        value = normalize_text(item.get("value"))
        if not name or not value:
            return None
        return {
            "fact_type": fact_type,
            "name": name[:120],
            "value": value[:120],
            "unit": normalize_text(item.get("unit")) or None,
            "period": normalize_text(item.get("period")) or None,
            "context": quote[:300],
            "extraction_confidence": confidence,
        }
    if fact_type == "risk_factor":
        description = normalize_text(item.get("description") or item.get("summary") or quote)
        if not description:
            return None
        return {
            "fact_type": fact_type,
            "category": normalize_text(item.get("category")) or "other",
            "description": description[:300],
            "severity": _normalize_severity(item.get("severity")),
            "extraction_confidence": confidence,
        }
    if fact_type == "business_event":
        summary = normalize_text(item.get("summary") or quote)
        if not summary:
            return None
        parties = item.get("parties") if isinstance(item.get("parties"), list) else []
        return {
            "fact_type": fact_type,
            "event_type": normalize_text(item.get("event_type")) or "other",
            "summary": summary[:300],
            "event_date": normalize_text(item.get("event_date")) or None,
            "parties": [normalize_text(party) for party in parties if normalize_text(party)][:8],
            "extraction_confidence": confidence,
        }
    if fact_type == "management_statement":
        summary = normalize_text(item.get("summary") or quote)
        if not summary:
            return None
        return {
            "fact_type": fact_type,
            "statement_type": normalize_text(item.get("statement_type")) or "other",
            "summary": summary[:300],
            "extraction_confidence": confidence,
        }
    if fact_type == "opportunity_signal_candidate":
        summary = normalize_text(item.get("summary") or quote)
        if not summary:
            return None
        return {
            "fact_type": fact_type,
            "signal_type": normalize_text(item.get("signal_type")) or "other",
            "summary": summary[:300],
            "extraction_confidence": confidence,
        }
    return None


def _validate_evidence_span(
    raw_span: Any,
    *,
    allowed: dict[str, CandidateParagraph],
) -> tuple[GenAIEvidenceSpan | None, list[str]]:
    if not isinstance(raw_span, dict):
        return None, ["missing_evidence_span"]
    chunk_id = normalize_text(raw_span.get("chunk_id"))
    candidate = allowed.get(chunk_id)
    if candidate is None:
        return None, ["unknown_chunk_id"]
    quote = normalize_text(raw_span.get("quoted_text"))
    if len(quote) < _minimum_quote_length(quote):
        return None, ["missing_or_short_quote"]
    if not _contains_quote(candidate.text, quote):
        return None, ["quote_not_found_in_candidate"]
    return GenAIEvidenceSpan(
        document_id=candidate.evidence.document_id,
        section_id=candidate.evidence.section_id,
        paragraph_id=candidate.evidence.paragraph_id,
        chunk_id=candidate.evidence.chunk_id,
        page=candidate.evidence.page,
        quoted_text=quote,
        language=candidate.evidence.language,
    ), []


def _merge_eligible_facts(parsed: ParsedDocument, accepted: list[dict[str, Any]], *, config: GenAIExtractionConfig) -> None:
    for fact in accepted:
        if not fact.get("scoring_eligibility", {}).get("eligible"):
            continue
        confidence = float(fact.get("extraction_confidence") or 0)
        if fact["fact_type"] == "metric":
            parsed.metrics.append(
                ExtractedMetric(
                    name=fact["name"],
                    value=fact["value"],
                    unit=fact.get("unit"),
                    period=fact.get("period"),
                    context=fact.get("context"),
                    confidence=confidence,
                )
            )
        elif fact["fact_type"] == "risk_factor":
            parsed.risk_factors.append(
                RiskFactor(
                    category=fact["category"],
                    description=fact["description"],
                    severity=fact["severity"],
                    confidence=confidence,
                )
            )
        elif fact["fact_type"] == "business_event":
            parsed.business_events.append(
                BusinessEvent(
                    event_type=fact["event_type"],
                    summary=fact["summary"],
                    event_date=fact.get("event_date"),
                    parties=fact.get("parties", []),
                    confidence=confidence,
                )
            )

    if config.merge_management_discussion:
        statements = [fact for fact in accepted if fact["fact_type"] == "management_statement"]
        if statements:
            highlights = [fact["summary"] for fact in statements[:5]]
            source_sections = [
                str(fact["evidence_span"]["section_id"])
                for fact in statements
                if fact.get("evidence_span")
            ]
            summary = " ".join(highlights[:3])
            if parsed.management_discussion is None:
                parsed.management_discussion = ManagementDiscussion(
                    summary=summary[:600],
                    highlights=highlights,
                    source_sections=source_sections,
                )
            else:
                parsed.management_discussion.highlights.extend(highlights)
                parsed.management_discussion.source_sections.extend(source_sections)


def _score_text(value: str, *, heading: bool) -> tuple[int, list[str]]:
    lower = normalize_text(value).lower()
    if not lower:
        return 0, []
    score = 0
    reasons: list[str] = []
    if any(marker in lower for marker in _TITLE_MARKERS):
        score += 5 if heading else 2
        reasons.append("title_match" if heading else "title_marker_in_text")
    if any(marker in lower for marker in _KEYWORD_MARKERS):
        score += 3
        reasons.append("keyword_match")
    if any(marker in lower for marker in _SEMANTIC_INTENT_MARKERS):
        score += 2
        reasons.append("light_semantic_match")
    return score, reasons


def _paragraphs(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    parts = [part.strip() for part in re.split(r"\n{2,}", normalized) if part.strip()]
    if len(parts) == 1 and len(parts[0]) > 1400:
        sentences = re.split(r"(?<=[.!?])\s+", parts[0])
        chunks: list[str] = []
        buffer: list[str] = []
        current_len = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            buffer.append(sentence)
            current_len += len(sentence)
            if current_len >= 900:
                chunks.append(" ".join(buffer))
                buffer = []
                current_len = 0
        if buffer:
            chunks.append(" ".join(buffer))
        return chunks
    return parts


def _confidence(item: dict[str, Any]) -> float:
    try:
        value = float(item.get("confidence", 0))
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def _normalize_severity(value: Any) -> str:
    severity = normalize_text(value).lower()
    if severity in {"low", "medium", "high"}:
        return severity
    return "medium"


def _document_id(parsed: ParsedDocument) -> str | None:
    for key in ("document_id", "source_id", "source_record_key", "record_key"):
        value = parsed.metadata.get(key)
        if value is not None and normalize_text(value):
            return normalize_text(value)
    return None


def _contains_quote(text: str, quote: str) -> bool:
    normalized_text = normalize_text(text).lower()
    normalized_quote = normalize_text(quote).lower()
    return normalized_quote in normalized_text


def _is_generic_fact(fact: dict[str, Any] | None) -> bool:
    if fact is None:
        return False
    if fact.get("fact_type") == "metric":
        return False
    text = normalize_text(fact.get("summary") or fact.get("description") or fact.get("context")).lower()
    min_len = 4 if re.search(r"[\u4e00-\u9fff]", text) else 20
    if len(text) < min_len:
        return True
    return any(phrase in text for phrase in _GENERIC_PHRASES)


def _normalize_metric_name(value: Any) -> str:
    raw = normalize_text(value)
    lowered = raw.lower()
    for canonical, aliases in _METRIC_NAME_ALIASES:
        if any(alias.lower() in lowered for alias in aliases):
            return canonical
    return raw[:120]


def _minimum_quote_length(value: str) -> int:
    return 4 if re.search(r"[\u4e00-\u9fff]", value) else 8


def _existing_fact_keys(parsed: ParsedDocument) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for metric in parsed.metrics:
        keys.add(("metric", metric.name.lower(), metric.value.lower()))
    for risk in parsed.risk_factors:
        keys.add(("risk_factor", risk.category.lower(), normalize_text(risk.description).lower()[:80]))
    for event in parsed.business_events:
        keys.add(("business_event", event.event_type.lower(), normalize_text(event.summary).lower()[:80]))
    return keys


def _fact_key(fact: dict[str, Any]) -> tuple[str, str, str]:
    fact_type = fact["fact_type"]
    if fact_type == "metric":
        return (fact_type, fact["name"].lower(), fact["value"].lower())
    if fact_type == "risk_factor":
        return (fact_type, fact["category"].lower(), normalize_text(fact["description"]).lower()[:80])
    if fact_type == "business_event":
        return (fact_type, fact["event_type"].lower(), normalize_text(fact["summary"]).lower()[:80])
    if fact_type == "management_statement":
        return (fact_type, fact["statement_type"].lower(), normalize_text(fact["summary"]).lower()[:80])
    return (fact_type, fact.get("signal_type", "other").lower(), normalize_text(fact.get("summary")).lower()[:80])


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
