from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from ..base import BaseParser
from ..models import ParseRequest, ParsedDocument, ParsedSection, ParsedTable
from ..structured import extract_business_events, extract_management_discussion, extract_metrics, extract_risk_factors
from ..utils import looks_like_html, normalize_heading, normalize_text, read_text_file, sections_to_text


class HTMLParser(BaseParser):
    name = "html"

    def supports(self, request: ParseRequest) -> bool:
        media_type = normalize_text(request.media_type).lower()
        if "html" in media_type:
            return True
        if isinstance(request.content, str) and looks_like_html(request.content):
            return True
        path = request.path
        return path is not None and path.suffix.lower() in {".html", ".htm"}

    def parse(self, request: ParseRequest) -> ParsedDocument:
        warnings: list[str] = []
        html_text = ""
        if isinstance(request.content, str) and request.content.strip():
            html_text = request.content
        elif request.path is not None and request.path.exists():
            html_text = read_text_file(request.path)

        trafilatura_text = self._extract_with_trafilatura(html_text)
        backend_name = "trafilatura" if trafilatura_text else "beautifulsoup"
        if not trafilatura_text and html_text:
            warnings.append("Trafilatura not available or extraction returned empty text; used BeautifulSoup fallback.")

        soup = BeautifulSoup(html_text, "lxml")
        for tag in soup.select("script, style, nav, footer, noscript, form, aside"):
            tag.decompose()

        title = request.title or normalize_text(
            (soup.title.string if soup.title and soup.title.string else "")
            or (soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else "")
        )
        sections = self._sections_from_soup(soup)
        text = trafilatura_text or sections_to_text(sections)
        tables = self._tables_from_soup(soup)
        metrics = extract_metrics(text=text, tables=tables)
        risks = extract_risk_factors(text=text)
        events = extract_business_events(text=text, title=title)
        management_discussion = extract_management_discussion(title=title, sections=sections, text=text)

        return ParsedDocument(
            parser_name=self.name,
            backend_name=backend_name,
            source_kind="html",
            media_type=request.media_type or "text/html",
            title=title or None,
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

    def _extract_with_trafilatura(self, html_text: str) -> str:
        if not html_text.strip():
            return ""
        try:
            import trafilatura
        except Exception:
            return ""
        try:
            extracted = trafilatura.extract(
                html_text,
                output_format="txt",
                include_tables=True,
                include_links=False,
                favor_precision=True,
            )
        except Exception:
            return ""
        return normalize_text(extracted)

    def _sections_from_soup(self, soup: BeautifulSoup) -> list[ParsedSection]:
        content_root = soup.select_one("article") or soup.select_one("main") or soup.body or soup
        sections: list[ParsedSection] = []
        current_heading = "Body"
        buffer: list[str] = []

        def _flush() -> None:
            if buffer:
                sections.append(ParsedSection(heading=current_heading, text="\n\n".join(buffer).strip()))

        for node in content_root.descendants:
            name = getattr(node, "name", None)
            if name in {"h1", "h2", "h3", "h4"}:
                _flush()
                buffer = []
                current_heading = normalize_heading(node.get_text(" ", strip=True)) or current_heading
                continue
            if name in {"p", "li"}:
                text = normalize_text(node.get_text(" ", strip=True))
                if text:
                    buffer.append(text)
        if buffer:
            sections.append(ParsedSection(heading=current_heading, text="\n\n".join(buffer).strip()))
        if not sections:
            fallback_text = normalize_text(content_root.get_text("\n", strip=True))
            if fallback_text:
                sections.append(ParsedSection(heading="Body", text=fallback_text))
        return sections

    def _tables_from_soup(self, soup: BeautifulSoup) -> list[ParsedTable]:
        tables: list[ParsedTable] = []
        for index, node in enumerate(soup.select("table"), start=1):
            rows = []
            headers = []
            header_nodes = node.select("tr th")
            if header_nodes:
                headers = [normalize_text(cell.get_text(" ", strip=True)) for cell in header_nodes]
            for row_node in node.select("tr"):
                cells = row_node.find_all(["td", "th"])
                if not cells:
                    continue
                row = [normalize_text(cell.get_text(" ", strip=True)) for cell in cells]
                if row:
                    rows.append(row)
            if headers and rows and rows[0] == headers:
                rows = rows[1:]
            title = None
            caption = node.find("caption")
            if caption is not None:
                title = normalize_text(caption.get_text(" ", strip=True))
            tables.append(ParsedTable(title=title or f"HTML table {index}", headers=headers, rows=rows[:20]))
        return tables
