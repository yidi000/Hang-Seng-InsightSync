from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SourceKind = Literal["document", "html", "json", "text", "unknown"]


@dataclass(slots=True)
class ParseRequest:
    source_name: str | None = None
    dataset: str | None = None
    title: str | None = None
    summary: str | None = None
    language: str | None = None
    source_uri: str | None = None
    media_type: str | None = None
    file_path: str | None = None
    content: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> Path | None:
        if not self.file_path:
            return None
        try:
            return Path(self.file_path).expanduser().resolve()
        except OSError:
            return None


@dataclass(slots=True)
class ParsedSection:
    heading: str
    text: str
    level: int = 1
    section_type: str | None = None
    page_number: int | None = None


@dataclass(slots=True)
class ParsedTable:
    title: str | None
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    page_number: int | None = None

    def preview_lines(self, *, max_rows: int = 3) -> list[str]:
        if not self.rows:
            return []
        out: list[str] = []
        headers = [header.strip() for header in self.headers if header and header.strip()]
        for row in self.rows[: max(0, max_rows)]:
            cells = [str(cell).strip() for cell in row]
            if headers and len(headers) == len(cells):
                pairs = [f"{header}: {value}" for header, value in zip(headers, cells) if value]
                if pairs:
                    out.append("; ".join(pairs))
                    continue
            compact = " | ".join(cell for cell in cells if cell)
            if compact:
                out.append(compact)
        return out


@dataclass(slots=True)
class ExtractedMetric:
    name: str
    value: str
    unit: str | None = None
    period: str | None = None
    context: str | None = None
    confidence: float | None = None


@dataclass(slots=True)
class RiskFactor:
    category: str
    description: str
    severity: str = "medium"
    confidence: float | None = None


@dataclass(slots=True)
class BusinessEvent:
    event_type: str
    summary: str
    event_date: str | None = None
    parties: list[str] = field(default_factory=list)
    confidence: float | None = None


@dataclass(slots=True)
class ManagementDiscussion:
    summary: str
    highlights: list[str] = field(default_factory=list)
    source_sections: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ParsedDocument:
    parser_name: str
    backend_name: str | None = None
    parse_status: str = "success"
    source_kind: SourceKind = "unknown"
    media_type: str | None = None
    title: str | None = None
    summary: str | None = None
    text: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    metrics: list[ExtractedMetric] = field(default_factory=list)
    risk_factors: list[RiskFactor] = field(default_factory=list)
    business_events: list[BusinessEvent] = field(default_factory=list)
    management_discussion: ManagementDiscussion | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def parse_summary(self) -> dict[str, Any]:
        return {
            "parser_name": self.parser_name,
            "backend_name": self.backend_name,
            "parse_status": self.parse_status,
            "source_kind": self.source_kind,
            "media_type": self.media_type,
            "sections_count": len(self.sections),
            "tables_count": len(self.tables),
            "metrics_count": len(self.metrics),
            "risk_factors_count": len(self.risk_factors),
            "business_events_count": len(self.business_events),
            "has_management_discussion": self.management_discussion is not None,
            "warnings": list(self.warnings),
        }

    def to_rag_text(self) -> str:
        parts: list[str] = []
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.summary:
            parts.append(f"Summary: {self.summary}")
        if self.text:
            parts.append(f"Parsed text:\n{self.text}")
        if self.management_discussion:
            parts.append(f"Management discussion summary: {self.management_discussion.summary}")
            if self.management_discussion.highlights:
                parts.append(
                    "Management discussion highlights:\n"
                    + "\n".join(f"- {item}" for item in self.management_discussion.highlights)
                )
        if self.metrics:
            parts.append(
                "Extracted metrics:\n"
                + "\n".join(
                    f"- {metric.name}: {metric.value}"
                    + (f" {metric.unit}" if metric.unit else "")
                    + (f" ({metric.period})" if metric.period else "")
                    + (f" | {metric.context}" if metric.context else "")
                    for metric in self.metrics
                )
            )
        if self.risk_factors:
            parts.append(
                "Risk factors:\n"
                + "\n".join(
                    f"- [{risk.severity}] {risk.category}: {risk.description}" for risk in self.risk_factors
                )
            )
        if self.business_events:
            parts.append(
                "Business events:\n"
                + "\n".join(
                    f"- {event.event_type}: {event.summary}"
                    + (f" ({event.event_date})" if event.event_date else "")
                    for event in self.business_events
                )
            )
        if self.tables:
            table_blocks: list[str] = []
            for idx, table in enumerate(self.tables, start=1):
                title = table.title or f"Table {idx}"
                preview = table.preview_lines()
                if preview:
                    table_blocks.append(f"{title}:\n" + "\n".join(f"- {line}" for line in preview))
            if table_blocks:
                parts.append("Tables:\n" + "\n\n".join(table_blocks))
        if self.warnings:
            parts.append("Parsing warnings:\n" + "\n".join(f"- {warning}" for warning in self.warnings))
        return "\n\n".join(part for part in parts if part and part.strip()).strip()
