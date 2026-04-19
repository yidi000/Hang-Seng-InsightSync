"""Convert event_time and related timestamp columns from TEXT to TIMESTAMPTZ.

Revision ID: 0002_event_time_timestamptz
Revises: 0001_backend_rag_schema
Create Date: 2026-04-18
"""
from __future__ import annotations

from alembic import op

revision = "0002_event_time_timestamptz"
down_revision = "0001_backend_rag_schema"
branch_labels = None
depends_on = None


# Tables with event_time (nullable) + fetched_at columns.
_TABLES_WITH_EVENT_TIME_NULLABLE = [
    "intelligence_records",
    "client_one_view_timeline",
    "rag_documents",
]
# trigger_signals.event_time is NOT NULL.
_TABLES_WITH_EVENT_TIME_NOT_NULL = ["trigger_signals"]
_TABLES_WITH_FETCHED_AT = [
    "intelligence_records",
    "trigger_signals",
    "client_one_view_timeline",
]


def upgrade() -> None:
    # Drop indexes that reference event_time so ALTER TYPE can run.
    op.execute(
        """
        DROP INDEX IF EXISTS idx_intelligence_lookup;
        DROP INDEX IF EXISTS idx_intelligence_entity_time;
        DROP INDEX IF EXISTS idx_trigger_lookup;
        DROP INDEX IF EXISTS idx_trigger_entity_type_time;
        DROP INDEX IF EXISTS idx_timeline_lookup;
        DROP INDEX IF EXISTS idx_timeline_entity_time;
        DROP INDEX IF EXISTS idx_rag_documents_metadata;
        """
    )

    # Helper to parse flexible legacy formats (YYYY, YYYY-MM, YYYY-MM-DD, ISO, slash dates).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION insightsync_parse_loose_ts(raw text)
        RETURNS timestamptz AS $$
        DECLARE
          v text;
        BEGIN
          IF raw IS NULL THEN RETURN NULL; END IF;
          v := btrim(raw);
          IF v = '' THEN RETURN NULL; END IF;
          -- Slash dates → dashes.
          v := replace(v, '/', '-');
          -- YYYY → YYYY-01-01
          IF v ~ '^\\d{4}$' THEN
            RETURN (v || '-01-01')::timestamptz;
          END IF;
          -- YYYY-MM → YYYY-MM-01
          IF v ~ '^\\d{4}-\\d{1,2}$' THEN
            RETURN (v || '-01')::timestamptz;
          END IF;
          -- Otherwise, rely on Postgres to parse.
          BEGIN
            RETURN v::timestamptz;
          EXCEPTION WHEN others THEN
            RETURN NULL;
          END;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
        """
    )

    for table in _TABLES_WITH_EVENT_TIME_NULLABLE:
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN event_time TYPE TIMESTAMPTZ
            USING insightsync_parse_loose_ts(event_time)
            """
        )
    for table in _TABLES_WITH_EVENT_TIME_NOT_NULL:
        # For NOT NULL columns, keep the constraint; rows with unparseable values
        # must be remediated before this migration — fail fast if any are bad.
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN event_time TYPE TIMESTAMPTZ
            USING insightsync_parse_loose_ts(event_time)
            """
        )
    for table in _TABLES_WITH_FETCHED_AT:
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN fetched_at TYPE TIMESTAMPTZ
            USING insightsync_parse_loose_ts(fetched_at)
            """
        )

    op.execute(
        """
        ALTER TABLE generated_insights
        ALTER COLUMN generated_at TYPE TIMESTAMPTZ
        USING insightsync_parse_loose_ts(generated_at);
        ALTER TABLE ingestion_runs
        ALTER COLUMN started_at TYPE TIMESTAMPTZ
        USING insightsync_parse_loose_ts(started_at);
        ALTER TABLE ingestion_runs
        ALTER COLUMN finished_at TYPE TIMESTAMPTZ
        USING insightsync_parse_loose_ts(finished_at);
        """
    )

    op.execute("DROP FUNCTION IF EXISTS insightsync_parse_loose_ts(text)")

    # Recreate indexes.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_intelligence_lookup
          ON intelligence_records (source, dataset, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_intelligence_entity_time
          ON intelligence_records (entity, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_trigger_lookup
          ON trigger_signals (source, signal_type, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_trigger_entity_type_time
          ON trigger_signals (entity, signal_type, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_timeline_lookup
          ON client_one_view_timeline (company_id, entity, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_timeline_entity_time
          ON client_one_view_timeline (entity, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata
          ON rag_documents (entity, source, dataset, event_time DESC);
        """
    )


def downgrade() -> None:
    # Cast back to TEXT; original representation cannot be perfectly recovered.
    for table in _TABLES_WITH_EVENT_TIME_NULLABLE + _TABLES_WITH_EVENT_TIME_NOT_NULL:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN event_time TYPE TEXT USING event_time::text")
    for table in _TABLES_WITH_FETCHED_AT:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN fetched_at TYPE TEXT USING fetched_at::text")
    op.execute(
        """
        ALTER TABLE generated_insights ALTER COLUMN generated_at TYPE TEXT USING generated_at::text;
        ALTER TABLE ingestion_runs ALTER COLUMN started_at TYPE TEXT USING started_at::text;
        ALTER TABLE ingestion_runs ALTER COLUMN finished_at TYPE TEXT USING finished_at::text;
        """
    )
