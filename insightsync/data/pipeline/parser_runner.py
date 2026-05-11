from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insightsync.parsing import DEFAULT_PARSE_VERSION, parse_content
from insightsync.parsing.genai_extractor import GenAIExtractionConfig, enhance_parsed_document_with_genai
from insightsync.parsing.request_builders import build_parse_request_from_row

from .storage import SQLiteRepository
from .utils import utc_now_iso


@dataclass(slots=True)
class ParsingConfig:
    db_path: Path = Path("insightsync/data/storage/insightsync.db")
    raw_dir: Path = Path("insightsync/data/storage/raw")
    parse_version: str = DEFAULT_PARSE_VERSION
    limit: int = 0
    force: bool = False
    enable_genai_extraction: bool = False
    genai_max_candidates: int = 8


def run_parsing_once(config: ParsingConfig) -> dict[str, Any]:
    cfg = ParsingConfig(
        db_path=Path(config.db_path).expanduser().resolve(),
        raw_dir=Path(config.raw_dir).expanduser().resolve(),
        parse_version=config.parse_version,
        limit=max(0, int(config.limit)),
        force=bool(config.force),
        enable_genai_extraction=bool(config.enable_genai_extraction),
        genai_max_candidates=max(1, int(config.genai_max_candidates)),
    )
    run_id = datetime.now(timezone.utc).strftime("parse-%Y%m%dT%H%M%SZ")
    started_at = utc_now_iso()

    with SQLiteRepository(cfg.db_path) as repo:
        repo.start_parsing_run(run_id, parse_version=cfg.parse_version, started_at=started_at)
        candidates = repo.parsing_candidates(
            parse_version=cfg.parse_version,
            limit=cfg.limit,
            force=cfg.force,
        )
        inserted = 0
        skipped = 0
        errors: list[dict[str, Any]] = []
        genai_provider = None
        if cfg.enable_genai_extraction:
            from insightsync.backend.ai.providers.openai_client import OpenAIProvider
            from insightsync.backend.core.config import Settings

            genai_provider = OpenAIProvider(Settings())

        for row in candidates:
            try:
                request, request_warnings = build_parse_request_from_row(row, raw_root=cfg.raw_dir)
                parsed = parse_content(request)
                if genai_provider is not None:
                    parsed = enhance_parsed_document_with_genai(
                        parsed,
                        chat_json=genai_provider.chat_json,
                        config=GenAIExtractionConfig(max_candidates=cfg.genai_max_candidates),
                    )
                inserted += repo.persist_parsed_document(
                    source_row=row,
                    parsed=parsed,
                    parse_version=cfg.parse_version,
                    run_id=run_id,
                    parsed_at=utc_now_iso(),
                    extra_warnings=request_warnings,
                    replace=cfg.force,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "source_id": row.get("source_id"),
                        "source": row.get("source"),
                        "dataset": row.get("dataset"),
                        "title": row.get("title"),
                        "error": str(exc),
                    }
                )

        scanned = len(candidates)
        skipped = max(0, scanned - inserted - len(errors))
        status = "success" if not errors else ("failed" if len(errors) == scanned and scanned > 0 else "partial_success")
        summary = {
            "run_id": run_id,
            "parse_version": cfg.parse_version,
            "db_path": str(cfg.db_path),
            "raw_dir": str(cfg.raw_dir),
            "scanned": scanned,
            "inserted": inserted,
            "skipped": skipped,
            "genai_extraction_enabled": cfg.enable_genai_extraction,
            "errors": errors,
            "finished_at": utc_now_iso(),
        }
        repo.finish_parsing_run(
            run_id,
            status=status,
            message=f"{len(errors)} parsing errors" if errors else "parsed successfully",
            summary=summary,
        )
        return summary
