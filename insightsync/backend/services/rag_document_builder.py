from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from insightsync.backend.db.tables import rag_chunks, rag_documents
from insightsync.backend.services.chunker import chunk_text
from insightsync.backend.utils import stable_hash
from insightsync.parsing import parse_content
from insightsync.parsing.request_builders import build_parse_request_from_row


def _payload_to_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, dict):
        parts = []
        for key, value in payload.items():
            if value is not None:
                parts.append(f"{key}: {value}")
        return "\n".join(parts)
    return str(payload)


class RagDocumentBuilder:
    """Build RAG documents and chunks from synchronized backend tables."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_documents(self) -> dict[str, int]:
        """Build documents from facts, selected signals, and timeline events.

        Semantics: ``rag_documents`` is a current-version store keyed by
        ``(source_table, source_id)``. When the source row's ``content_hash``
        changes, prior rag_document rows for the same source are deleted
        (cascading to chunks and embeddings) so retrieval only sees the
        latest version.
        """

        rows = self._source_rows()
        parsed_lookup = self._latest_parsed_documents()
        inserted = 0
        superseded = 0
        for row in rows:
            doc = self._row_to_document(row, parsed_doc=parsed_lookup.get((row["source_table"], row["source_id"])))
            delete_result = self.db.execute(
                text(
                    """
                    DELETE FROM rag_documents
                    WHERE source_table = :source_table
                      AND source_id = :source_id
                      AND content_hash <> :content_hash
                    """
                ),
                {
                    "source_table": doc["source_table"],
                    "source_id": doc["source_id"],
                    "content_hash": doc["content_hash"],
                },
            )
            superseded += max(0, int(delete_result.rowcount or 0))
            stmt = insert(rag_documents).values(doc).on_conflict_do_nothing(
                index_elements=["source_table", "source_id", "content_hash"]
            )
            result = self.db.execute(stmt)
            inserted += max(0, int(result.rowcount or 0))
        return {
            "scanned": len(rows),
            "inserted": inserted,
            "superseded": superseded,
            "skipped": max(0, len(rows) - inserted),
        }

    def build_chunks(self) -> dict[str, int]:
        """Build chunks for documents that do not have chunks yet."""

        documents = self.db.execute(
            text(
                """
                SELECT d.*
                FROM rag_documents d
                LEFT JOIN rag_chunks c ON c.document_id = d.id
                WHERE c.id IS NULL
                ORDER BY d.id
                """
            )
        ).mappings()
        scanned = 0
        inserted = 0
        for doc in documents:
            scanned += 1
            for chunk in chunk_text(doc["content"]):
                metadata = dict(doc["metadata_json"] or {})
                metadata.update({"document_id": doc["id"], "chunk_index": chunk["chunk_index"]})
                stmt = insert(rag_chunks).values(
                    document_id=doc["id"],
                    chunk_index=chunk["chunk_index"],
                    chunk_text=chunk["chunk_text"],
                    chunk_hash=chunk["chunk_hash"],
                    token_count=chunk["token_count"],
                    metadata_json=metadata,
                ).on_conflict_do_nothing(index_elements=["document_id", "chunk_index", "chunk_hash"])
                result = self.db.execute(stmt)
                inserted += max(0, int(result.rowcount or 0))
        return {"documents_scanned": scanned, "chunks_inserted": inserted}

    def _source_rows(self) -> list[dict[str, Any]]:
        record_rows = self.db.execute(
            text(
                """
                SELECT 'intelligence_records' AS source_table, id AS source_id, source, dataset, record_key,
                       NULL::text AS signal_key, entity, company_id, event_time, record_type,
                       NULL::text AS signal_type, region, industry, lang, evidence_url, title,
                       summary, payload_json, NULL::text AS signal_text
                FROM intelligence_records
                """
            )
        ).mappings()
        signal_rows = self.db.execute(
            text(
                """
                SELECT 'trigger_signals' AS source_table, id AS source_id, source, dataset, NULL::text AS record_key,
                       signal_key, entity, company_id, event_time, NULL::text AS record_type,
                       signal_type, NULL::text AS region, NULL::text AS industry,
                       COALESCE(extra_json->>'lang', NULL) AS lang, NULL::text AS evidence_url,
                       indicator AS title, NULL::text AS summary, extra_json AS payload_json, signal_text
                FROM trigger_signals
                WHERE signal_text IS NOT NULL AND signal_text <> ''
                """
            )
        ).mappings()
        timeline_rows = self.db.execute(
            text(
                """
                SELECT 'client_one_view_timeline' AS source_table, id AS source_id, source,
                       COALESCE(payload_json->>'dataset', event_type) AS dataset,
                       payload_json->>'record_key' AS record_key, NULL::text AS signal_key,
                       entity, company_id, event_time, event_type AS record_type,
                       NULL::text AS signal_type, NULL::text AS region, NULL::text AS industry,
                       NULL::text AS lang, evidence_url, headline AS title, detail AS summary,
                       payload_json, NULL::text AS signal_text
                FROM client_one_view_timeline
                """
            )
        ).mappings()
        return [dict(row) for row in record_rows] + [dict(row) for row in signal_rows] + [dict(row) for row in timeline_rows]

    def _latest_parsed_documents(self) -> dict[tuple[str, int], dict[str, Any]]:
        try:
            rows = self.db.execute(
                text(
                    """
                    SELECT DISTINCT ON (source_table, source_id)
                           source_table, source_id, parser_name, backend_name, parse_status,
                           search_text, warnings_json, metadata_json, section_count, table_count,
                           metric_count, risk_factor_count, business_event_count,
                           management_discussion_summary, parsed_at, parse_version
                    FROM parsed_documents
                    ORDER BY source_table, source_id, parsed_at DESC, id DESC
                    """
                )
            ).mappings()
        except Exception:
            return {}
        return {
            (str(row["source_table"]), int(row["source_id"])): dict(row)
            for row in rows
        }

    def _row_to_document(self, row: dict[str, Any], *, parsed_doc: dict[str, Any] | None = None) -> dict[str, Any]:
        title = row.get("title") or row.get("dataset") or row.get("source_table")
        event_time = row.get("event_time")
        event_time_str = event_time.isoformat() if isinstance(event_time, (datetime, date)) else event_time
        sections = [
            f"Title: {title}",
            f"Source: {row.get('source')}",
            f"Dataset: {row.get('dataset')}",
            f"Entity: {row.get('entity')}",
            f"Event time: {event_time_str}",
        ]
        if row.get("summary"):
            sections.append(f"Summary: {row['summary']}")
        if row.get("signal_text"):
            sections.append(f"Signal: {row['signal_text']}")
        parse_summary: dict[str, Any]
        parsed_text = ""
        if parsed_doc and parsed_doc.get("search_text"):
            parsed_text = str(parsed_doc["search_text"])
            parse_summary = {
                "parser_name": parsed_doc.get("parser_name"),
                "backend_name": parsed_doc.get("backend_name"),
                "parse_status": parsed_doc.get("parse_status"),
                "sections_count": parsed_doc.get("section_count"),
                "tables_count": parsed_doc.get("table_count"),
                "metrics_count": parsed_doc.get("metric_count"),
                "risk_factors_count": parsed_doc.get("risk_factor_count"),
                "business_events_count": parsed_doc.get("business_event_count"),
                "management_discussion_summary": parsed_doc.get("management_discussion_summary"),
                "warnings": parsed_doc.get("warnings_json") or [],
                "parse_version": parsed_doc.get("parse_version"),
                "parsed_at": parsed_doc.get("parsed_at"),
            }
        else:
            parse_request, request_warnings = build_parse_request_from_row(row, title=title)
            parsed = parse_content(parse_request)
            parsed_text = parsed.to_rag_text()
            parse_summary = parsed.parse_summary()
            parse_summary["warnings"] = request_warnings + list(parse_summary.get("warnings") or [])
        if parsed_text:
            sections.append(parsed_text)
        else:
            payload_text = _payload_to_text(row.get("payload_json"))
            if payload_text:
                sections.append(f"Payload:\n{payload_text}")
        content = "\n".join(section for section in sections if section)
        metadata = {
            key: row.get(key)
            for key in (
                "source_table",
                "source_id",
                "source",
                "dataset",
                "record_key",
                "signal_key",
                "entity",
                "company_id",
                "event_time",
                "record_type",
                "signal_type",
                "region",
                "industry",
                "lang",
                "evidence_url",
            )
        }
        # Row-level values keep native datetime (columns are TIMESTAMPTZ),
        # but metadata_json must be JSON-native.
        metadata_json = {
            k: (v.isoformat() if isinstance(v, (datetime, date)) else v)
            for k, v in metadata.items()
        }
        metadata_json["parse"] = parse_summary
        metadata_json["parse_version"] = parse_summary.get("parse_version") or "multisource-v2"
        return {
            **metadata,
            "title": str(title),
            "content": content,
            "metadata_json": metadata_json,
            "content_hash": stable_hash({"content": content, "metadata": metadata_json}),
        }
