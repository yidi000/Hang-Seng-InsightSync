from __future__ import annotations

from ..base import BaseParser
from ..models import ParseRequest, ParsedDocument
from ..structured import extract_business_events, extract_management_discussion, extract_metrics, extract_risk_factors
from ..utils import normalize_text, split_text_sections


class TextParser(BaseParser):
    name = "text"

    def supports(self, request: ParseRequest) -> bool:
        if not isinstance(request.content, str):
            return False
        return True

    def parse(self, request: ParseRequest) -> ParsedDocument:
        text = normalize_text(request.content)
        sections = split_text_sections(text, default_heading="Text")
        metrics = extract_metrics(text=text)
        risks = extract_risk_factors(text=text)
        events = extract_business_events(text=text, title=request.title)
        management_discussion = extract_management_discussion(
            title=request.title,
            sections=sections,
            text=text,
        )
        return ParsedDocument(
            parser_name=self.name,
            backend_name="native",
            source_kind="text",
            media_type=request.media_type or "text/plain",
            title=request.title,
            summary=request.summary,
            text=text,
            sections=sections,
            metrics=metrics,
            risk_factors=risks,
            business_events=events,
            management_discussion=management_discussion,
            metadata={"source_name": request.source_name, "dataset": request.dataset, **request.metadata},
        )
