"""Add company mirror tables for SQLite sync.

Revision ID: 0004_company_tables_sync
Revises: 0003_rag_hnsw_index
Create Date: 2026-04-22
"""
from __future__ import annotations

from alembic import op

revision = "0004_company_tables_sync"
down_revision = "0003_rag_hnsw_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
          id BIGSERIAL PRIMARY KEY,
          source TEXT NOT NULL,
          company_id TEXT NOT NULL,
          canonical_name TEXT NOT NULL,
          display_name TEXT,
          country TEXT,
          region TEXT,
          city TEXT,
          segments_json JSONB,
          industries_json JSONB,
          website_url TEXT,
          linkedin_url TEXT,
          facebook_url TEXT,
          x_url TEXT,
          instagram_url TEXT,
          wikipedia_url TEXT,
          profile_summary TEXT,
          description TEXT,
          extra_json JSONB,
          row_hash TEXT NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL,
          run_id TEXT NOT NULL,
          CONSTRAINT uq_companies_company_hash UNIQUE (company_id, row_hash)
        );

        CREATE INDEX IF NOT EXISTS idx_companies_lookup
          ON companies (company_id, canonical_name, country, region);

        CREATE TABLE IF NOT EXISTS company_mapping_audit (
          id BIGSERIAL PRIMARY KEY,
          run_id TEXT NOT NULL,
          target_table TEXT NOT NULL,
          target_row_id BIGINT NOT NULL,
          old_company_id TEXT,
          new_company_id TEXT NOT NULL,
          mapping_method TEXT NOT NULL,
          confidence DOUBLE PRECISION,
          matched_alias TEXT,
          matched_context TEXT,
          mapped_at TIMESTAMPTZ NOT NULL,
          CONSTRAINT uq_company_mapping_audit UNIQUE (
            run_id,
            target_table,
            target_row_id,
            new_company_id,
            mapping_method
          )
        );

        CREATE INDEX IF NOT EXISTS idx_company_mapping_audit_lookup
          ON company_mapping_audit (target_table, target_row_id, mapped_at DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_company_mapping_audit_lookup;
        DROP TABLE IF EXISTS company_mapping_audit;

        DROP INDEX IF EXISTS idx_companies_lookup;
        DROP TABLE IF EXISTS companies;
        """
    )
