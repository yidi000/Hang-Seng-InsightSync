"""Add parsed document persistence tables.

Revision ID: 0005_parsed_document_tables
Revises: 0004_company_tables_sync
Create Date: 2026-04-22
"""
from __future__ import annotations

from alembic import op

revision = "0005_parsed_document_tables"
down_revision = "0004_company_tables_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS parsing_runs (
          run_id TEXT PRIMARY KEY,
          parse_version TEXT NOT NULL,
          started_at TIMESTAMPTZ NOT NULL,
          finished_at TIMESTAMPTZ,
          status TEXT NOT NULL,
          message TEXT,
          summary_json JSONB
        );

        CREATE TABLE IF NOT EXISTS parsed_documents (
          id BIGSERIAL PRIMARY KEY,
          source_table TEXT NOT NULL,
          source_id BIGINT NOT NULL,
          source_content_hash TEXT NOT NULL,
          source_record_key TEXT,
          source TEXT NOT NULL,
          dataset TEXT,
          company_id TEXT,
          entity TEXT,
          title TEXT,
          summary TEXT,
          media_type TEXT,
          lang TEXT,
          file_path TEXT,
          evidence_url TEXT,
          parser_name TEXT NOT NULL,
          backend_name TEXT,
          parse_version TEXT NOT NULL,
          parse_status TEXT NOT NULL,
          ocr_status TEXT,
          xbrl_status TEXT,
          content_text TEXT,
          search_text TEXT,
          warnings_json JSONB,
          metadata_json JSONB,
          management_discussion_summary TEXT,
          management_discussion_highlights_json JSONB,
          management_discussion_source_sections_json JSONB,
          section_count INTEGER NOT NULL DEFAULT 0,
          table_count INTEGER NOT NULL DEFAULT 0,
          metric_count INTEGER NOT NULL DEFAULT 0,
          risk_factor_count INTEGER NOT NULL DEFAULT 0,
          business_event_count INTEGER NOT NULL DEFAULT 0,
          parsed_at TIMESTAMPTZ NOT NULL,
          run_id TEXT NOT NULL,
          CONSTRAINT uq_parsed_document_source_version UNIQUE (
            source_table,
            source_id,
            source_content_hash,
            parse_version
          )
        );

        CREATE INDEX IF NOT EXISTS idx_parsed_documents_lookup
          ON parsed_documents (source_table, source_id, parsed_at DESC);

        CREATE INDEX IF NOT EXISTS idx_parsed_documents_company
          ON parsed_documents (company_id, source, dataset, parsed_at DESC);

        CREATE TABLE IF NOT EXISTS parsed_sections (
          id BIGSERIAL PRIMARY KEY,
          document_id BIGINT NOT NULL REFERENCES parsed_documents(id) ON DELETE CASCADE,
          section_index INTEGER NOT NULL,
          heading TEXT NOT NULL,
          text TEXT NOT NULL,
          level INTEGER NOT NULL DEFAULT 1,
          section_type TEXT,
          page_number INTEGER,
          CONSTRAINT uq_parsed_section_index UNIQUE (document_id, section_index)
        );

        CREATE TABLE IF NOT EXISTS parsed_tables (
          id BIGSERIAL PRIMARY KEY,
          document_id BIGINT NOT NULL REFERENCES parsed_documents(id) ON DELETE CASCADE,
          table_index INTEGER NOT NULL,
          title TEXT,
          headers_json JSONB,
          rows_json JSONB,
          page_number INTEGER,
          CONSTRAINT uq_parsed_table_index UNIQUE (document_id, table_index)
        );

        CREATE TABLE IF NOT EXISTS parsed_metrics (
          id BIGSERIAL PRIMARY KEY,
          document_id BIGINT NOT NULL REFERENCES parsed_documents(id) ON DELETE CASCADE,
          metric_index INTEGER NOT NULL,
          name TEXT NOT NULL,
          value TEXT NOT NULL,
          unit TEXT,
          period TEXT,
          context TEXT,
          confidence DOUBLE PRECISION,
          CONSTRAINT uq_parsed_metric_index UNIQUE (document_id, metric_index)
        );

        CREATE TABLE IF NOT EXISTS parsed_risk_factors (
          id BIGSERIAL PRIMARY KEY,
          document_id BIGINT NOT NULL REFERENCES parsed_documents(id) ON DELETE CASCADE,
          risk_index INTEGER NOT NULL,
          category TEXT NOT NULL,
          description TEXT NOT NULL,
          severity TEXT NOT NULL,
          confidence DOUBLE PRECISION,
          CONSTRAINT uq_parsed_risk_index UNIQUE (document_id, risk_index)
        );

        CREATE TABLE IF NOT EXISTS parsed_business_events (
          id BIGSERIAL PRIMARY KEY,
          document_id BIGINT NOT NULL REFERENCES parsed_documents(id) ON DELETE CASCADE,
          event_index INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          summary TEXT NOT NULL,
          event_date TEXT,
          parties_json JSONB,
          confidence DOUBLE PRECISION,
          CONSTRAINT uq_parsed_business_event_index UNIQUE (document_id, event_index)
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS parsed_business_events;
        DROP TABLE IF EXISTS parsed_risk_factors;
        DROP TABLE IF EXISTS parsed_metrics;
        DROP TABLE IF EXISTS parsed_tables;
        DROP TABLE IF EXISTS parsed_sections;
        DROP INDEX IF EXISTS idx_parsed_documents_company;
        DROP INDEX IF EXISTS idx_parsed_documents_lookup;
        DROP TABLE IF EXISTS parsed_documents;
        DROP TABLE IF EXISTS parsing_runs;
        """
    )
