from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RagFilters(BaseModel):
    """Metadata filters for RAG retrieval."""

    entity: str | None = None
    company_id: str | None = None
    signal_type: str | None = None
    source: str | None = None
    dataset: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class RagQueryIn(BaseModel):
    """RAG query request."""

    question: str = Field(min_length=1)
    filters: RagFilters = Field(default_factory=RagFilters)
    top_k: int | None = Field(default=None, ge=1, le=20)
    include_chunks: bool = False


class CitationOut(BaseModel):
    """Evidence citation returned with a RAG answer."""

    chunk_id: int
    document_id: int
    score: float
    source: str
    dataset: str | None = None
    record_key: str | None = None
    signal_key: str | None = None
    evidence_url: str | None = None
    text: str | None = None


class RagQueryOut(BaseModel):
    """RAG query response."""

    answer: str
    status: str
    retrieval_run_id: int | None = None
    citations: list[CitationOut]
    structured_insight: dict[str, Any] | None = None


class RagIndexStatusOut(BaseModel):
    """RAG index status response."""

    document_count: int
    chunk_count: int
    embedded_chunk_count: int
    embedding_model: str
    last_indexed_at: str | None = None


class GenerateInsightIn(BaseModel):
    """Trusted insight generation request."""

    question: str = Field(min_length=1)
    insight_type: str = "explanation"
    filters: RagFilters = Field(default_factory=RagFilters)


class GeneratedInsightOut(BaseModel):
    """Generated insight response."""

    status: str
    insight: dict[str, Any] | None = None
    citations: list[CitationOut]
