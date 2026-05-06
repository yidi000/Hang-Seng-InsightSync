from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.db.session import get_db
from insightsync.backend.repositories.read_repository import ReadRepository
from insightsync.backend.schemas.prospects import (
    ProspectDetailOut,
    ProspectEvidenceOut,
    ProspectInsightOut,
    ProspectListItemOut,
    ProspectListOut,
    ProspectScoreOut,
    ProspectSignalOut,
    ProspectTimelineOut,
)

router = APIRouter(prefix="/api/prospects", tags=["prospects"])


def _page_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


@router.get("", response_model=ProspectListOut)
def list_prospects(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=200),
    q: str | None = None,
    region: str | None = None,
    industry: str | None = None,
    tier: str | None = None,
    db: Session = Depends(get_db),
) -> ProspectListOut:
    params: dict[str, object] = {"limit": pageSize, "offset": _page_offset(page, pageSize)}
    clauses: list[str] = []
    if q:
        clauses.append("(LOWER(p.display_name) LIKE :q OR LOWER(COALESCE(p.canonical_name, '')) LIKE :q)")
        params["q"] = f"%{q.lower()}%"
    if region:
        clauses.append("p.region = :region")
        params["region"] = region
    if industry:
        clauses.append("p.industry = :industry")
        params["industry"] = industry
    if tier:
        clauses.append("s.tier = :tier")
        params["tier"] = tier
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    total = int(
        db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM prospects p
                LEFT JOIN prospect_scores s ON s.prospect_id = p.prospect_id
                {where_sql}
                """
            ),
            params,
        ).scalar_one()
    )
    rows = db.execute(
        text(
            f"""
            SELECT p.prospect_id, p.company_id, p.display_name, p.canonical_name, p.region,
                   p.industry, p.size_band, p.segments_json, p.last_activity_at,
                   s.score, s.tier, s.recommended_products_json, s.recommended_entry_angle
            FROM prospects p
            LEFT JOIN prospect_scores s ON s.prospect_id = p.prospect_id
            {where_sql}
            ORDER BY s.score DESC NULLS LAST, p.last_activity_at DESC NULLS LAST, p.display_name ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings()
    repo = ReadRepository(db)
    items = [
        ProspectListItemOut(
            prospect_id=row["prospect_id"],
            company_id=row.get("company_id"),
            display_name=row["display_name"],
            canonical_name=row.get("canonical_name"),
            region=row.get("region"),
            industry=row.get("industry"),
            size_band=row.get("size_band") or "unknown",
            segments=repo._json_field(row.get("segments_json"), []),
            last_activity_at=row.get("last_activity_at"),
            score=row.get("score"),
            tier=row.get("tier"),
            recommended_products=repo._json_field(row.get("recommended_products_json"), []),
            recommended_entry_angle=row.get("recommended_entry_angle"),
        )
        for row in rows
    ]
    return ProspectListOut(items=items, total=total, page=page, pageSize=pageSize)


@router.get("/{prospect_id}", response_model=ProspectDetailOut)
def get_prospect(prospect_id: str, db: Session = Depends(get_db)) -> ProspectDetailOut:
    row = db.execute(
        text(
            """
            SELECT p.prospect_id, p.company_id, p.display_name, p.canonical_name, p.region,
                   p.industry, p.size_band, p.segments_json, p.last_activity_at,
                   s.score, s.tier, s.reasons_json, s.recommended_products_json,
                   s.recommended_entry_angle, s.updated_at
            FROM prospects p
            LEFT JOIN prospect_scores s ON s.prospect_id = p.prospect_id
            WHERE p.prospect_id = :prospect_id
            """
        ),
        {"prospect_id": prospect_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": {"code": "NOT_FOUND", "message": "Prospect not found"}})
    repo = ReadRepository(db)
    stats = db.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*) FROM prospect_evidence_items WHERE prospect_id = :prospect_id) AS evidence_count,
              (SELECT COUNT(*) FROM prospect_signals WHERE prospect_id = :prospect_id) AS signal_count
            """
        ),
        {"prospect_id": prospect_id},
    ).mappings().first()
    score_detail = None
    if row.get("score") is not None:
        score_detail = ProspectScoreOut(
            score=row["score"],
            tier=row["tier"],
            reasons=repo._json_field(row.get("reasons_json"), []),
            recommended_products=repo._json_field(row.get("recommended_products_json"), []),
            recommended_entry_angle=row.get("recommended_entry_angle"),
            updated_at=row.get("updated_at"),
        )
    item = ProspectDetailOut(
        prospect_id=row["prospect_id"],
        company_id=row.get("company_id"),
        display_name=row["display_name"],
        canonical_name=row.get("canonical_name"),
        region=row.get("region"),
        industry=row.get("industry"),
        size_band=row.get("size_band") or "unknown",
        segments=repo._json_field(row.get("segments_json"), []),
        last_activity_at=row.get("last_activity_at"),
        score=row.get("score"),
        tier=row.get("tier"),
        recommended_products=repo._json_field(row.get("recommended_products_json"), []),
        recommended_entry_angle=row.get("recommended_entry_angle"),
        score_detail=score_detail,
        stats=dict(stats or {}),
    )
    item.latest_evidence = get_prospect_evidence(prospect_id, limit=5, db=db)
    item.latest_signals = get_prospect_signals(prospect_id, limit=5, db=db)
    return item


@router.get("/{prospect_id}/evidence", response_model=list[ProspectEvidenceOut])
def get_prospect_evidence(prospect_id: str, limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)) -> list[ProspectEvidenceOut]:
    repo = ReadRepository(db)
    rows = db.execute(
        text(
            """
            SELECT evidence_id, prospect_id, evidence_type, event_time, title, summary, url,
                   source, dataset, metadata_json
            FROM prospect_evidence_items
            WHERE prospect_id = :prospect_id
            ORDER BY event_time DESC NULLS LAST, id DESC
            LIMIT :limit
            """
        ),
        {"prospect_id": prospect_id, "limit": limit},
    ).mappings()
    return [ProspectEvidenceOut(**{**dict(row), "metadata": repo._json_field(row.get("metadata_json"), {})}) for row in rows]


@router.get("/{prospect_id}/signals", response_model=list[ProspectSignalOut])
def get_prospect_signals(prospect_id: str, limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)) -> list[ProspectSignalOut]:
    repo = ReadRepository(db)
    rows = db.execute(
        text(
            """
            SELECT signal_id, prospect_id, signal_type, signal_subtype, signal_level, signal_score,
                   event_time, signal_text, evidence_ids_json, metadata_json
            FROM prospect_signals
            WHERE prospect_id = :prospect_id
            ORDER BY event_time DESC NULLS LAST, id DESC
            LIMIT :limit
            """
        ),
        {"prospect_id": prospect_id, "limit": limit},
    ).mappings()
    return [
        ProspectSignalOut(
            **{
                **dict(row),
                "evidence_ids": repo._json_field(row.get("evidence_ids_json"), []),
                "metadata": repo._json_field(row.get("metadata_json"), {}),
            }
        )
        for row in rows
    ]


@router.get("/{prospect_id}/timeline", response_model=list[ProspectTimelineOut])
def get_prospect_timeline(prospect_id: str, limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)) -> list[ProspectTimelineOut]:
    rows = db.execute(
        text(
            """
            SELECT id, event_time, evidence_type AS event_type, title, summary, source, url
            FROM prospect_evidence_items
            WHERE prospect_id = :prospect_id
            ORDER BY event_time DESC NULLS LAST, id DESC
            LIMIT :limit
            """
        ),
        {"prospect_id": prospect_id, "limit": limit},
    ).mappings()
    return [ProspectTimelineOut(**dict(row)) for row in rows]


@router.get("/{prospect_id}/insights", response_model=list[ProspectInsightOut])
def get_prospect_insights(prospect_id: str, limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)) -> list[ProspectInsightOut]:
    rows = db.execute(
        text(
            """
            SELECT id, insight_type, title, summary, confidence, model_name, prompt_version, generated_at
            FROM generated_insights
            WHERE company_id = :prospect_id
            ORDER BY generated_at DESC, id DESC
            LIMIT :limit
            """
        ),
        {"prospect_id": prospect_id, "limit": limit},
    ).mappings()
    return [ProspectInsightOut(**dict(row)) for row in rows]
