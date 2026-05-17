from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config

from insightsync.backend.core.config import get_settings
from insightsync.backend.db.session import SessionLocal
from insightsync.backend.services.embedding_service import EmbeddingService
from insightsync.backend.services.rag_document_builder import RagDocumentBuilder
from insightsync.backend.workflows.sync_from_sqlite import sync_from_sqlite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a frontend-ready local/dev backend database."
    )
    parser.add_argument("--skip-migrations", action="store_true")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-rag", action="store_true")
    parser.add_argument("--sqlite-source-path", type=Path, default=None)
    parser.add_argument("--rag-batch-size", type=int, default=64)
    return parser


def run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def run_sqlite_sync(sqlite_source_path: Path) -> dict[str, Any]:
    with SessionLocal() as db:
        return sync_from_sqlite(sqlite_source_path, db)


def run_rag_build(*, batch_size: int) -> dict[str, Any]:
    settings = get_settings()
    summary: dict[str, Any] = {}
    with SessionLocal() as db:
        try:
            builder = RagDocumentBuilder(db)
            summary["documents"] = builder.build_documents()
            summary["chunks"] = builder.build_chunks()
            summary["embeddings"] = EmbeddingService(db, settings).embed_all_missing(batch_size=batch_size)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return summary


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    sqlite_source_path = Path(args.sqlite_source_path or settings.sqlite_source_path)

    summary: dict[str, Any] = {
        "database_url": settings.database_url,
        "sqlite_source_path": str(sqlite_source_path),
        "migrations": "skipped" if args.skip_migrations else "pending",
        "sqlite_sync": "skipped" if args.skip_sync else "pending",
        "rag_index": "skipped" if args.skip_rag else "pending",
    }

    if not args.skip_migrations:
        run_migrations()
        summary["migrations"] = "completed"
    if not args.skip_sync:
        summary["sqlite_sync"] = run_sqlite_sync(sqlite_source_path)
    if not args.skip_rag:
        summary["rag_index"] = run_rag_build(batch_size=max(1, int(args.rag_batch_size)))

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
