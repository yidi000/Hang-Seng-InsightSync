from __future__ import annotations

import argparse
import json

from insightsync.backend.core.config import get_settings
from insightsync.backend.db.session import SessionLocal
from insightsync.backend.services.embedding_service import EmbeddingService
from insightsync.backend.services.rag_document_builder import RagDocumentBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or update the InsightSync RAG index.")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--documents", action="store_true")
    parser.add_argument("--chunks", action="store_true")
    parser.add_argument("--embeddings", action="store_true")
    parser.add_argument("--batch-size", type=int, default=64)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.full:
        args.documents = True
        args.chunks = True
        args.embeddings = True
    if not (args.documents or args.chunks or args.embeddings):
        args.documents = True
        args.chunks = True

    settings = get_settings()
    summary: dict[str, dict[str, int]] = {}
    with SessionLocal() as db:
        try:
            builder = RagDocumentBuilder(db)
            if args.documents:
                summary["documents"] = builder.build_documents()
            if args.chunks:
                summary["chunks"] = builder.build_chunks()
            if args.embeddings:
                summary["embeddings"] = EmbeddingService(db, settings).embed_all_missing(batch_size=args.batch_size)
            db.commit()
        except Exception:
            db.rollback()
            raise
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
