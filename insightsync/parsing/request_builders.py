from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import DEFAULT_RAW_STORAGE_ROOT
from .models import ParseRequest
from .utils import guess_media_type, looks_like_html, normalize_text


def find_string_field(value: Any, *, candidates: tuple[str, ...]) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in candidates and isinstance(nested, str) and normalize_text(nested):
                return nested
            found = find_string_field(nested, candidates=candidates)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_string_field(item, candidates=candidates)
            if found:
                return found
    return None


def extract_file_path(payload: Any) -> str | None:
    return find_string_field(
        payload,
        candidates=("file_path", "local_path", "download_path", "artifact_path", "path"),
    )


def select_primary_content(
    payload: Any,
    *,
    summary: str | None = None,
    signal_text: str | None = None,
) -> tuple[Any, str | None]:
    if isinstance(payload, (dict, list)):
        html_candidate = find_string_field(
            payload,
            candidates=("html", "page_html", "detail_html", "article_html", "content_html"),
        )
        if html_candidate and looks_like_html(html_candidate):
            return html_candidate, "text/html"

        for key in ("article_text", "body", "content", "text", "description", "summary"):
            candidate = find_string_field(payload, candidates=(key,))
            if candidate and len(normalize_text(candidate)) >= 80:
                return candidate, "text/plain"
        return payload, "application/json"

    text_candidate = normalize_text(payload)
    if text_candidate:
        media_type = "text/html" if looks_like_html(text_candidate) else "text/plain"
        return payload, media_type

    fallback = normalize_text(summary) or normalize_text(signal_text)
    if fallback:
        return fallback, "text/plain"
    return payload, None


def resolve_file_path(
    file_path: str | None,
    *,
    raw_root: str | Path | None = None,
) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    raw = normalize_text(file_path)
    if not raw:
        return None, warnings
    try:
        candidate = Path(raw).expanduser()
    except OSError:
        return raw, [f"Unresolvable file path: {raw}"]

    if candidate.exists():
        return str(candidate.resolve()), warnings

    search_root = Path(raw_root or DEFAULT_RAW_STORAGE_ROOT).expanduser()
    if search_root.exists():
        matches = list(search_root.rglob(candidate.name))
        if matches:
            resolved = matches[0].resolve()
            warnings.append(f"Resolved missing artifact path {raw} to local file {resolved}.")
            return str(resolved), warnings

    warnings.append(f"Referenced file path is missing: {raw}")
    return str(candidate), warnings


def build_parse_request_from_row(
    row: dict[str, Any],
    *,
    title: Any | None = None,
    raw_root: str | Path | None = None,
) -> tuple[ParseRequest, list[str]]:
    row_title = title if title is not None else row.get("title") or row.get("dataset") or row.get("source_table")
    payload = row.get("payload_json")
    file_path = extract_file_path(payload)
    resolved_file_path, warnings = resolve_file_path(file_path, raw_root=raw_root)
    content, detected_media_type = select_primary_content(
        payload,
        summary=row.get("summary"),
        signal_text=row.get("signal_text"),
    )
    media_type = guess_media_type(
        explicit=detected_media_type,
        file_path=resolved_file_path,
        source_uri=row.get("evidence_url"),
    )
    request = ParseRequest(
        source_name=row.get("source"),
        dataset=row.get("dataset"),
        title=str(row_title) if row_title is not None else None,
        summary=row.get("summary"),
        language=row.get("lang"),
        source_uri=row.get("evidence_url"),
        media_type=media_type,
        file_path=resolved_file_path,
        content=content,
        metadata={
            "source_table": row.get("source_table"),
            "record_type": row.get("record_type"),
            "signal_type": row.get("signal_type"),
            "original_file_path": file_path,
            "resolved_file_path": resolved_file_path,
        },
    )
    return request, warnings
