from __future__ import annotations

import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ..models import ParseRequest, ParsedDocument, ParsedSection, ParsedTable
from ..structured import extract_business_events, extract_management_discussion, extract_metrics, extract_risk_factors
from ..utils import csv_text_to_table, guess_media_type, normalize_text, read_text_file, split_text_sections, table_to_text

_DOCUMENT_SUFFIXES = {
    ".pdf",
    ".txt",
    ".md",
    ".csv",
    ".xbrl",
    ".xml",
    ".xhtml",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xls",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
}
_PDF_NOISE_PATTERNS = (
    re.compile(r"^page\s+\d+$", re.I),
    re.compile(r"\b(?:https?://|www\.|[\w.-]+\.com(?:/\S*)?)\b", re.I),
    re.compile(r"all rights reserved", re.I),
    re.compile(r"copyright", re.I),
    re.compile(r"member firm", re.I),
    re.compile(r"private english company limited by guarantee", re.I),
)


class DocumentParser(BaseParser):
    name = "document"

    def supports(self, request: ParseRequest) -> bool:
        path = request.path
        if path is None:
            return False
        if path.suffix.lower() in _DOCUMENT_SUFFIXES:
            return True
        media_type = normalize_text(request.media_type).lower()
        return media_type in {
            "application/pdf",
            "text/csv",
            "text/plain",
            "application/xbrl+xml",
            "application/xml",
        }

    def parse(self, request: ParseRequest) -> ParsedDocument:
        warnings: list[str] = []
        path = request.path
        suffix = path.suffix.lower() if path is not None else ""
        media_type = guess_media_type(
            explicit=request.media_type,
            file_path=str(path) if path is not None else None,
            source_uri=request.source_uri,
        )

        if path is None or not path.exists():
            return ParsedDocument(
                parser_name=self.name,
                backend_name=None,
                parse_status="failed",
                source_kind="document",
                media_type=media_type,
                title=request.title,
                summary=request.summary,
                text="",
                warnings=["Referenced document file is missing or inaccessible."],
                metadata={"source_name": request.source_name, "dataset": request.dataset, **request.metadata},
            )

        backend_name = "native"
        extra_metadata: dict[str, Any] = {}
        if suffix == ".pdf":
            text, tables, pdf_warnings, backend_name, extra_metadata = self._parse_pdf(path)
            warnings.extend(pdf_warnings)
        elif suffix in {".txt", ".md"}:
            text = read_text_file(path)
            tables = []
            backend_name = "plain-text"
        elif suffix == ".csv":
            raw_text = read_text_file(path)
            table = csv_text_to_table(raw_text, title=path.name)
            tables = [table] if table is not None else []
            text = table_to_text(table, max_rows=60) if table is not None else raw_text
            backend_name = "csv"
        elif suffix in {".xbrl", ".xml", ".xhtml"}:
            text, tables, xbrl_warnings, backend_name, extra_metadata = self._parse_xbrl(path)
            warnings.extend(xbrl_warnings)
        else:
            text, tables, doc_warnings, backend_name = self._parse_with_docling(path)
            warnings.extend(doc_warnings)

        sections = split_text_sections(text, default_heading=path.stem or "Document")
        metrics = extract_metrics(text=text, tables=tables)
        risks = extract_risk_factors(text=text)
        events = extract_business_events(text=text, title=request.title or path.name)
        management_discussion = extract_management_discussion(
            title=request.title or path.name,
            sections=sections,
            text=text,
        )

        return ParsedDocument(
            parser_name=self.name,
            backend_name=backend_name,
            parse_status="success" if text or tables else "partial",
            source_kind="document",
            media_type=media_type,
            title=request.title or path.name,
            summary=request.summary,
            text=text,
            sections=sections,
            tables=tables,
            metrics=metrics,
            risk_factors=risks,
            business_events=events,
            management_discussion=management_discussion,
            warnings=warnings,
            metadata={
                "source_name": request.source_name,
                "dataset": request.dataset,
                "file_path": str(path),
                **extra_metadata,
                **request.metadata,
            },
        )

    def _parse_pdf(self, path: Path) -> tuple[str, list[ParsedTable], list[str], str, dict[str, Any]]:
        warnings: list[str] = []
        try:
            import fitz
        except Exception:
            return (
                "",
                [],
                [
                    "PyMuPDF is not installed, so PDF text extraction was skipped.",
                    "Install an OCR/document backend such as PyMuPDF, Docling, or OCRmyPDF for production parsing.",
                ],
                "unavailable",
                {"ocr_status": "unavailable"},
            )

        page_text_lines: list[list[str]] = []
        tables: list[ParsedTable] = []
        try:
            doc = fitz.open(path)
        except Exception as exc:
            return "", [], [f"Failed to open PDF: {exc}"], "pymupdf", {"ocr_status": "failed"}

        try:
            for page_index, page in enumerate(doc, start=1):
                page_lines = self._page_lines(page)
                if page_lines:
                    page_text_lines.append(page_lines)
                tables.extend(self._page_tables(page, page_number=page_index))
        finally:
            doc.close()

        text = self._clean_pdf_text(page_text_lines)
        metadata: dict[str, Any] = {"ocr_status": "not_needed"}
        backend_name = "pymupdf"
        if len(text.replace(" ", "")) < 80:
            ocr_text, ocr_warnings, ocr_backend = self._ocr_pdf(path)
            warnings.extend(ocr_warnings)
            if len(ocr_text.replace(" ", "")) > len(text.replace(" ", "")):
                text = ocr_text
                backend_name = ocr_backend
                metadata["ocr_status"] = "applied"
            else:
                warnings.append(
                    "PDF has little extractable text. This often indicates a scanned document; OCR preprocessing is recommended."
                )
                metadata["ocr_status"] = "recommended"
        return text, tables, warnings, backend_name, metadata

    def _page_lines(self, page: object) -> list[str]:
        try:
            text = page.get_text(sort=True)
        except TypeError:
            try:
                text = page.get_text("text", sort=True)
            except Exception:
                text = page.get_text("text")
        except Exception:
            text = ""
        normalized = normalize_text(text)
        if not normalized:
            return []
        return [normalize_text(line) for line in normalized.splitlines() if normalize_text(line)]

    def _clean_pdf_text(self, pages: list[list[str]]) -> str:
        if not pages:
            return ""

        page_count = len(pages)
        repeated_lines = Counter()
        for page in pages:
            page_keys = {self._line_key(line) for line in page if self._eligible_for_repetition_filter(line)}
            repeated_lines.update(key for key in page_keys if key)

        repeated_keys = {
            key
            for key, count in repeated_lines.items()
            if key and count >= 2 and count >= max(2, round(page_count * 0.4))
        }

        cleaned_pages: list[str] = []
        for page in pages:
            kept_lines: list[str] = []
            for line in page:
                if self._is_noise_line(line):
                    continue
                key = self._line_key(line)
                if key in repeated_keys and len(line) <= 180:
                    continue
                kept_lines.append(line)
            page_text = normalize_text("\n".join(kept_lines))
            if page_text:
                cleaned_pages.append(page_text)

        return normalize_text("\n\n".join(cleaned_pages))

    def _line_key(self, line: str) -> str:
        return normalize_text(line).lower()

    def _eligible_for_repetition_filter(self, line: str) -> bool:
        normalized = normalize_text(line)
        if not normalized or len(normalized) < 8 or len(normalized) > 180:
            return False
        if re.search(r"[.!?。！？]", normalized):
            return False
        return True

    def _is_noise_line(self, line: str) -> bool:
        normalized = normalize_text(line)
        lower = normalized.lower()
        if not normalized:
            return True
        if any(pattern.search(lower) for pattern in _PDF_NOISE_PATTERNS):
            return True
        if lower in {"contents", "aml", "(aml)"}:
            return True
        if re.fullmatch(r"(?:\d+\s*){2,}", normalized):
            return True
        if re.fullmatch(r"[\W_]+", normalized):
            return True
        return False

    def _page_tables(self, page: object, *, page_number: int) -> list[ParsedTable]:
        if not hasattr(page, "find_tables"):
            return []
        try:
            found = page.find_tables()
        except Exception:
            return []
        table_items = getattr(found, "tables", found) or []
        tables: list[ParsedTable] = []
        for index, table in enumerate(table_items, start=1):
            matrix = []
            if hasattr(table, "extract"):
                try:
                    matrix = table.extract() or []
                except Exception:
                    matrix = []
            if not matrix:
                continue
            rows_matrix = self._normalize_table_matrix(matrix)
            if rows_matrix is None:
                continue
            headers, rows = rows_matrix
            tables.append(
                ParsedTable(
                    title=f"PDF table {page_number}.{index}",
                    headers=headers,
                    rows=rows,
                    page_number=page_number,
                )
            )
        return tables

    def _normalize_table_matrix(self, matrix: list[list[Any]]) -> tuple[list[str], list[list[str]]] | None:
        normalized_rows = [[normalize_text(cell) for cell in row] for row in matrix]
        normalized_rows = [row for row in normalized_rows if any(cell for cell in row)]
        if len(normalized_rows) < 2:
            return None

        header_row_index = 0
        if self._looks_like_positional_row(normalized_rows[0]) and len(normalized_rows) >= 2:
            header_row_index = 1

        headers = normalized_rows[header_row_index]
        rows = normalized_rows[header_row_index + 1 :]
        if rows and rows[0] == headers:
            rows = rows[1:]
        if not rows or self._looks_like_layout_table(headers, rows):
            return None
        return headers, rows[:20]

    def _looks_like_positional_row(self, row: list[str]) -> bool:
        cells = [cell for cell in row if cell]
        if len(cells) < 2:
            return False
        return all(re.fullmatch(r"\d+", cell) for cell in cells)

    def _looks_like_layout_table(self, headers: list[str], rows: list[list[str]]) -> bool:
        sample_rows = [headers] + rows[:5]
        non_empty_cells = [cell for row in sample_rows for cell in row if cell]
        if len(non_empty_cells) < 4:
            return True
        joined = " ".join(non_empty_cells).lower()
        if any(len(cell) > 400 for cell in headers):
            return True
        if any(marker in joined for marker in ("all rights reserved", "member firm", "contact us")):
            return True
        if all(sum(1 for cell in row if cell) <= 1 for row in sample_rows):
            return True
        if not any(re.search(r"\d", cell) for row in rows[:5] for cell in row if cell):
            return True
        return False

    def _parse_with_docling(self, path: Path) -> tuple[str, list[ParsedTable], list[str], str]:
        try:
            from docling.document_converter import DocumentConverter
        except Exception:
            return (
                "",
                [],
                [
                    f"No parser backend available for {path.suffix} files.",
                    "Docling is recommended for Office, image, and mixed-layout documents.",
                ],
                "unavailable",
            )

        try:
            converter = DocumentConverter()
            result = converter.convert(str(path))
        except Exception as exc:
            return "", [], [f"Docling conversion failed: {exc}"], "docling"

        text = ""
        tables: list[ParsedTable] = []
        document = getattr(result, "document", None)
        if document is not None:
            try:
                text = normalize_text(document.export_to_markdown())
            except Exception:
                text = ""
        return text, tables, [], "docling"

    def _ocr_pdf(self, path: Path) -> tuple[str, list[str], str]:
        try:
            import fitz
            import ocrmypdf
        except Exception:
            return "", ["OCR backend not available; install OCRmyPDF and its runtime dependencies."], "ocrmypdf"

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = Path(tmp_dir) / f"{path.stem}_ocr.pdf"
                ocrmypdf.ocr(
                    str(path),
                    str(output_path),
                    force_ocr=True,
                    skip_text=True,
                    progress_bar=False,
                )
                doc = fitz.open(output_path)
                try:
                    parts = [normalize_text("\n".join(self._page_lines(page))) for page in doc]
                finally:
                    doc.close()
        except Exception as exc:
            return "", [f"OCR attempt failed: {exc}"], "ocrmypdf"
        return normalize_text("\n\n".join(part for part in parts if part)), [], "ocrmypdf+pymupdf"

    def _parse_xbrl(self, path: Path) -> tuple[str, list[ParsedTable], list[str], str, dict[str, Any]]:
        warnings: list[str] = []
        try:
            from arelle import Cntlr, ModelManager
        except Exception:
            text = read_text_file(path)
            warnings.append("Arelle is not installed; XBRL was parsed as plain XML text.")
            return text, [], warnings, "xml-fallback", {"xbrl_status": "unavailable"}

        facts: list[dict[str, str]] = []
        try:
            controller = Cntlr.Cntlr(logFileName=None)
            model_manager = ModelManager.initialize(controller)
            model_xbrl = model_manager.load(str(path))
            if model_xbrl is not None:
                for fact in getattr(model_xbrl, "facts", []):
                    qname = getattr(getattr(fact, "concept", None), "qname", None)
                    name = str(qname or getattr(fact, "qname", "") or "")
                    value = normalize_text(getattr(fact, "value", ""))
                    context = normalize_text(getattr(getattr(fact, "context", None), "id", ""))
                    if name and value:
                        facts.append({"name": name, "value": value, "context": context})
            try:
                model_manager.close()
            except Exception:
                pass
            try:
                controller.close()
            except Exception:
                pass
        except Exception as exc:
            warnings.append(f"Arelle XBRL parsing failed: {exc}")
            text = read_text_file(path)
            return text, [], warnings, "arelle", {"xbrl_status": "failed"}

        text_lines = [f"{item['name']}: {item['value']}" + (f" ({item['context']})" if item["context"] else "") for item in facts]
        table = ParsedTable(
            title=f"{path.name} facts",
            headers=["fact", "value", "context"],
            rows=[[item["name"], item["value"], item["context"]] for item in facts[:200]],
        )
        return "\n".join(text_lines), [table], warnings, "arelle", {"xbrl_status": "extracted"}
