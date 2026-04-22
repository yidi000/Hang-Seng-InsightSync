from __future__ import annotations

from .base import BaseParser
from .models import ParseRequest, ParsedDocument
from .parsers.document_parser import DocumentParser
from .parsers.html_parser import HTMLParser
from .parsers.json_parser import JSONParser
from .parsers.text_parser import TextParser


class ParserRegistry:
    def __init__(self, parsers: list[BaseParser] | None = None) -> None:
        self.parsers = parsers or []

    def register(self, parser: BaseParser) -> None:
        self.parsers.append(parser)

    def parse(self, request: ParseRequest) -> ParsedDocument:
        for parser in self.parsers:
            if parser.supports(request):
                return parser.parse(request)
        return ParsedDocument(
            parser_name="fallback",
            source_kind="unknown",
            media_type=request.media_type,
            title=request.title,
            summary=request.summary,
            text="",
            warnings=["No parser matched the supplied source payload."],
            metadata={"source_name": request.source_name, "dataset": request.dataset},
        )


_DEFAULT_REGISTRY = ParserRegistry(
    [
        DocumentParser(),
        HTMLParser(),
        JSONParser(),
        TextParser(),
    ]
)


def get_default_registry() -> ParserRegistry:
    return _DEFAULT_REGISTRY


def parse_content(request: ParseRequest) -> ParsedDocument:
    return get_default_registry().parse(request)
