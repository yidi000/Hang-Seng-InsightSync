"""Add curated prospect and Copilot tables.

Revision ID: 0006_curated_prospect_copilot
Revises: 0005_parsed_document_tables
Create Date: 2026-05-05
"""
from __future__ import annotations

from alembic import op

revision = "0006_curated_prospect_copilot"
down_revision = "0005_parsed_document_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prospects (
          id BIGSERIAL PRIMARY KEY,
          prospect_id TEXT NOT NULL UNIQUE,
          company_id TEXT,
          display_name TEXT NOT NULL,
          canonical_name TEXT,
          region TEXT,
          industry TEXT,
          size_band TEXT NOT NULL DEFAULT 'unknown',
          segments_json JSONB,
          source_profile_json JSONB,
          last_activity_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          run_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_prospects_region_industry
          ON prospects (region, industry, size_band);

        CREATE TABLE IF NOT EXISTS prospect_evidence_items (
          id BIGSERIAL PRIMARY KEY,
          evidence_id TEXT NOT NULL UNIQUE,
          prospect_id TEXT,
          company_id TEXT,
          source_table TEXT NOT NULL,
          source_id BIGINT NOT NULL,
          evidence_type TEXT NOT NULL,
          event_time TIMESTAMPTZ,
          title TEXT NOT NULL,
          summary TEXT,
          url TEXT,
          source TEXT NOT NULL,
          dataset TEXT,
          metadata_json JSONB,
          content_hash TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          run_id TEXT NOT NULL,
          CONSTRAINT uq_prospect_evidence_source_hash UNIQUE (source_table, source_id, content_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_prospect_evidence_lookup
          ON prospect_evidence_items (prospect_id, evidence_type, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_prospect_evidence_source
          ON prospect_evidence_items (source, dataset, event_time DESC);

        CREATE TABLE IF NOT EXISTS prospect_signals (
          id BIGSERIAL PRIMARY KEY,
          signal_id TEXT NOT NULL UNIQUE,
          prospect_id TEXT,
          company_id TEXT,
          signal_type TEXT NOT NULL,
          signal_subtype TEXT NOT NULL,
          signal_level TEXT,
          signal_score DOUBLE PRECISION,
          event_time TIMESTAMPTZ,
          signal_text TEXT NOT NULL,
          evidence_ids_json JSONB,
          metadata_json JSONB,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          run_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_prospect_signals_lookup
          ON prospect_signals (prospect_id, signal_subtype, event_time DESC);

        CREATE TABLE IF NOT EXISTS prospect_scores (
          id BIGSERIAL PRIMARY KEY,
          prospect_id TEXT NOT NULL UNIQUE,
          company_id TEXT,
          score DOUBLE PRECISION NOT NULL,
          tier TEXT NOT NULL,
          reasons_json JSONB,
          recommended_products_json JSONB,
          recommended_entry_angle TEXT,
          score_inputs_json JSONB,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          run_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_prospect_scores_rank
          ON prospect_scores (score DESC, tier);

        CREATE TABLE IF NOT EXISTS market_opportunity_snapshots (
          id BIGSERIAL PRIMARY KEY,
          snapshot_date TIMESTAMPTZ NOT NULL,
          region TEXT,
          industry TEXT,
          size_band TEXT NOT NULL DEFAULT 'unknown',
          signal_type TEXT,
          lead_count INTEGER NOT NULL DEFAULT 0,
          signal_count INTEGER NOT NULL DEFAULT 0,
          avg_score DOUBLE PRECISION,
          top_prospect_ids_json JSONB,
          trend_summary TEXT,
          run_id TEXT NOT NULL,
          CONSTRAINT uq_market_snapshot_bucket UNIQUE (
            snapshot_date, region, industry, size_band, signal_type
          )
        );

        CREATE TABLE IF NOT EXISTS data_quality_reports (
          id BIGSERIAL PRIMARY KEY,
          run_id TEXT NOT NULL UNIQUE,
          report_json JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS copilot_conversations (
          id BIGSERIAL PRIMARY KEY,
          conversation_id TEXT NOT NULL UNIQUE,
          context TEXT NOT NULL,
          prospect_id TEXT,
          title TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS copilot_messages (
          id BIGSERIAL PRIMARY KEY,
          message_id TEXT NOT NULL UNIQUE,
          conversation_id TEXT NOT NULL,
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          status TEXT NOT NULL,
          structured_insight_json JSONB,
          suggested_actions_json JSONB,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_copilot_messages_conversation
          ON copilot_messages (conversation_id, created_at);

        CREATE TABLE IF NOT EXISTS copilot_citations (
          id BIGSERIAL PRIMARY KEY,
          message_id TEXT NOT NULL,
          evidence_id TEXT,
          chunk_id BIGINT,
          document_id BIGINT,
          title TEXT,
          source TEXT,
          dataset TEXT,
          event_time TIMESTAMPTZ,
          url TEXT,
          snippet TEXT,
          metadata_json JSONB,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_copilot_citations_message
          ON copilot_citations (message_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_copilot_citations_message;
        DROP TABLE IF EXISTS copilot_citations;
        DROP INDEX IF EXISTS idx_copilot_messages_conversation;
        DROP TABLE IF EXISTS copilot_messages;
        DROP TABLE IF EXISTS copilot_conversations;
        DROP TABLE IF EXISTS data_quality_reports;
        DROP TABLE IF EXISTS market_opportunity_snapshots;
        DROP INDEX IF EXISTS idx_prospect_scores_rank;
        DROP TABLE IF EXISTS prospect_scores;
        DROP INDEX IF EXISTS idx_prospect_signals_lookup;
        DROP TABLE IF EXISTS prospect_signals;
        DROP INDEX IF EXISTS idx_prospect_evidence_source;
        DROP INDEX IF EXISTS idx_prospect_evidence_lookup;
        DROP TABLE IF EXISTS prospect_evidence_items;
        DROP INDEX IF EXISTS idx_prospects_region_industry;
        DROP TABLE IF EXISTS prospects;
        """
    )
