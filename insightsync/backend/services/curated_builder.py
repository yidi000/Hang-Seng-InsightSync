from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from insightsync.backend.services.company_mapping_quality import EXCLUDED_MACRO_SOURCE_TOKENS, mapping_coverage
from insightsync.backend.services.prospect_scoring import (
    EvidenceRef,
    ProspectScoreInput,
    assign_percentile_tier,
    build_score_reasons,
    calculate_score,
    entry_angle_for_subtypes,
    recommended_products_for_subtypes,
)
from insightsync.backend.utils import stable_hash

SIGNAL_SUBTYPES = {
    "growth",
    "funding",
    "expansion",
    "mna",
    "policy",
    "trade",
    "cross_border",
    "risk",
    "market_attention",
    "hiring",
}


def _macro_source_exclusion_params() -> dict[str, str]:
    return {f"excluded_macro_source_{idx}": token for idx, token in enumerate(EXCLUDED_MACRO_SOURCE_TOKENS)}


def _company_mappable_source_predicate(table_alias: str) -> str:
    excluded_values = ", ".join(f"(:excluded_macro_source_{idx})" for idx, _ in enumerate(EXCLUDED_MACRO_SOURCE_TOKENS))
    return f"""
            NOT EXISTS (
              SELECT 1
              FROM (VALUES {excluded_values}) AS excluded_macro_sources(token)
              WHERE LOWER(CONCAT_WS(' ', {table_alias}.source, {table_alias}.dataset)) LIKE '%' || excluded_macro_sources.token || '%'
            )
        """


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def infer_signal_subtype(*parts: Any) -> str:
    text_value = " ".join(_clean_text(part).lower() for part in parts if part)
    if any(token in text_value for token in ("hire", "hiring", "recruit", "招聘", "人才")):
        return "hiring"
    if any(token in text_value for token in ("fund", "financ", "loan", "credit", "bond", "placing", "募资", "融资", "贷款", "发债")):
        return "funding"
    if any(token in text_value for token in ("expand", "expansion", "new project", "investment", "投资", "扩张", "新项目", "开设")):
        return "expansion"
    if any(token in text_value for token in ("merger", "acquisition", "m&a", "restructur", "收购", "并购", "重组")):
        return "mna"
    if any(token in text_value for token in ("policy", "regulat", "budget", "政府", "政策", "监管", "财政")):
        return "policy"
    if any(token in text_value for token in ("trade", "export", "import", "cross-border", "cross border", "跨境", "贸易", "出口", "进口")):
        return "trade" if "cross" not in text_value and "跨境" not in text_value else "cross_border"
    if any(token in text_value for token in ("risk", "warning", "default", "impair", "违规", "问询", "风险", "处罚")):
        return "risk"
    if any(token in text_value for token in ("holding", "shareholding", "northbound", "southbound", "增持", "持股", "资金")):
        return "market_attention"
    if any(token in text_value for token in ("growth", "gdp", "increase", "yoy", "同比", "增长", "增速")):
        return "growth"
    return "cross_border" if "cross_border" in text_value else "growth"


def infer_evidence_type(source: str | None, dataset: str | None, record_type: str | None = None) -> str:
    text_value = f"{source or ''} {dataset or ''} {record_type or ''}".lower()
    if any(token in text_value for token in ("hkex", "szse", "announcement", "disclosure")):
        return "announcement"
    if any(token in text_value for token in ("investhk", "news", "hkgov", "press_release")):
        return "news" if "policy" not in text_value else "policy"
    if any(token in text_value for token in ("kpmg", "annual_report", "pdf", "parsed")):
        return "annual_report"
    if any(token in text_value for token in ("dongfang", "eastmoney", "holding", "connect")):
        return "fund_flow"
    if any(token in text_value for token in ("hkma", "adb", "censtatd", "guangdong", "stats")):
        return "market_metric"
    return "macro_signal" if not source else "news"


def products_for_subtypes(subtypes: set[str]) -> list[str]:
    return recommended_products_for_subtypes(subtypes)


def tier_for_score(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


class CuratedProspectBuilder:
    """Build frontend-ready prospect, evidence, signal, score, and market snapshot tables."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.run_id = datetime.now(timezone.utc).strftime("curated-%Y%m%dT%H%M%SZ")

    def build_all(self) -> dict[str, Any]:
        mapping_backfill = self.backfill_company_ids_from_evidence()
        prospects = self.build_prospects()
        evidence = self.build_evidence_items()
        signals = self.build_signals()
        scores = self.build_scores()
        market = self.build_market_snapshots()
        quality = self.build_quality_report()
        return {
            "run_id": self.run_id,
            "mapping_backfill": mapping_backfill,
            "prospects": prospects,
            "evidence": evidence,
            "signals": signals,
            "scores": scores,
            "market_snapshots": market,
            "quality": quality,
        }

    def build_prospects(self) -> dict[str, int]:
        rows = self.db.execute(
            text(
                """
                WITH ranked AS (
                  SELECT c.*,
                         ROW_NUMBER() OVER (PARTITION BY c.company_id ORDER BY c.updated_at DESC, c.id DESC) AS rn
                  FROM companies c
                ),
                latest AS (
                  SELECT * FROM ranked WHERE rn = 1
                ),
                activity AS (
                  SELECT company_id, MAX(event_time) AS last_activity_at
                  FROM (
                    SELECT company_id, event_time FROM trigger_signals
                    UNION ALL
                    SELECT company_id, event_time FROM client_one_view_timeline
                    UNION ALL
                    SELECT company_id, event_time FROM intelligence_records
                  ) x
                  WHERE company_id IS NOT NULL AND TRIM(company_id) <> ''
                  GROUP BY company_id
                )
                SELECT l.company_id, l.canonical_name, l.display_name, l.region,
                       COALESCE(l.industries_json->>0, NULL) AS industry,
                       l.segments_json, l.extra_json, l.updated_at, a.last_activity_at
                FROM latest l
                LEFT JOIN activity a ON a.company_id = l.company_id
                """
            )
        ).mappings().all()
        if not rows:
            rows = self.db.execute(
                text(
                    """
                    SELECT company_id,
                           company_id AS canonical_name,
                           company_id AS display_name,
                           NULL::text AS region,
                           NULL::text AS industry,
                           '[]'::jsonb AS segments_json,
                           '{}'::jsonb AS extra_json,
                           NULL::timestamptz AS updated_at,
                           MAX(event_time) AS last_activity_at
                    FROM (
                      SELECT company_id, event_time FROM trigger_signals
                      UNION ALL
                      SELECT company_id, event_time FROM client_one_view_timeline
                      UNION ALL
                      SELECT company_id, event_time FROM intelligence_records
                    ) x
                    WHERE company_id IS NOT NULL AND TRIM(company_id) <> ''
                    GROUP BY company_id
                    """
                )
            ).mappings().all()

        upserted = 0
        now = datetime.now(timezone.utc)
        for row in rows:
            company_id = row["company_id"]
            if not company_id:
                continue
            source_profile = {
                "segments": _json_field(row.get("segments_json"), []),
                "extra": _json_field(row.get("extra_json"), {}),
            }
            result = self.db.execute(
                text(
                    """
                    INSERT INTO prospects (
                      prospect_id, company_id, display_name, canonical_name, region, industry,
                      size_band, segments_json, source_profile_json, last_activity_at, created_at,
                      updated_at, run_id
                    )
                    VALUES (
                      :prospect_id, :company_id, :display_name, :canonical_name, :region, :industry,
                      :size_band, CAST(:segments AS jsonb), CAST(:source_profile AS jsonb),
                      :last_activity_at, :now, :now, :run_id
                    )
                    ON CONFLICT (prospect_id) DO UPDATE SET
                      display_name = EXCLUDED.display_name,
                      canonical_name = EXCLUDED.canonical_name,
                      region = EXCLUDED.region,
                      industry = EXCLUDED.industry,
                      segments_json = EXCLUDED.segments_json,
                      source_profile_json = EXCLUDED.source_profile_json,
                      last_activity_at = EXCLUDED.last_activity_at,
                      updated_at = EXCLUDED.updated_at,
                      run_id = EXCLUDED.run_id
                    """
                ),
                {
                    "prospect_id": company_id,
                    "company_id": company_id,
                    "display_name": row.get("display_name") or row.get("canonical_name") or company_id,
                    "canonical_name": row.get("canonical_name") or company_id,
                    "region": row.get("region"),
                    "industry": row.get("industry"),
                    "size_band": "unknown",
                    "segments": _json_dumps(source_profile["segments"]),
                    "source_profile": _json_dumps(source_profile),
                    "last_activity_at": row.get("last_activity_at") or row.get("updated_at"),
                    "now": now,
                    "run_id": self.run_id,
                },
            )
            upserted += max(0, int(result.rowcount or 0))
        return {"scanned": len(rows), "upserted": upserted}

    def build_evidence_items(self) -> dict[str, int]:
        rows = self.db.execute(
            text(
                """
                SELECT 'intelligence_records' AS source_table, id AS source_id, company_id,
                       source, dataset, record_type, event_time, title, summary, evidence_url AS url,
                       payload_json AS metadata_json
                FROM intelligence_records
                UNION ALL
                SELECT 'client_one_view_timeline' AS source_table, id AS source_id, company_id,
                       source, COALESCE(payload_json->>'dataset', event_type) AS dataset,
                       event_type AS record_type, event_time, headline AS title, detail AS summary,
                       evidence_url AS url, payload_json AS metadata_json
                FROM client_one_view_timeline
                UNION ALL
                SELECT 'parsed_documents' AS source_table, id AS source_id, company_id,
                       source, dataset, media_type AS record_type, parsed_at AS event_time,
                       COALESCE(title, source_record_key, dataset) AS title,
                       COALESCE(management_discussion_summary, summary, search_text) AS summary,
                       evidence_url AS url, metadata_json
                FROM parsed_documents
                UNION ALL
                SELECT 'trigger_signals' AS source_table, id AS source_id, company_id,
                       source, dataset, signal_type AS record_type, event_time,
                       COALESCE(indicator, signal_key) AS title, signal_text AS summary,
                       NULL::text AS url, extra_json AS metadata_json
                FROM trigger_signals
                """
            )
        ).mappings().all()
        inserted = 0
        skipped = 0
        for row in rows:
            title = _clean_text(row.get("title"))
            summary = _clean_text(row.get("summary"))
            url = _clean_text(row.get("url"))
            if not title or (not summary and not url and not row.get("event_time")):
                skipped += 1
                continue
            content_hash = stable_hash(
                {
                    "source_table": row["source_table"],
                    "source_id": row["source_id"],
                    "title": title,
                    "summary": summary,
                    "url": url,
                }
            )
            evidence_id = "ev_" + stable_hash({"source_table": row["source_table"], "source_id": row["source_id"], "hash": content_hash})[:24]
            evidence_type = infer_evidence_type(row.get("source"), row.get("dataset"), row.get("record_type"))
            result = self.db.execute(
                text(
                    """
                    INSERT INTO prospect_evidence_items (
                      evidence_id, prospect_id, company_id, source_table, source_id, evidence_type,
                      event_time, title, summary, url, source, dataset, metadata_json, content_hash, run_id
                    )
                    VALUES (
                      :evidence_id, :prospect_id, :company_id, :source_table, :source_id, :evidence_type,
                      :event_time, :title, :summary, :url, :source, :dataset,
                      CAST(:metadata AS jsonb), :content_hash, :run_id
                    )
                    ON CONFLICT (source_table, source_id, content_hash) DO NOTHING
                    """
                ),
                {
                    "evidence_id": evidence_id,
                    "prospect_id": row.get("company_id"),
                    "company_id": row.get("company_id"),
                    "source_table": row["source_table"],
                    "source_id": row["source_id"],
                    "evidence_type": evidence_type,
                    "event_time": row.get("event_time"),
                    "title": title[:500],
                    "summary": summary[:4000] if summary else None,
                    "url": url or None,
                    "source": row.get("source") or "unknown",
                    "dataset": row.get("dataset"),
                    "metadata": _json_dumps(_json_field(row.get("metadata_json"), {})),
                    "content_hash": content_hash,
                    "run_id": self.run_id,
                },
            )
            inserted += max(0, int(result.rowcount or 0))
        return {"scanned": len(rows), "inserted": inserted, "skipped_low_value": skipped}

    def build_signals(self) -> dict[str, int]:
        rows = self.db.execute(
            text(
                """
                SELECT ts.id, ts.company_id, ts.signal_type, ts.signal_level, ts.signal_score,
                       ts.event_time, ts.signal_text, ts.indicator, ts.value_text, ts.source, ts.dataset,
                       pei.evidence_id
                FROM trigger_signals ts
                LEFT JOIN prospect_evidence_items pei
                  ON pei.source_table = 'trigger_signals' AND pei.source_id = ts.id
                WHERE ts.signal_text IS NOT NULL AND TRIM(ts.signal_text) <> ''
                """
            )
        ).mappings().all()
        inserted = 0
        for row in rows:
            subtype = infer_signal_subtype(row.get("signal_type"), row.get("signal_text"), row.get("indicator"), row.get("dataset"))
            signal_id = "sig_" + stable_hash({"source": row.get("source"), "id": row["id"], "subtype": subtype})[:24]
            evidence_ids = [row["evidence_id"]] if row.get("evidence_id") else []
            result = self.db.execute(
                text(
                    """
                    INSERT INTO prospect_signals (
                      signal_id, prospect_id, company_id, signal_type, signal_subtype, signal_level,
                      signal_score, event_time, signal_text, evidence_ids_json, metadata_json, run_id
                    )
                    VALUES (
                      :signal_id, :prospect_id, :company_id, :signal_type, :signal_subtype, :signal_level,
                      :signal_score, :event_time, :signal_text, CAST(:evidence_ids AS jsonb),
                      CAST(:metadata AS jsonb), :run_id
                    )
                    ON CONFLICT (signal_id) DO UPDATE SET
                      signal_level = EXCLUDED.signal_level,
                      signal_score = EXCLUDED.signal_score,
                      evidence_ids_json = EXCLUDED.evidence_ids_json,
                      metadata_json = EXCLUDED.metadata_json,
                      run_id = EXCLUDED.run_id
                    """
                ),
                {
                    "signal_id": signal_id,
                    "prospect_id": row.get("company_id"),
                    "company_id": row.get("company_id"),
                    "signal_type": row.get("signal_type") or "market",
                    "signal_subtype": subtype,
                    "signal_level": row.get("signal_level"),
                    "signal_score": row.get("signal_score"),
                    "event_time": row.get("event_time"),
                    "signal_text": row.get("signal_text"),
                    "evidence_ids": _json_dumps(evidence_ids),
                    "metadata": _json_dumps({"source": row.get("source"), "dataset": row.get("dataset"), "raw_signal_id": row["id"]}),
                    "run_id": self.run_id,
                },
            )
            inserted += max(0, int(result.rowcount or 0))
        return {"scanned": len(rows), "upserted": inserted}

    def build_scores(self) -> dict[str, int]:
        rows = self.db.execute(
            text(
                """
                SELECT p.prospect_id, p.company_id,
                       COALESCE((
                         SELECT JSONB_OBJECT_AGG(signal_subtype, signal_count)
                         FROM (
                           SELECT signal_subtype, COUNT(*) AS signal_count
                           FROM prospect_signals
                           WHERE prospect_id = p.prospect_id
                             AND signal_subtype IS NOT NULL
                           GROUP BY signal_subtype
                         ) counts
                       ), '{}'::jsonb) AS signal_counts,
                       (
                         SELECT COUNT(*)
                         FROM prospect_evidence_items
                         WHERE prospect_id = p.prospect_id
                       ) AS evidence_count,
                       EXTRACT(DAY FROM (NOW() - (
                         SELECT MAX(event_time)
                         FROM (
                           SELECT event_time FROM prospect_signals WHERE prospect_id = p.prospect_id
                           UNION ALL
                           SELECT event_time FROM prospect_evidence_items WHERE prospect_id = p.prospect_id
                         ) activity
                       )))::int AS days_since_last_activity,
                       COALESCE((
                         SELECT JSONB_AGG(JSONB_BUILD_OBJECT(
                           'evidence_id', evidence_id,
                           'subtype', subtype,
                           'title', title
                         ) ORDER BY event_time DESC NULLS LAST, evidence_id)
                         FROM (
                           SELECT DISTINCT pei.evidence_id, ps.signal_subtype AS subtype, pei.title, pei.event_time
                           FROM prospect_signals ps
                           JOIN prospect_evidence_items pei
                             ON pei.prospect_id = ps.prospect_id
                            AND ps.evidence_ids_json ? pei.evidence_id
                           WHERE ps.prospect_id = p.prospect_id
                             AND ps.signal_subtype IS NOT NULL
                             AND pei.evidence_id IS NOT NULL
                           UNION
                           SELECT pei.evidence_id,
                                  CASE
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(fund|financ|loan|credit|bond|placing|募资|融资|贷款|发债)' THEN 'funding'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(cross-border|cross border|跨境)' THEN 'cross_border'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(trade|export|import|贸易|出口|进口)' THEN 'trade'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(expand|expansion|new project|investment|投资|扩张|新项目|开设)' THEN 'expansion'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(policy|regulat|budget|政府|政策|监管|财政)' THEN 'policy'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(holding|shareholding|northbound|southbound|增持|持股)' THEN 'market_attention'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(growth|gdp|increase|yoy|同比|增长|增速)' THEN 'growth'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(risk|warning|default|impair|违规|问询|风险|处罚)' THEN 'risk'
                                    WHEN LOWER(CONCAT_WS(' ', pei.title, pei.summary)) ~ '(hire|hiring|recruit|招聘|人才)' THEN 'hiring'
                                    ELSE NULL
                                  END AS subtype,
                                  pei.title,
                                  pei.event_time
                           FROM prospect_evidence_items pei
                           WHERE pei.prospect_id = p.prospect_id
                             AND pei.evidence_id IS NOT NULL
                             AND NOT EXISTS (
                               SELECT 1
                               FROM prospect_signals linked_ps
                               WHERE linked_ps.prospect_id = p.prospect_id
                                 AND linked_ps.evidence_ids_json ? pei.evidence_id
                             )
                         ) typed_evidence
                         WHERE subtype IS NOT NULL
                       ), '[]'::jsonb) AS evidence_refs
                FROM prospects p
                """
            )
        ).mappings().all()
        inputs: list[ProspectScoreInput] = []
        score_by_prospect: dict[str, float] = {}
        for row in rows:
            raw_counts = _json_field(row.get("signal_counts"), {})
            signal_counts = {str(key): int(value or 0) for key, value in raw_counts.items() if key and int(value or 0) > 0}
            raw_refs = _json_field(row.get("evidence_refs"), [])
            evidence_refs = [
                EvidenceRef(
                    evidence_id=str(item["evidence_id"]),
                    subtype=str(item.get("subtype") or "evidence"),
                    title=item.get("title"),
                )
                for item in raw_refs
                if isinstance(item, dict) and item.get("evidence_id")
            ]
            item = ProspectScoreInput(
                prospect_id=row["prospect_id"],
                signal_counts=signal_counts,
                evidence_count=int(row.get("evidence_count") or 0),
                evidence_refs=evidence_refs,
                days_since_last_activity=row.get("days_since_last_activity"),
            )
            inputs.append(item)
            score_by_prospect[item.prospect_id] = calculate_score(item)

        tiers = assign_percentile_tier(sorted(score_by_prospect.items(), key=lambda pair: pair[1], reverse=True))
        upserted = 0
        input_by_id = {item.prospect_id: item for item in inputs}
        for row in rows:
            prospect_id = row["prospect_id"]
            item = input_by_id[prospect_id]
            subtypes = set(item.signal_counts)
            products = recommended_products_for_subtypes(subtypes)
            reasons = build_score_reasons(item)
            result = self.db.execute(
                text(
                    """
                    INSERT INTO prospect_scores (
                      prospect_id, company_id, score, tier, reasons_json, recommended_products_json,
                      recommended_entry_angle, score_inputs_json, updated_at, run_id
                    )
                    VALUES (
                      :prospect_id, :company_id, :score, :tier, CAST(:reasons AS jsonb), CAST(:products AS jsonb),
                      :entry_angle, CAST(:score_inputs AS jsonb), :updated_at, :run_id
                    )
                    ON CONFLICT (prospect_id) DO UPDATE SET
                      score = EXCLUDED.score,
                      tier = EXCLUDED.tier,
                      reasons_json = EXCLUDED.reasons_json,
                      recommended_products_json = EXCLUDED.recommended_products_json,
                      recommended_entry_angle = EXCLUDED.recommended_entry_angle,
                      score_inputs_json = EXCLUDED.score_inputs_json,
                      updated_at = EXCLUDED.updated_at,
                      run_id = EXCLUDED.run_id
                    """
                ),
                {
                    "prospect_id": prospect_id,
                    "company_id": row.get("company_id"),
                    "score": score_by_prospect[prospect_id],
                    "tier": tiers[prospect_id],
                    "reasons": _json_dumps(reasons),
                    "products": _json_dumps(products),
                    "entry_angle": entry_angle_for_subtypes(subtypes, products),
                    "score_inputs": _json_dumps(
                        {
                            "signal_counts": item.signal_counts,
                            "evidence_count": item.evidence_count,
                            "evidence_refs": [ref.__dict__ for ref in item.evidence_refs[:10]],
                            "days_since_last_activity": item.days_since_last_activity,
                        }
                    ),
                    "updated_at": datetime.now(timezone.utc),
                    "run_id": self.run_id,
                },
            )
            upserted += max(0, int(result.rowcount or 0))
        return {"scanned": len(rows), "upserted": upserted}

    def backfill_company_ids_from_evidence(self) -> dict[str, int]:
        macro_exclusion_params = _macro_source_exclusion_params()
        company_mappable_ir = _company_mappable_source_predicate("ir")
        name_match = self.db.execute(
            text(
                f"""
                WITH company_tokens AS (
                  SELECT DISTINCT company_id,
                         token
                  FROM (
                    SELECT company_id,
                           LOWER(REGEXP_REPLACE(TRIM(canonical_name), '\\s+', ' ', 'g')) AS token
                    FROM companies
                    WHERE company_id IS NOT NULL AND TRIM(company_id) <> ''
                    UNION ALL
                    SELECT company_id,
                           LOWER(REGEXP_REPLACE(TRIM(COALESCE(display_name, '')), '\\s+', ' ', 'g')) AS token
                    FROM companies
                    WHERE company_id IS NOT NULL AND TRIM(company_id) <> ''
                  ) tokens
                  WHERE token <> ''
                ),
                record_tokens AS (
                  SELECT ir.id,
                         record_values.token
                  FROM intelligence_records ir
                  CROSS JOIN LATERAL (
                    VALUES
                      (LOWER(REGEXP_REPLACE(TRIM(COALESCE(ir.entity, '')), '\\s+', ' ', 'g'))),
                      (LOWER(REGEXP_REPLACE(TRIM(COALESCE(ir.title, '')), '\\s+', ' ', 'g')))
                  ) AS record_values(token)
                  WHERE (ir.company_id IS NULL OR TRIM(ir.company_id) = '')
                    AND record_values.token <> ''
                    AND {company_mappable_ir}
                ),
                candidates AS (
                  SELECT DISTINCT ON (rt.id) rt.id, c.company_id
                  FROM record_tokens rt
                  JOIN company_tokens c ON c.token = rt.token
                  ORDER BY rt.id, c.company_id
                )
                UPDATE intelligence_records ir
                SET company_id = candidates.company_id
                FROM candidates
                WHERE ir.id = candidates.id
                """
            ),
            {"rule": "name_match", **macro_exclusion_params},
        )
        payload_id = self.db.execute(
            text(
                f"""
                WITH payload_candidates AS (
                  SELECT ir.id,
                         COALESCE(
                           NULLIF(TRIM(ir.payload_json->>'company_id'), ''),
                           NULLIF(TRIM(ir.payload_json->>'stock_code'), ''),
                           NULLIF(TRIM(ir.payload_json->>'ticker'), ''),
                           NULLIF(TRIM(ir.payload_json->>'code'), ''),
                           NULLIF(TRIM(ir.payload_json->>'security_code'), '')
                         ) AS payload_company_id
                  FROM intelligence_records ir
                  WHERE (ir.company_id IS NULL OR TRIM(ir.company_id) = '')
                    AND ir.payload_json IS NOT NULL
                    AND {company_mappable_ir}
                ),
                candidates AS (
                  SELECT DISTINCT ON (pc.id) pc.id, c.company_id
                  FROM payload_candidates pc
                  JOIN companies c ON c.company_id = pc.payload_company_id
                  WHERE pc.payload_company_id IS NOT NULL
                  ORDER BY pc.id, c.company_id
                )
                UPDATE intelligence_records ir
                SET company_id = candidates.company_id
                FROM candidates
                WHERE ir.id = candidates.id
                """
            ),
            {"rule": "payload_id", **macro_exclusion_params},
        )
        eastmoney_code = self.db.execute(
            text(
                f"""
                WITH source_rows AS (
                  SELECT ir.id,
                         (
                           regexp_match(
                             CONCAT_WS(' ', ir.record_key, ir.entity, ir.title),
                             '(^|[^0-9])([0-9]{6})([^0-9]|$)'
                           )
                         )[2] AS six_digit_code
                  FROM intelligence_records ir
                  WHERE (ir.company_id IS NULL OR TRIM(ir.company_id) = '')
                    AND {company_mappable_ir}
                    AND (
                      LOWER(COALESCE(ir.source, '')) LIKE '%dongfang%'
                      OR LOWER(COALESCE(ir.dataset, '')) LIKE '%dongfang%'
                      OR LOWER(COALESCE(ir.source, '')) LIKE '%eastmoney%'
                      OR LOWER(COALESCE(ir.dataset, '')) LIKE '%eastmoney%'
                    )
                    AND CONCAT_WS(' ', ir.record_key, ir.entity, ir.title) ~ '(^|[^0-9])[0-9]{6}([^0-9]|$)'
                ),
                candidates AS (
                  SELECT DISTINCT ON (sr.id) sr.id, c.company_id
                  FROM source_rows sr
                  JOIN companies c ON c.company_id = sr.six_digit_code
                  WHERE sr.six_digit_code IS NOT NULL
                  ORDER BY sr.id, c.company_id
                )
                UPDATE intelligence_records ir
                SET company_id = candidates.company_id
                FROM candidates
                WHERE ir.id = candidates.id
                """
            ),
            {"rule": "eastmoney_code", **macro_exclusion_params},
        )
        counts = {
            "name_match_updated": max(0, int(name_match.rowcount or 0)),
            "payload_id_updated": max(0, int(payload_id.rowcount or 0)),
            "eastmoney_code_updated": max(0, int(eastmoney_code.rowcount or 0)),
        }
        counts["total_updated"] = sum(counts.values())
        return counts

    def build_market_snapshots(self) -> dict[str, int]:
        snapshot_date = datetime.now(timezone.utc)
        rows = self.db.execute(
            text(
                """
                SELECT COALESCE(p.region, 'Unknown') AS region,
                       COALESCE(p.industry, 'Unknown') AS industry,
                       COALESCE(p.size_band, 'unknown') AS size_band,
                       psig.signal_subtype AS signal_type,
                       COUNT(DISTINCT p.prospect_id) AS lead_count,
                       COUNT(psig.id) AS signal_count,
                       AVG(score.score) AS avg_score,
                       ARRAY_AGG(DISTINCT p.prospect_id) FILTER (WHERE score.score IS NOT NULL) AS prospect_ids
                FROM prospects p
                LEFT JOIN prospect_signals psig ON psig.prospect_id = p.prospect_id
                LEFT JOIN prospect_scores score ON score.prospect_id = p.prospect_id
                GROUP BY p.region, p.industry, p.size_band, psig.signal_subtype
                """
            )
        ).mappings().all()
        inserted = 0
        for row in rows:
            prospect_ids = [item for item in (row.get("prospect_ids") or []) if item][:10]
            result = self.db.execute(
                text(
                    """
                    INSERT INTO market_opportunity_snapshots (
                      snapshot_date, region, industry, size_band, signal_type, lead_count, signal_count,
                      avg_score, top_prospect_ids_json, trend_summary, run_id
                    )
                    VALUES (
                      :snapshot_date, :region, :industry, :size_band, :signal_type, :lead_count, :signal_count,
                      :avg_score, CAST(:top_prospect_ids AS jsonb), :trend_summary, :run_id
                    )
                    ON CONFLICT (snapshot_date, region, industry, size_band, signal_type) DO NOTHING
                    """
                ),
                {
                    "snapshot_date": snapshot_date,
                    "region": row.get("region"),
                    "industry": row.get("industry"),
                    "size_band": row.get("size_band") or "unknown",
                    "signal_type": row.get("signal_type") or "unclassified",
                    "lead_count": int(row.get("lead_count") or 0),
                    "signal_count": int(row.get("signal_count") or 0),
                    "avg_score": float(row["avg_score"]) if row.get("avg_score") is not None else None,
                    "top_prospect_ids": _json_dumps(prospect_ids),
                    "trend_summary": f"{row.get('signal_type') or 'unclassified'} signals in {row.get('industry') or 'Unknown'} / {row.get('region') or 'Unknown'}",
                    "run_id": self.run_id,
                },
            )
            inserted += max(0, int(result.rowcount or 0))
        return {"scanned": len(rows), "inserted": inserted}

    def build_quality_report(self) -> dict[str, Any]:
        report = {
            "table_counts": self._table_counts(),
            "company_mapping": self._mapping_quality(),
            "signal_subtype_distribution": self._distribution("prospect_signals", "signal_subtype"),
            "score_tier_distribution": self._distribution("prospect_scores", "tier"),
        }
        self.db.execute(
            text(
                """
                INSERT INTO data_quality_reports (run_id, report_json)
                VALUES (:run_id, CAST(:report AS jsonb))
                ON CONFLICT (run_id) DO UPDATE SET report_json = EXCLUDED.report_json
                """
            ),
            {"run_id": self.run_id, "report": _json_dumps(report)},
        )
        return report

    def _entry_angle(self, subtypes: set[str], products: list[str]) -> str:
        if "funding" in subtypes:
            return "Lead with financing needs evidenced by recent funding or credit-related signals."
        if "cross_border" in subtypes or "trade" in subtypes:
            return "Lead with cross-border settlement and trade finance support."
        if "expansion" in subtypes:
            return "Lead with working capital and cash management for expansion plans."
        if products:
            return f"Lead with {products[0].replace('_', ' ')} based on recent evidence."
        return "Start with a needs-discovery conversation grounded in recent market evidence."

    def _table_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for table in (
            "intelligence_records",
            "trigger_signals",
            "client_one_view_timeline",
            "companies",
            "parsed_documents",
            "prospects",
            "prospect_evidence_items",
            "prospect_signals",
            "prospect_scores",
        ):
            try:
                out[table] = int(self.db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
            except Exception:
                out[table] = -1
        return out

    def _mapping_quality(self) -> dict[str, Any]:
        excluded_params = _macro_source_exclusion_params()
        company_mappable_predicate = _company_mappable_source_predicate("intelligence_records")
        mapped_predicate = "company_id IS NOT NULL AND TRIM(company_id) <> ''"
        total = int(self.db.execute(text("SELECT COUNT(*) FROM intelligence_records")).scalar_one())
        mapped = int(self.db.execute(text(f"SELECT COUNT(*) FROM intelligence_records WHERE {mapped_predicate}")).scalar_one())
        company_mappable_total = int(
            self.db.execute(
                text(f"SELECT COUNT(*) FROM intelligence_records WHERE {company_mappable_predicate}"),
                excluded_params,
            ).scalar_one()
        )
        company_mappable_mapped = int(
            self.db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM intelligence_records
                    WHERE {mapped_predicate}
                      AND {company_mappable_predicate}
                    """
                ),
                excluded_params,
            ).scalar_one()
        )
        return {
            "intelligence_records_total": total,
            "intelligence_records_mapped": mapped,
            "raw_coverage": mapping_coverage(mapped=mapped, total=total),
            "company_mappable_total": company_mappable_total,
            "company_mappable_mapped": company_mappable_mapped,
            "coverage": mapping_coverage(mapped=company_mappable_mapped, total=company_mappable_total),
            "target_coverage": 0.6,
            "excluded_macro_sources": list(EXCLUDED_MACRO_SOURCE_TOKENS),
        }

    def _distribution(self, table: str, column: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            text(f"SELECT {column} AS name, COUNT(*) AS count FROM {table} GROUP BY {column} ORDER BY count DESC")
        ).mappings().all()
        return [dict(row) for row in rows]
