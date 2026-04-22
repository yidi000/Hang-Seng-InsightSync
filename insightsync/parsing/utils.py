from __future__ import annotations

import csv
import html
import re
from pathlib import Path
from typing import Any

from .models import ParsedSection, ParsedTable

_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_DATE_RE = re.compile(
    r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Z][a-z]{2,8}\s+20\d{2}|[A-Z][a-z]{2,8}\s+\d{1,2},\s+20\d{2})\b"
)
_HTML_TAG_RE = re.compile(r"<(?:!doctype|html|body|head|title|meta|script|style|article|main|div|span|table)\b", re.I)

_HEADING_HINTS = {
    "management discussion",
    "management's discussion",
    "md&a",
    "chairman",
    "chief executive",
    "overview",
    "business review",
    "financial highlights",
    "risk factors",
    "outlook",
    "strategy",
    "discussion",
    "analysis",
    "管理层讨论",
    "管理层討論",
    "业务回顾",
    "業務回顧",
    "财务摘要",
    "財務摘要",
    "风险因素",
    "風險因素",
    "前景",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = str(value)
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def normalize_heading(value: str) -> str:
    return normalize_text(value).replace("_", " ").replace("-", " ").strip("# ").strip(":：")


def looks_like_html(text: str) -> bool:
    snippet = (text or "").lstrip()[:500]
    return bool(_HTML_TAG_RE.search(snippet))


def guess_media_type(*, explicit: str | None = None, file_path: str | None = None, source_uri: str | None = None) -> str | None:
    raw = normalize_text(explicit).lower()
    if raw:
        return raw
    candidate = normalize_text(file_path or source_uri).lower()
    if candidate.endswith(".pdf"):
        return "application/pdf"
    if candidate.endswith(".xbrl"):
        return "application/xbrl+xml"
    if candidate.endswith(".xml") or candidate.endswith(".xhtml"):
        return "application/xml"
    if candidate.endswith(".json"):
        return "application/json"
    if candidate.endswith(".html") or candidate.endswith(".htm"):
        return "text/html"
    if candidate.endswith(".csv"):
        return "text/csv"
    if candidate.endswith(".txt") or candidate.endswith(".md"):
        return "text/plain"
    return None


def read_text_file(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "big5", "latin-1"):
        try:
            return normalize_text(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    return normalize_text(raw.decode("utf-8", errors="ignore"))


def flatten_json_lines(value: Any, *, prefix: str = "") -> list[str]:
    lines: list[str] = []
    label = normalize_heading(prefix)
    if isinstance(value, dict):
        for key, nested in value.items():
            child = f"{label}.{key}" if label else str(key)
            lines.extend(flatten_json_lines(nested, prefix=child))
        return lines
    if isinstance(value, list):
        for idx, nested in enumerate(value, start=1):
            child = f"{label}[{idx}]" if label else f"[{idx}]"
            lines.extend(flatten_json_lines(nested, prefix=child))
        return lines
    text = normalize_text(value)
    if text:
        lines.append(f"{label}: {text}" if label else text)
    return lines


def _is_heading_candidate(line: str) -> bool:
    clean = normalize_heading(line)
    if not clean or len(clean) > 120:
        return False
    lower = clean.lower()
    if lower in _HEADING_HINTS:
        return True
    if any(hint in lower for hint in _HEADING_HINTS):
        return True
    if clean.startswith(("#", "##", "###")):
        return True
    if re.match(r"^\d+(\.\d+){0,3}[\).\s-]+\S", clean):
        return True
    if re.match(r"^[A-Z][A-Z0-9 /&,\-]{2,80}$", clean):
        return True
    if re.match(r"^[\u4e00-\u9fffA-Za-z0-9（）()、/\- ]{2,40}$", clean) and not re.search(r"[。！？.!?]$", clean):
        return len(clean.split()) <= 10 or len(clean) <= 24
    return False


def split_text_sections(text: str, *, default_heading: str = "Body") -> list[ParsedSection]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if not paragraphs:
        return []

    sections: list[ParsedSection] = []
    current_heading = default_heading
    buffer: list[str] = []

    def _flush() -> None:
        if buffer:
            sections.append(ParsedSection(heading=current_heading, text="\n\n".join(buffer).strip()))

    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        if len(lines) == 1 and _is_heading_candidate(lines[0]):
            _flush()
            buffer = []
            current_heading = normalize_heading(lines[0])
            continue
        if lines and _is_heading_candidate(lines[0]) and len(lines) > 1:
            _flush()
            current_heading = normalize_heading(lines[0])
            buffer = ["\n".join(lines[1:]).strip()]
            continue
        buffer.append(paragraph)
    if buffer:
        sections.append(ParsedSection(heading=current_heading, text="\n\n".join(buffer).strip()))
    return [section for section in sections if section.text]


def sections_to_text(sections: list[ParsedSection]) -> str:
    return "\n\n".join(
        f"{section.heading}\n{section.text}".strip()
        for section in sections
        if section.heading or section.text
    ).strip()


def extract_date_candidates(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _DATE_RE.finditer(text or ""):
        value = match.group(0)
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def csv_text_to_table(text: str, *, title: str | None = None) -> ParsedTable | None:
    normalized = normalize_text(text)
    if not normalized:
        return None
    rows = [[normalize_text(cell) for cell in row] for row in csv.reader(normalized.splitlines())]
    if not rows:
        return None
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return None

    header_row_index = 0
    if len(rows) >= 2 and _looks_like_positional_index_row(rows[0]) and not _looks_like_positional_index_row(rows[1]):
        header_row_index = 1

    headers = rows[header_row_index]
    body = rows[header_row_index + 1 :]
    return ParsedTable(title=title, headers=headers, rows=body)


def _looks_like_positional_index_row(row: list[str]) -> bool:
    cells = [normalize_text(cell) for cell in row if normalize_text(cell)]
    if len(cells) < 2:
        return False
    return all(re.fullmatch(r"\d+", cell) for cell in cells)
