"""Create backend mirror and RAG schema.

Revision ID: 0001_backend_rag_schema
Revises:
Create Date: 2026-04-16
"""
from __future__ import annotations

from alembic import op

revision = "0001_backend_rag_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_runs (
          run_id TEXT PRIMARY KEY,
          started_at TEXT NOT NULL,
          finished_at TEXT,
          status TEXT NOT NULL,
          message TEXT,
          summary_json JSONB
        );

        CREATE TABLE IF NOT EXISTS intelligence_records (
          id BIGSERIAL PRIMARY KEY,
          source TEXT NOT NULL,
          dataset TEXT NOT NULL,
          record_key TEXT NOT NULL,
          record_type TEXT NOT NULL,
          company_id TEXT,
          entity TEXT,
          event_time TEXT,
          title TEXT,
          summary TEXT,
          region TEXT,
          industry TEXT,
          lang TEXT,
          evidence_url TEXT,
          tags_json JSONB,
          payload_json JSONB NOT NULL,
          raw_json JSONB,
          content_hash TEXT NOT NULL,
          fetched_at TEXT NOT NULL,
          run_id TEXT NOT NULL,
          CONSTRAINT uq_intelligence_record_hash UNIQUE (source, dataset, record_key, content_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_intelligence_lookup
          ON intelligence_records (source, dataset, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_intelligence_entity_time
          ON intelligence_records (entity, event_time DESC);

        CREATE TABLE IF NOT EXISTS trigger_signals (
          id BIGSERIAL PRIMARY KEY,
          source TEXT NOT NULL,
          dataset TEXT NOT NULL,
          signal_key TEXT NOT NULL,
          signal_type TEXT NOT NULL,
          company_id TEXT,
          entity TEXT,
          event_time TEXT NOT NULL,
          indicator TEXT,
          value_num DOUBLE PRECISION,
          value_text TEXT,
          unit TEXT,
          signal_text TEXT,
          signal_score DOUBLE PRECISION,
          signal_level TEXT,
          evidence_refs_json JSONB,
          extra_json JSONB,
          row_hash TEXT NOT NULL,
          fetched_at TEXT NOT NULL,
          run_id TEXT NOT NULL,
          CONSTRAINT uq_trigger_signal_hash UNIQUE (source, dataset, signal_key, row_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_trigger_lookup
          ON trigger_signals (source, signal_type, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_trigger_entity_type_time
          ON trigger_signals (entity, signal_type, event_time DESC);

        CREATE TABLE IF NOT EXISTS client_one_view_timeline (
          id BIGSERIAL PRIMARY KEY,
          source TEXT NOT NULL,
          company_id TEXT,
          entity TEXT,
          event_time TEXT,
          event_type TEXT NOT NULL,
          headline TEXT NOT NULL,
          detail TEXT,
          evidence_url TEXT,
          payload_json JSONB,
          dedup_hash TEXT NOT NULL,
          fetched_at TEXT NOT NULL,
          run_id TEXT NOT NULL,
          CONSTRAINT uq_timeline_dedup_hash UNIQUE (source, dedup_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_timeline_lookup
          ON client_one_view_timeline (company_id, entity, event_time DESC);
        CREATE INDEX IF NOT EXISTS idx_timeline_entity_time
          ON client_one_view_timeline (entity, event_time DESC);

        CREATE TABLE IF NOT EXISTS generated_insights (
          id BIGSERIAL PRIMARY KEY,
          source TEXT NOT NULL,
          company_id TEXT,
          entity TEXT,
          insight_type TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          confidence DOUBLE PRECISION,
          evidence_record_keys_json JSONB,
          evidence_signal_keys_json JSONB,
          model_name TEXT,
          model_version TEXT,
          prompt_version TEXT,
          meta_json JSONB,
          generated_at TEXT NOT NULL,
          run_id TEXT NOT NULL,
          dedup_hash TEXT NOT NULL UNIQUE
        );
        CREATE INDEX IF NOT EXISTS idx_generated_insights_lookup
          ON generated_insights (company_id, entity, insight_type, generated_at DESC);

        CREATE TABLE IF NOT EXISTS rag_documents (
          id BIGSERIAL PRIMARY KEY,
          source_table TEXT NOT NULL,
          source_id BIGINT NOT NULL,
          source TEXT NOT NULL,
          dataset TEXT,
          record_key TEXT,
          signal_key TEXT,
          entity TEXT,
          company_id TEXT,
          event_time TEXT,
          record_type TEXT,
          signal_type TEXT,
          region TEXT,
          industry TEXT,
          lang TEXT,
          evidence_url TEXT,
          title TEXT,
          content TEXT NOT NULL,
          metadata_json JSONB,
          content_hash TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_rag_document_source_hash UNIQUE (source_table, source_id, content_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata
          ON rag_documents (entity, source, dataset, event_time DESC);

        CREATE TABLE IF NOT EXISTS rag_chunks (
          id BIGSERIAL PRIMARY KEY,
          document_id BIGINT NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
          chunk_index INTEGER NOT NULL,
          chunk_text TEXT NOT NULL,
          chunk_hash TEXT NOT NULL,
          token_count INTEGER NOT NULL,
          metadata_json JSONB,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_rag_chunk_hash UNIQUE (document_id, chunk_index, chunk_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_rag_chunks_document
          ON rag_chunks (document_id, chunk_index);

        CREATE TABLE IF NOT EXISTS rag_embeddings (
          id BIGSERIAL PRIMARY KEY,
          chunk_id BIGINT NOT NULL REFERENCES rag_chunks(id) ON DELETE CASCADE,
          embedding_model TEXT NOT NULL,
          embedding vector(1536) NOT NULL,
          embedding_hash TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_rag_embedding_model_hash UNIQUE (chunk_id, embedding_model, embedding_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_rag_embeddings_vector
          ON rag_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

        CREATE TABLE IF NOT EXISTS rag_retrieval_runs (
          id BIGSERIAL PRIMARY KEY,
          question TEXT NOT NULL,
          filters_json JSONB,
          top_k INTEGER NOT NULL,
          results_json JSONB,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS llm_generation_runs (
          id BIGSERIAL PRIMARY KEY,
          retrieval_run_id BIGINT REFERENCES rag_retrieval_runs(id) ON DELETE SET NULL,
          prompt_version TEXT NOT NULL,
          model_name TEXT NOT NULL,
          input_json JSONB,
          output_json JSONB,
          status TEXT NOT NULL,
          error TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS llm_generation_runs;
        DROP TABLE IF EXISTS rag_retrieval_runs;
        DROP TABLE IF EXISTS rag_embeddings;
        DROP TABLE IF EXISTS rag_chunks;
        DROP TABLE IF EXISTS rag_documents;
        DROP TABLE IF EXISTS generated_insights;
        DROP TABLE IF EXISTS client_one_view_timeline;
        DROP TABLE IF EXISTS trigger_signals;
        DROP TABLE IF EXISTS intelligence_records;
        DROP TABLE IF EXISTS ingestion_runs;
        """
    )
