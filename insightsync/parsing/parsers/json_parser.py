from __future__ import annotations

from typing import Any

from ..base import BaseParser
from ..models import ParseRequest, ParsedDocument, ParsedSection, ParsedTable
from ..structured import extract_business_events, extract_management_discussion, extract_metrics, extract_risk_factors
from ..utils import flatten_json_lines, normalize_heading, normalize_text, sections_to_text

_NARRATIVE_KEYS = {
    "summary",
    "description",
    "article_text",
    "body",
    "content",
    "text",
    "details",
    "management_discussion",
    "management_review",
    "risk_factors",
    "outlook",
}


class JSONParser(BaseParser):
    name = "json"

    def supports(self, request: ParseRequest) -> bool:
        if isinstance(request.content, (dict, list)):
            return True
        media_type = normalize_text(request.media_type).lower()
        if media_type.endswith("/json") or media_type == "application/json":
            return True
        path = request.path
        return path is not None and path.suffix.lower() == ".json"

    def parse(self, request: ParseRequest) -> ParsedDocument:
        payload = request.content
        warnings: list[str] = []
        if payload is None and request.path is not None:
            try:
                import json

                payload = json.loads(request.path.read_text(encoding="utf-8"))
            except Exception as exc:
                payload = {}
                warnings.append(f"Failed to load JSON file: {exc}")
        payload = payload if isinstance(payload, (dict, list)) else {"value": payload}

        sections = self._sections_from_payload(payload)
        text = sections_to_text(sections)
        tables = self._tables_from_payload(payload)
        metrics = extract_metrics(text=text, tables=tables)
        risks = extract_risk_factors(text=text)
        events = extract_business_events(text=text, title=request.title)
        management_discussion = extract_management_discussion(title=request.title, sections=sections, text=text)

        return ParsedDocument(
            parser_name=self.name,
            backend_name="native",
            source_kind="json",
            media_type=request.media_type or "application/json",
            title=request.title,
            summary=request.summary,
            text=text,
            sections=sections,
            tables=tables,
            metrics=metrics,
            risk_factors=risks,
            business_events=events,
            management_discussion=management_discussion,
            warnings=warnings,
            metadata={"source_name": request.source_name, "dataset": request.dataset, **request.metadata},
        )

    def _sections_from_payload(self, payload: Any) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        if isinstance(payload, dict):
            for key, value in payload.items():
                label = normalize_heading(str(key))
                if isinstance(value, str):
                    text = normalize_text(value)
                    if not text:
                        continue
                    section_type = "narrative" if key.lower() in _NARRATIVE_KEYS or len(text) > 80 else "field"
                    sections.append(ParsedSection(heading=label or "Field", text=text, section_type=section_type))
                    continue
                if isinstance(value, dict):
                    nested_lines = flatten_json_lines(value)
                    if nested_lines:
                        sections.append(
                            ParsedSection(
                                heading=label or "Object",
                                text="\n".join(nested_lines),
                                section_type="object",
                            )
                        )
                    continue
                if isinstance(value, list):
                    if value and all(isinstance(item, dict) for item in value):
                        preview_lines = []
                        for item in value[:10]:
                            preview_lines.extend(flatten_json_lines(item))
                        if preview_lines:
                            sections.append(
                                ParsedSection(
                                    heading=label or "List",
                                    text="\n".join(preview_lines),
                                    section_type="list",
                                )
                            )
                    else:
                        text = "\n".join(f"- {normalize_text(item)}" for item in value if normalize_text(item))
                        if text:
                            sections.append(ParsedSection(heading=label or "List", text=text, section_type="list"))
                    continue
                scalar = normalize_text(value)
                if scalar:
                    sections.append(ParsedSection(heading=label or "Field", text=scalar, section_type="field"))
        elif isinstance(payload, list):
            lines = flatten_json_lines(payload)
            if lines:
                sections.append(ParsedSection(heading="Items", text="\n".join(lines), section_type="list"))
        else:
            text = normalize_text(payload)
            if text:
                sections.append(ParsedSection(heading="Value", text=text, section_type="field"))
        return sections

    def _tables_from_payload(self, payload: Any) -> list[ParsedTable]:
        tables: list[ParsedTable] = []
        if not isinstance(payload, dict):
            return tables
        for key, value in payload.items():
            if not isinstance(value, list) or not value or not all(isinstance(item, dict) for item in value):
                continue
            headers = []
            for item in value:
                for header in item.keys():
                    if header not in headers:
                        headers.append(str(header))
            rows = [[normalize_text(item.get(header)) for header in headers] for item in value[:20]]
            tables.append(ParsedTable(title=normalize_heading(str(key)) or None, headers=headers, rows=rows))
        return tables
