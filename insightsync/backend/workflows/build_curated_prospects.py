from __future__ import annotations

import argparse
import json

from insightsync.backend.db.session import SessionLocal
from insightsync.backend.services.curated_builder import CuratedProspectBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build curated prospect, evidence, signal, score, and market tables.")
    parser.add_argument("--quality-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    with SessionLocal() as db:
        try:
            builder = CuratedProspectBuilder(db)
            summary = builder.build_quality_report() if args.quality_only else builder.build_all()
            db.commit()
        except Exception:
            db.rollback()
            raise
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
