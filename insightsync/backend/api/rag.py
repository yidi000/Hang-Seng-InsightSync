from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.core.config import get_settings
from insightsync.backend.db.session import get_db
from insightsync.backend.schemas.rag import (
    CitationOut,
    RagIndexStatusOut,
    RagQueryIn,
    RagQueryOut,
)
from insightsync.backend.services.insight_generator import InsightGenerator

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/index/status", response_model=RagIndexStatusOut)
def index_status(db: Session = Depends(get_db)) -> RagIndexStatusOut:
    """Return RAG index status."""

    settings = get_settings()
    document_count = int(db.execute(text("SELECT COUNT(*) FROM rag_documents")).scalar_one())
    chunk_count = int(db.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar_one())
    embedded_count = int(
        db.execute(
            text("SELECT COUNT(DISTINCT chunk_id) FROM rag_embeddings WHERE embedding_model = :model"),
            {"model": settings.openai_embedding_model},
        ).scalar_one()
    )
    last_indexed_at = db.execute(text("SELECT MAX(created_at)::text FROM rag_chunks")).scalar_one()
    return RagIndexStatusOut(
        document_count=document_count,
        chunk_count=chunk_count,
        embedded_chunk_count=embedded_count,
        embedding_model=settings.openai_embedding_model,
        last_indexed_at=last_indexed_at,
    )


@router.post("/query", response_model=RagQueryOut)
def query_rag(payload: RagQueryIn, db: Session = Depends(get_db)) -> RagQueryOut:
    """Answer a question using evidence-grounded retrieval."""

    settings = get_settings()
    result = InsightGenerator(db, settings).answer_question(
        question=payload.question,
        filters=payload.filters.model_dump(exclude_none=True),
        top_k=payload.top_k,
    )
    db.commit()
    citations = [
        CitationOut(**{**item, "text": item.get("text") if payload.include_chunks else None})
        for item in result.get("citations", [])
    ]
    return RagQueryOut(
        answer=result["answer"],
        status=result["status"],
        retrieval_run_id=result.get("retrieval_run_id"),
        citations=citations,
        structured_insight=result.get("structured_insight"),
    )


