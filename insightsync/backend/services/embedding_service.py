from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.core.config import Settings
from insightsync.backend.utils import stable_hash


def vector_literal(values: list[float]) -> str:
    """Format a vector for pgvector SQL casts."""

    return "[" + ",".join(f"{value:.10f}" for value in values) + "]"


class EmbeddingService:
    """Generate and persist embeddings for RAG chunks."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = OpenAIProvider(settings)

    def embed_missing_chunks(self, *, batch_size: int = 64) -> dict[str, int]:
        """Embed chunks that are missing embeddings for the configured model."""

        rows = self.db.execute(
            text(
                """
                SELECT c.id, c.chunk_text, c.chunk_hash
                FROM rag_chunks c
                LEFT JOIN rag_embeddings e
                  ON e.chunk_id = c.id AND e.embedding_model = :model
                WHERE e.id IS NULL
                ORDER BY c.id
                LIMIT :limit
                """
            ),
            {"model": self.settings.openai_embedding_model, "limit": batch_size},
        ).mappings().all()
        if not rows:
            return {"scanned": 0, "inserted": 0}

        embeddings = self.provider.embed_texts([row["chunk_text"] for row in rows])
        inserted = 0
        for row, embedding in zip(rows, embeddings, strict=True):
            embedding_hash = stable_hash({"chunk_hash": row["chunk_hash"], "model": self.settings.openai_embedding_model})
            result = self.db.execute(
                text(
                    """
                    INSERT INTO rag_embeddings (chunk_id, embedding_model, embedding, embedding_hash)
                    VALUES (:chunk_id, :model, CAST(:embedding AS vector), :embedding_hash)
                    ON CONFLICT (chunk_id, embedding_model, embedding_hash) DO NOTHING
                    """
                ),
                {
                    "chunk_id": row["id"],
                    "model": self.settings.openai_embedding_model,
                    "embedding": vector_literal(embedding),
                    "embedding_hash": embedding_hash,
                },
            )
            inserted += int(result.rowcount or 0)
        return {"scanned": len(rows), "inserted": inserted}

    def embed_all_missing(self, *, batch_size: int = 64) -> dict[str, int]:
        """Embed all missing chunks in batches."""

        total_scanned = 0
        total_inserted = 0
        while True:
            result = self.embed_missing_chunks(batch_size=batch_size)
            total_scanned += result["scanned"]
            total_inserted += result["inserted"]
            if result["scanned"] == 0:
                break
        return {"scanned": total_scanned, "inserted": total_inserted}
