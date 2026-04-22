from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """Minimal pgvector type so SQLAlchemy metadata matches the migration."""

    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: object) -> str:
        return f"vector({self.dimensions})"

metadata = MetaData()

ingestion_runs = Table(
    "ingestion_runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", Text, nullable=False),
    Column("message", Text),
    Column("summary_json", JSONB),
)

intelligence_records = Table(
    "intelligence_records",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source", Text, nullable=False),
    Column("dataset", Text, nullable=False),
    Column("record_key", Text, nullable=False),
    Column("record_type", Text, nullable=False),
    Column("company_id", Text),
    Column("entity", Text),
    Column("event_time", DateTime(timezone=True)),
    Column("title", Text),
    Column("summary", Text),
    Column("region", Text),
    Column("industry", Text),
    Column("lang", Text),
    Column("evidence_url", Text),
    Column("tags_json", JSONB),
    Column("payload_json", JSONB, nullable=False),
    Column("raw_json", JSONB),
    Column("content_hash", Text, nullable=False),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Text, nullable=False),
    UniqueConstraint("source", "dataset", "record_key", "content_hash", name="uq_intelligence_record_hash"),
)

trigger_signals = Table(
    "trigger_signals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source", Text, nullable=False),
    Column("dataset", Text, nullable=False),
    Column("signal_key", Text, nullable=False),
    Column("signal_type", Text, nullable=False),
    Column("company_id", Text),
    Column("entity", Text),
    Column("event_time", DateTime(timezone=True), nullable=False),
    Column("indicator", Text),
    Column("value_num", Float),
    Column("value_text", Text),
    Column("unit", Text),
    Column("signal_text", Text),
    Column("signal_score", Float),
    Column("signal_level", Text),
    Column("evidence_refs_json", JSONB),
    Column("extra_json", JSONB),
    Column("row_hash", Text, nullable=False),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Text, nullable=False),
    UniqueConstraint("source", "dataset", "signal_key", "row_hash", name="uq_trigger_signal_hash"),
)

client_one_view_timeline = Table(
    "client_one_view_timeline",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source", Text, nullable=False),
    Column("company_id", Text),
    Column("entity", Text),
    Column("event_time", DateTime(timezone=True)),
    Column("event_type", Text, nullable=False),
    Column("headline", Text, nullable=False),
    Column("detail", Text),
    Column("evidence_url", Text),
    Column("payload_json", JSONB),
    Column("dedup_hash", Text, nullable=False),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Text, nullable=False),
    UniqueConstraint("source", "dedup_hash", name="uq_timeline_dedup_hash"),
)

generated_insights = Table(
    "generated_insights",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source", Text, nullable=False),
    Column("company_id", Text),
    Column("entity", Text),
    Column("insight_type", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("summary", Text, nullable=False),
    Column("confidence", Float),
    Column("evidence_record_keys_json", JSONB),
    Column("evidence_signal_keys_json", JSONB),
    Column("model_name", Text),
    Column("model_version", Text),
    Column("prompt_version", Text),
    Column("meta_json", JSONB),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Text, nullable=False),
    Column("dedup_hash", Text, nullable=False, unique=True),
)

companies = Table(
    "companies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source", Text, nullable=False),
    Column("company_id", Text, nullable=False),
    Column("canonical_name", Text, nullable=False),
    Column("display_name", Text),
    Column("country", Text),
    Column("region", Text),
    Column("city", Text),
    Column("segments_json", JSONB),
    Column("industries_json", JSONB),
    Column("website_url", Text),
    Column("linkedin_url", Text),
    Column("facebook_url", Text),
    Column("x_url", Text),
    Column("instagram_url", Text),
    Column("wikipedia_url", Text),
    Column("profile_summary", Text),
    Column("description", Text),
    Column("extra_json", JSONB),
    Column("row_hash", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Text, nullable=False),
    UniqueConstraint("company_id", "row_hash", name="uq_companies_company_hash"),
)

company_mapping_audit = Table(
    "company_mapping_audit",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", Text, nullable=False),
    Column("target_table", Text, nullable=False),
    Column("target_row_id", Integer, nullable=False),
    Column("old_company_id", Text),
    Column("new_company_id", Text, nullable=False),
    Column("mapping_method", Text, nullable=False),
    Column("confidence", Float),
    Column("matched_alias", Text),
    Column("matched_context", Text),
    Column("mapped_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "run_id",
        "target_table",
        "target_row_id",
        "new_company_id",
        "mapping_method",
        name="uq_company_mapping_audit",
    ),
)

rag_documents = Table(
    "rag_documents",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source_table", Text, nullable=False),
    Column("source_id", Integer, nullable=False),
    Column("source", Text, nullable=False),
    Column("dataset", Text),
    Column("record_key", Text),
    Column("signal_key", Text),
    Column("entity", Text),
    Column("company_id", Text),
    Column("event_time", DateTime(timezone=True)),
    Column("record_type", Text),
    Column("signal_type", Text),
    Column("region", Text),
    Column("industry", Text),
    Column("lang", Text),
    Column("evidence_url", Text),
    Column("title", Text),
    Column("content", Text, nullable=False),
    Column("metadata_json", JSONB),
    Column("content_hash", Text, nullable=False),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    UniqueConstraint("source_table", "source_id", "content_hash", name="uq_rag_document_source_hash"),
)

rag_chunks = Table(
    "rag_chunks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("document_id", Integer, nullable=False),
    Column("chunk_index", Integer, nullable=False),
    Column("chunk_text", Text, nullable=False),
    Column("chunk_hash", Text, nullable=False),
    Column("token_count", Integer, nullable=False),
    Column("metadata_json", JSONB),
    Column("created_at", DateTime(timezone=True)),
    UniqueConstraint("document_id", "chunk_index", "chunk_hash", name="uq_rag_chunk_hash"),
)

rag_embeddings = Table(
    "rag_embeddings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("chunk_id", Integer, ForeignKey("rag_chunks.id", ondelete="CASCADE"), nullable=False),
    Column("embedding_model", Text, nullable=False),
    Column("embedding", Vector(1536), nullable=False),
    Column("embedding_hash", Text, nullable=False),
    Column("created_at", DateTime(timezone=True)),
    UniqueConstraint("chunk_id", "embedding_model", "embedding_hash", name="uq_rag_embedding_model_hash"),
)

rag_retrieval_runs = Table(
    "rag_retrieval_runs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("question", Text, nullable=False),
    Column("filters_json", JSONB),
    Column("top_k", Integer, nullable=False),
    Column("results_json", JSONB),
    Column("created_at", DateTime(timezone=True)),
)

llm_generation_runs = Table(
    "llm_generation_runs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("retrieval_run_id", Integer),
    Column("prompt_version", Text, nullable=False),
    Column("model_name", Text, nullable=False),
    Column("input_json", JSONB),
    Column("output_json", JSONB),
    Column("status", Text, nullable=False),
    Column("error", Text),
    Column("created_at", DateTime(timezone=True)),
)
