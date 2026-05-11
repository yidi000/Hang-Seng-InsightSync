"""Add prospect workflow state table.

Revision ID: 0006_prospect_workflow_states
Revises: 0005_parsed_document_tables
Create Date: 2026-05-11
"""
from __future__ import annotations

from alembic import op

revision = "0006_prospect_workflow_states"
down_revision = "0005_parsed_document_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prospect_workflow_states (
          prospect_id TEXT PRIMARY KEY,
          company_id TEXT NOT NULL,
          owner TEXT,
          stage TEXT NOT NULL DEFAULT 'new',
          status TEXT NOT NULL DEFAULT 'open',
          last_action TEXT,
          next_action TEXT,
          review_status TEXT NOT NULL DEFAULT 'not_reviewed',
          notes TEXT,
          updated_at TIMESTAMPTZ NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_prospect_workflow_company
          ON prospect_workflow_states (company_id);

        CREATE INDEX IF NOT EXISTS idx_prospect_workflow_stage
          ON prospect_workflow_states (stage, status, review_status);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_prospect_workflow_stage;
        DROP INDEX IF EXISTS idx_prospect_workflow_company;
        DROP TABLE IF EXISTS prospect_workflow_states;
        """
    )
