"""Replace ivfflat index on rag_embeddings with HNSW.

Revision ID: 0003_rag_hnsw_index
Revises: 0002_event_time_timestamptz
Create Date: 2026-04-18

Rationale: ivfflat performs poorly when the index is built on an empty
table (cluster centroids are meaningless until data lands). HNSW does not
need a build-time data distribution and works well at any size. Requires
pgvector >= 0.5.0.
"""
from __future__ import annotations

from alembic import op

revision = "0003_rag_hnsw_index"
down_revision = "0002_event_time_timestamptz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_rag_embeddings_vector;
        CREATE INDEX IF NOT EXISTS idx_rag_embeddings_vector
          ON rag_embeddings USING hnsw (embedding vector_cosine_ops)
          WITH (m = 16, ef_construction = 64);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_rag_embeddings_vector;
        CREATE INDEX IF NOT EXISTS idx_rag_embeddings_vector
          ON rag_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """
    )
