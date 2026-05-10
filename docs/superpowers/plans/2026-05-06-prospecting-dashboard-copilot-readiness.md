# Prospecting Dashboard and Copilot Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make InsightSync business-trustworthy first, then demo-ready for Market Opportunity Overview, Priority Prospect List, Prospect Intelligence, Trigger Signals, and evidence-gated GLM Copilot.

**Architecture:** Keep dashboard metrics and ranking deterministic in the curated data layer. Use GLM only for citation-gated explanations, entry angles, briefs, and Copilot answers. Upgrade Copilot retrieval to hybrid SQL scoping plus vector RAG, with backend citation validation as the trust boundary.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy Core/ORM sessions, PostgreSQL + pgvector, Alembic, pytest, FastAPI TestClient, GLM through OpenAI-compatible chat provider.

---

## Scope Check

This plan covers three tightly coupled readiness areas:

- Business-quality curated data.
- Evidence-gated GLM/Copilot retrieval.
- Frontend-ready dashboard/prospect APIs.

They are kept in one plan because the demo acceptance criteria depend on the business-quality layer. Do not implement demo-only API polish before the business-trustworthy checklist passes.

## File Structure

Modify these existing files:

- `insightsync/backend/services/curated_builder.py`
  - Owns prospect evidence, signal subtype inference, score/tier calculation, product fit, entry angle, market snapshots, and data quality report.
- `insightsync/backend/services/copilot_service.py`
  - Owns context-aware retrieval, GLM call, citation validation, and Copilot persistence.
- `insightsync/backend/services/rag_document_builder.py`
  - Already builds curated-first RAG documents; use it only if retrieval metadata needs adjustment.
- `insightsync/backend/repositories/read_repository.py`
  - Owns dashboard read models and aggregate queries.
- `insightsync/backend/api/dashboard.py`
  - Exposes dashboard summary, market overview, priority prospects, and trigger signals.
- `insightsync/backend/api/prospects.py`
  - Exposes prospect detail, evidence, signals, timeline, and insights.
- `insightsync/backend/schemas/dashboard.py`
  - Add response fields for cited reasons, drill-down metadata, and quality warnings.
- `insightsync/backend/schemas/prospects.py`
  - Add score reason and insight/citation fields needed by frontend.
- `insightsync/backend/schemas/copilot.py`
  - Keep response names stable. Do not add fields unless a task below names the exact field.
- `insightsync/backend/db/tables.py`
  - No schema change is planned in this file for this implementation.
- `insightsync/backend/db/migrations/versions/0007_prospect_readiness_quality.py`
  - Do not create this migration unless execution discovers that an existing JSON column is missing in the checked-out schema.

Create these files:

- `insightsync/backend/services/prospect_scoring.py`
  - Pure scoring rules, tier assignment, product mapping, score reason generation.
- `insightsync/backend/services/company_mapping_quality.py`
  - Mapping coverage helpers and optional deterministic backfill from source payload/entity fields.
- `insightsync/backend/services/copilot_retrieval.py`
  - Hybrid SQL and vector retrieval, context-specific retrieval plans.
- `insightsync/backend/tests/test_prospect_scoring.py`
  - Unit tests for score distribution, tiers, reasons, and product fit.
- `insightsync/backend/tests/test_company_mapping_quality.py`
  - Unit tests for mapping coverage and deterministic matching helpers.
- `insightsync/backend/tests/test_copilot_retrieval.py`
  - Unit tests for prospect, market, signal, global retrieval planning and citation constraints.
- `insightsync/backend/tests/test_dashboard_readiness_api.py`
  - API/read-model tests for dashboard acceptance data.
- `insightsync/backend/tests/test_copilot_glm_gate.py`
  - Tests for GLM JSON, invalid citations, and fallback behavior.
- `insightsync/docs/prospecting-readiness-acceptance.md`
  - Operational checklist and commands for validating B then A.

## Task 1: Extract Deterministic Scoring Rules

**Files:**
- Create: `insightsync/backend/services/prospect_scoring.py`
- Modify: `insightsync/backend/services/curated_builder.py`
- Test: `insightsync/backend/tests/test_prospect_scoring.py`

- [ ] **Step 1: Write failing tests for tier distribution and cited reasons**

Create `insightsync/backend/tests/test_prospect_scoring.py`:

```python
from insightsync.backend.services.prospect_scoring import (
    EvidenceRef,
    ProspectScoreInput,
    assign_percentile_tier,
    build_score_reasons,
    calculate_score,
    recommended_products_for_subtypes,
)


def test_calculate_score_prioritizes_cross_border_funding_and_recency() -> None:
    item = ProspectScoreInput(
        prospect_id="p1",
        signal_counts={"cross_border": 2, "funding": 1, "growth": 5},
        evidence_count=8,
        evidence_refs=[
            EvidenceRef(evidence_id="ev_cross", subtype="cross_border", title="Cross-border expansion"),
            EvidenceRef(evidence_id="ev_fund", subtype="funding", title="Bond issuance"),
        ],
        days_since_last_activity=10,
    )

    score = calculate_score(item)

    assert 65 <= score <= 100


def test_assign_percentile_tier_creates_business_separation() -> None:
    ordered = [
        ("p1", 99.0),
        ("p2", 90.0),
        ("p3", 80.0),
        ("p4", 70.0),
        ("p5", 60.0),
        ("p6", 50.0),
        ("p7", 40.0),
        ("p8", 30.0),
        ("p9", 20.0),
        ("p10", 10.0),
    ]

    tiers = assign_percentile_tier(ordered)

    assert tiers["p1"] == "A"
    assert tiers["p2"] == "B"
    assert tiers["p5"] == "C"
    assert tiers["p10"] == "D"


def test_build_score_reasons_requires_evidence_ids() -> None:
    item = ProspectScoreInput(
        prospect_id="p1",
        signal_counts={"cross_border": 1, "funding": 1},
        evidence_count=2,
        evidence_refs=[
            EvidenceRef(evidence_id="ev1", subtype="cross_border", title="New overseas sales office"),
            EvidenceRef(evidence_id="ev2", subtype="funding", title="New loan facility"),
        ],
        days_since_last_activity=3,
    )

    reasons = build_score_reasons(item)

    assert reasons
    assert all(reason["evidence_ids"] for reason in reasons)
    assert {"trade_finance", "cash_management"} & set(recommended_products_for_subtypes({"cross_border"}))
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest insightsync/backend/tests/test_prospect_scoring.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'insightsync.backend.services.prospect_scoring'`.

- [ ] **Step 3: Implement pure scoring module**

Create `insightsync/backend/services/prospect_scoring.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from math import ceil


IMPORTANT_SUBTYPES = {"growth", "expansion", "funding", "cross_border", "market_attention"}


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    subtype: str
    title: str | None = None


@dataclass(frozen=True)
class ProspectScoreInput:
    prospect_id: str
    signal_counts: dict[str, int]
    evidence_count: int
    evidence_refs: list[EvidenceRef]
    days_since_last_activity: int | None


def calculate_score(item: ProspectScoreInput) -> float:
    subtype_weights = {
        "funding": 22.0,
        "cross_border": 20.0,
        "expansion": 18.0,
        "growth": 10.0,
        "market_attention": 8.0,
        "policy": 8.0,
        "trade": 12.0,
        "risk": -10.0,
        "hiring": 5.0,
    }
    score = 10.0
    for subtype, count in item.signal_counts.items():
        score += min(count, 5) * subtype_weights.get(subtype, 4.0)
    score += min(item.evidence_count, 10) * 2.0
    if item.days_since_last_activity is not None:
        if item.days_since_last_activity <= 30:
            score += 15.0
        elif item.days_since_last_activity <= 90:
            score += 8.0
        elif item.days_since_last_activity > 365:
            score -= 15.0
    if not item.evidence_refs:
        score = min(score, 39.0)
    return round(max(0.0, min(100.0, score)), 2)


def assign_percentile_tier(ordered_scores: list[tuple[str, float]]) -> dict[str, str]:
    if not ordered_scores:
        return {}
    count = len(ordered_scores)
    a_cutoff = max(1, ceil(count * 0.15))
    b_cutoff = max(a_cutoff + 1, ceil(count * 0.45))
    c_cutoff = max(b_cutoff + 1, ceil(count * 0.80))
    tiers: dict[str, str] = {}
    for idx, (prospect_id, score) in enumerate(ordered_scores):
        if score < 40:
            tiers[prospect_id] = "D"
        elif idx < a_cutoff:
            tiers[prospect_id] = "A"
        elif idx < b_cutoff:
            tiers[prospect_id] = "B"
        elif idx < c_cutoff:
            tiers[prospect_id] = "C"
        else:
            tiers[prospect_id] = "D"
    return tiers


def build_score_reasons(item: ProspectScoreInput) -> list[dict[str, object]]:
    refs_by_subtype: dict[str, list[EvidenceRef]] = {}
    for ref in item.evidence_refs:
        refs_by_subtype.setdefault(ref.subtype, []).append(ref)
    reasons: list[dict[str, object]] = []
    for subtype in ("funding", "cross_border", "expansion", "growth", "market_attention", "policy", "trade"):
        if item.signal_counts.get(subtype, 0) <= 0:
            continue
        refs = refs_by_subtype.get(subtype) or item.evidence_refs[:1]
        if not refs:
            continue
        reasons.append(
            {
                "reason": f"{item.signal_counts[subtype]} {subtype.replace('_', ' ')} signal(s)",
                "signal_subtype": subtype,
                "weight": item.signal_counts[subtype],
                "evidence_ids": [ref.evidence_id for ref in refs[:3]],
            }
        )
    return reasons


def recommended_products_for_subtypes(subtypes: set[str]) -> list[str]:
    mapping = {
        "cross_border": ["trade_finance", "cash_management", "cross_border_services"],
        "trade": ["trade_finance", "fx_services"],
        "funding": ["corporate_lending", "capital_markets", "working_capital"],
        "expansion": ["cash_management", "working_capital", "treasury_services"],
        "policy": ["treasury_services", "cross_border_services", "advisory"],
        "growth": ["cash_management", "working_capital"],
        "market_attention": ["capital_markets", "rm_review"],
        "risk": ["risk_review"],
    }
    products: list[str] = []
    for subtype in sorted(subtypes):
        for product in mapping.get(subtype, []):
            if product not in products:
                products.append(product)
    return products[:5]


def entry_angle_for_subtypes(subtypes: set[str], products: list[str]) -> str:
    if "cross_border" in subtypes:
        return "Lead with cross-border cash management and trade finance support backed by recent evidence."
    if "funding" in subtypes:
        return "Lead with financing and working-capital needs evidenced by recent funding signals."
    if "expansion" in subtypes:
        return "Lead with cash management and working capital for expansion plans."
    if "policy" in subtypes:
        return "Lead with a policy-aware treasury and cross-border services review."
    if products:
        return f"Lead with {products[0].replace('_', ' ')} based on cited recent evidence."
    return "Start with a needs-discovery conversation grounded in recent cited evidence."
```

- [ ] **Step 4: Wire scoring module into curated builder**

Modify `insightsync/backend/services/curated_builder.py`:

```python
from insightsync.backend.services.prospect_scoring import (
    EvidenceRef,
    ProspectScoreInput,
    assign_percentile_tier,
    build_score_reasons,
    calculate_score,
    entry_angle_for_subtypes,
    recommended_products_for_subtypes,
)
```

Replace the body of `build_scores()` with a two-pass implementation:

```python
    def build_scores(self) -> dict[str, int]:
        rows = self.db.execute(
            text(
                """
                SELECT p.prospect_id, p.company_id,
                       COUNT(DISTINCT ps.id) AS signal_count,
                       COUNT(DISTINCT pei.id) AS evidence_count,
                       EXTRACT(DAY FROM (NOW() - MAX(GREATEST(
                         COALESCE(ps.event_time, 'epoch'::timestamptz),
                         COALESCE(pei.event_time, 'epoch'::timestamptz)
                       ))))::int AS days_since_last_activity,
                       ARRAY_REMOVE(ARRAY_AGG(DISTINCT ps.signal_subtype), NULL) AS subtypes,
                       COALESCE(
                         JSONB_AGG(DISTINCT JSONB_BUILD_OBJECT(
                           'evidence_id', pei.evidence_id,
                           'subtype', COALESCE(ps.signal_subtype, 'evidence'),
                           'title', pei.title
                         )) FILTER (WHERE pei.evidence_id IS NOT NULL),
                         '[]'::jsonb
                       ) AS evidence_refs
                FROM prospects p
                LEFT JOIN prospect_signals ps ON ps.prospect_id = p.prospect_id
                LEFT JOIN prospect_evidence_items pei ON pei.prospect_id = p.prospect_id
                GROUP BY p.prospect_id, p.company_id
                """
            )
        ).mappings().all()
        inputs: list[ProspectScoreInput] = []
        score_by_prospect: dict[str, float] = {}
        for row in rows:
            subtypes = {str(item) for item in (row.get("subtypes") or []) if item}
            evidence_refs = [
                EvidenceRef(
                    evidence_id=str(item["evidence_id"]),
                    subtype=str(item.get("subtype") or "evidence"),
                    title=item.get("title"),
                )
                for item in _json_field(row.get("evidence_refs"), [])
                if item.get("evidence_id")
            ]
            signal_counts = {subtype: 1 for subtype in subtypes}
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
```

- [ ] **Step 5: Run scoring tests**

Run:

```bash
pytest insightsync/backend/tests/test_prospect_scoring.py insightsync/backend/tests/test_curated_builder.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add insightsync/backend/services/prospect_scoring.py insightsync/backend/services/curated_builder.py insightsync/backend/tests/test_prospect_scoring.py insightsync/backend/tests/test_curated_builder.py
git commit -m "feat: add evidence-backed prospect scoring"
```

Expected: commit succeeds. If the working directory is not a git repository, skip the commit and record that in the execution notes.

## Task 2: Improve Company Mapping Coverage Reporting and Backfill

**Files:**
- Create: `insightsync/backend/services/company_mapping_quality.py`
- Modify: `insightsync/backend/services/curated_builder.py`
- Test: `insightsync/backend/tests/test_company_mapping_quality.py`

- [ ] **Step 1: Write failing tests for deterministic company ID extraction**

Create `insightsync/backend/tests/test_company_mapping_quality.py`:

```python
from insightsync.backend.services.company_mapping_quality import (
    canonical_company_token,
    extract_company_id_from_payload,
    mapping_coverage,
)


def test_extract_company_id_from_payload_prefers_stock_code() -> None:
    payload = {"stock_code": " 002129 ", "name": "TCL Zhonghuan"}

    assert extract_company_id_from_payload(payload) == "002129"


def test_canonical_company_token_normalizes_names() -> None:
    assert canonical_company_token(" TCL中环股份有限公司 ") == "tcl中环股份有限公司"


def test_mapping_coverage_handles_empty_total() -> None:
    assert mapping_coverage(mapped=0, total=0) == 0.0
    assert mapping_coverage(mapped=60, total=100) == 0.6
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest insightsync/backend/tests/test_company_mapping_quality.py -q
```

Expected: FAIL with module not found.

- [ ] **Step 3: Implement mapping helper**

Create `insightsync/backend/services/company_mapping_quality.py`:

```python
from __future__ import annotations

from typing import Any


COMPANY_ID_KEYS = ("company_id", "stock_code", "ticker", "code", "security_code")


def extract_company_id_from_payload(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    for key in COMPANY_ID_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return None


def canonical_company_token(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def mapping_coverage(*, mapped: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return mapped / total
```

- [ ] **Step 4: Add a safe backfill method to curated builder**

Modify `insightsync/backend/services/curated_builder.py` imports:

```python
from insightsync.backend.services.company_mapping_quality import mapping_coverage
```

Modify `_mapping_quality()` to use `mapping_coverage`:

```python
        return {
            "intelligence_records_total": total,
            "intelligence_records_mapped": mapped,
            "coverage": mapping_coverage(mapped=mapped, total=total),
            "target_coverage": 0.6,
        }
```

Add this method to `CuratedProspectBuilder`:

```python
    def backfill_company_ids_from_evidence(self) -> dict[str, int]:
        exact_name_result = self.db.execute(
            text(
                """
                UPDATE intelligence_records ir
                SET company_id = candidates.company_id
                FROM (
                  SELECT ir2.id, c.company_id
                  FROM intelligence_records ir2
                  JOIN companies c
                    ON LOWER(COALESCE(ir2.entity, '')) = LOWER(COALESCE(c.canonical_name, ''))
                    OR LOWER(COALESCE(ir2.title, '')) LIKE '%' || LOWER(COALESCE(c.canonical_name, '')) || '%'
                  WHERE (ir2.company_id IS NULL OR TRIM(ir2.company_id) = '')
                    AND c.company_id IS NOT NULL
                    AND TRIM(c.company_id) <> ''
                ) candidates
                WHERE ir.id = candidates.id
                  AND (ir.company_id IS NULL OR TRIM(ir.company_id) = '')
                """
            )
        )
        payload_code_result = self.db.execute(
            text(
                """
                UPDATE intelligence_records ir
                SET company_id = payload.company_id
                FROM (
                  SELECT id,
                         COALESCE(
                           NULLIF(payload_json->>'company_id', ''),
                           NULLIF(payload_json->>'stock_code', ''),
                           NULLIF(payload_json->>'ticker', ''),
                           NULLIF(payload_json->>'code', ''),
                           NULLIF(payload_json->>'security_code', '')
                         ) AS company_id
                  FROM intelligence_records
                  WHERE company_id IS NULL OR TRIM(company_id) = ''
                ) payload
                WHERE ir.id = payload.id
                  AND payload.company_id IS NOT NULL
                  AND TRIM(payload.company_id) <> ''
                  AND EXISTS (
                    SELECT 1 FROM companies c WHERE c.company_id = payload.company_id
                  )
                """
            )
        )
        dongfang_result = self.db.execute(
            text(
                """
                UPDATE intelligence_records ir
                SET company_id = regexp_replace(COALESCE(ir.record_key, ir.entity, ir.title), '.*?([0-9]{6}).*', '\\1')
                WHERE (ir.company_id IS NULL OR TRIM(ir.company_id) = '')
                  AND ir.source IN ('dongfang', 'eastmoney')
                  AND COALESCE(ir.record_key, ir.entity, ir.title, '') ~ '[0-9]{6}'
                  AND EXISTS (
                    SELECT 1
                    FROM companies c
                    WHERE c.company_id = regexp_replace(COALESCE(ir.record_key, ir.entity, ir.title), '.*?([0-9]{6}).*', '\\1')
                  )
                """
            )
        )
        updated = sum(max(0, int(result.rowcount or 0)) for result in (exact_name_result, payload_code_result, dongfang_result))
        return {
            "updated": updated,
            "exact_name_updated": max(0, int(exact_name_result.rowcount or 0)),
            "payload_code_updated": max(0, int(payload_code_result.rowcount or 0)),
            "dongfang_code_updated": max(0, int(dongfang_result.rowcount or 0)),
        }
```

Modify `build_all()` to run the backfill before `build_prospects()`:

```python
        mapping_backfill = self.backfill_company_ids_from_evidence()
        prospects = self.build_prospects()
```

Add `"mapping_backfill": mapping_backfill` to the returned dict.

- [ ] **Step 5: Run mapping tests**

Run:

```bash
pytest insightsync/backend/tests/test_company_mapping_quality.py -q
```

Expected: PASS.

- [ ] **Step 6: Rebuild curated layer and inspect mapping**

Run:

```bash
docker compose exec api python -m insightsync.backend.workflows.build_curated_prospects
```

Expected: output contains `quality.company_mapping.coverage >= 0.6`. If coverage is below `0.6`, this task is not complete. Add another deterministic source-specific rule to `backfill_company_ids_from_evidence()`, rerun this step, and repeat until the target is met.

- [ ] **Step 7: Commit**

Run:

```bash
git add insightsync/backend/services/company_mapping_quality.py insightsync/backend/services/curated_builder.py insightsync/backend/tests/test_company_mapping_quality.py
git commit -m "feat: improve company mapping quality checks"
```

Expected: commit succeeds or non-git workspace is noted.

## Task 3: Add Dashboard Read Models for Cited Priority Reasons and Market Drilldown

**Files:**
- Modify: `insightsync/backend/repositories/read_repository.py`
- Modify: `insightsync/backend/api/dashboard.py`
- Modify: `insightsync/backend/schemas/dashboard.py`
- Test: `insightsync/backend/tests/test_dashboard_readiness_api.py`

- [ ] **Step 1: Write API shape tests**

Create `insightsync/backend/tests/test_dashboard_readiness_api.py`:

```python
from fastapi.testclient import TestClient

from insightsync.backend.main import app


def test_priority_prospects_response_has_reason_and_citation_fields() -> None:
    client = TestClient(app)

    response = client.get("/api/dashboard/priority-prospects?limit=1")

    assert response.status_code in {200, 500}
    if response.status_code == 200 and response.json()["items"]:
        item = response.json()["items"][0]
        assert "scoreReasons" in item
        assert "evidenceIds" in item


def test_market_overview_response_has_drilldown_keys() -> None:
    client = TestClient(app)

    response = client.get("/api/dashboard/market-overview")

    assert response.status_code in {200, 500}
    if response.status_code == 200:
        payload = response.json()
        assert "industryBreakdown" in payload
        first_group = payload["industryBreakdown"][:1]
        if first_group:
            assert "drilldown" in first_group[0]
```

- [ ] **Step 2: Run tests to verify they fail on missing fields**

Run:

```bash
pytest insightsync/backend/tests/test_dashboard_readiness_api.py -q
```

Expected: FAIL because `scoreReasons`, `evidenceIds`, or `drilldown` are not in response models.

- [ ] **Step 3: Extend dashboard schemas**

Modify `insightsync/backend/schemas/dashboard.py`:

```python
class EvidenceCitationItem(BaseModel):
    evidenceId: str
    title: str | None = None
    source: str | None = None
    eventTime: str | None = None


class ScoreReasonItem(BaseModel):
    reason: str
    signalSubtype: str | None = None
    evidenceIds: list[str]


class ChartDrilldown(BaseModel):
    prospectIds: list[str] = []
    evidenceIds: list[str] = []


class ChartItem(BaseModel):
    key: str
    label: str
    value: float | int
    drilldown: ChartDrilldown | None = None
```

Extend `DashboardPriorityProspectOut`:

```python
    scoreReasons: list[ScoreReasonItem] = []
    evidenceIds: list[str] = []
```

- [ ] **Step 4: Add repository methods**

Modify `ReadRepository.priority_prospects()` to select `reasons_json` and `score_inputs_json`, then hydrate fields:

```python
                SELECT p.prospect_id, p.display_name, p.industry, p.region, s.score, s.tier,
                       s.recommended_products_json, s.recommended_entry_angle,
                       s.reasons_json, s.score_inputs_json
```

Return:

```python
            {
                **dict(row),
                "recommended_products": self._json_field(row.get("recommended_products_json"), []),
                "score_reasons": self._json_field(row.get("reasons_json"), []),
                "score_inputs": self._json_field(row.get("score_inputs_json"), {}),
            }
```

Modify `ReadRepository.chart_breakdown()` to return drilldown:

```python
                SELECT COALESCE({column}, 'Unknown') AS key,
                       COALESCE({column}, 'Unknown') AS label,
                       COUNT(*) AS value,
                       JSONB_BUILD_OBJECT(
                         'prospectIds', COALESCE(JSONB_AGG(prospect_id) FILTER (WHERE prospect_id IS NOT NULL), '[]'::jsonb),
                         'evidenceIds', '[]'::jsonb
                       ) AS drilldown
```

Add `_json_field(row.get("drilldown"), {})` in the returned items.

- [ ] **Step 5: Map fields in dashboard API**

Modify `insightsync/backend/api/dashboard.py` in `priority_prospects()`:

```python
                scoreReasons=[
                    {
                        "reason": reason.get("reason", ""),
                        "signalSubtype": reason.get("signal_subtype"),
                        "evidenceIds": reason.get("evidence_ids", []),
                    }
                    for reason in row.get("score_reasons", [])
                ],
                evidenceIds=[
                    ref.get("evidence_id")
                    for ref in row.get("score_inputs", {}).get("evidence_refs", [])
                    if ref.get("evidence_id")
                ],
```

- [ ] **Step 6: Run dashboard tests**

Run:

```bash
pytest insightsync/backend/tests/test_dashboard_readiness_api.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add insightsync/backend/repositories/read_repository.py insightsync/backend/api/dashboard.py insightsync/backend/schemas/dashboard.py insightsync/backend/tests/test_dashboard_readiness_api.py
git commit -m "feat: expose cited dashboard readiness data"
```

Expected: commit succeeds or non-git workspace is noted.

## Task 4: Add Hybrid Copilot Retrieval

**Files:**
- Create: `insightsync/backend/services/copilot_retrieval.py`
- Modify: `insightsync/backend/services/embedding_service.py`
- Modify: `insightsync/backend/services/copilot_service.py`
- Test: `insightsync/backend/tests/test_copilot_retrieval.py`

- [ ] **Step 1: Write failing tests for retrieval plan construction**

Create `insightsync/backend/tests/test_copilot_retrieval.py`:

```python
from insightsync.backend.services.copilot_retrieval import RetrievalRequest, build_retrieval_plan


def test_prospect_context_retrieves_structured_and_vector_sources() -> None:
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="What makes this prospect actionable?",
            context="prospect",
            filters={"prospect_id": "002129"},
            top_k=5,
        )
    )

    assert "prospect_evidence_items" in plan.sql_sources
    assert "prospect_signals" in plan.sql_sources
    assert plan.use_vector is True
    assert plan.required_filters["prospect_id"] == "002129"


def test_market_context_includes_market_snapshots_and_policy_evidence() -> None:
    plan = build_retrieval_plan(
        RetrievalRequest(
            message="Which GBA policy signals create opportunities?",
            context="market",
            filters={"region": "Hong Kong"},
            top_k=8,
        )
    )

    assert "market_opportunity_snapshots" in plan.sql_sources
    assert "prospect_evidence_items" in plan.sql_sources
    assert plan.use_vector is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest insightsync/backend/tests/test_copilot_retrieval.py -q
```

Expected: FAIL with module not found.

- [ ] **Step 3: Implement retrieval plan module**

Create `insightsync/backend/services/copilot_retrieval.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalRequest:
    message: str
    context: str
    filters: dict[str, Any]
    top_k: int


@dataclass(frozen=True)
class RetrievalPlan:
    context: str
    sql_sources: list[str]
    required_filters: dict[str, Any] = field(default_factory=dict)
    use_vector: bool = True
    top_k: int = 5


def build_retrieval_plan(request: RetrievalRequest) -> RetrievalPlan:
    context = request.context or "global"
    filters = dict(request.filters or {})
    if context == "prospect":
        prospect_id = filters.get("prospect_id")
        return RetrievalPlan(
            context=context,
            sql_sources=["prospect_evidence_items", "prospect_signals", "prospect_scores"],
            required_filters={"prospect_id": prospect_id} if prospect_id else {},
            use_vector=True,
            top_k=request.top_k,
        )
    if context == "market":
        return RetrievalPlan(
            context=context,
            sql_sources=["market_opportunity_snapshots", "prospect_evidence_items"],
            required_filters={k: v for k, v in filters.items() if k in {"region", "industry", "date_from", "date_to"}},
            use_vector=True,
            top_k=request.top_k,
        )
    if context == "signal":
        return RetrievalPlan(
            context=context,
            sql_sources=["prospect_signals", "prospect_evidence_items"],
            required_filters={k: v for k, v in filters.items() if k in {"signal_id", "prospect_id"}},
            use_vector=True,
            top_k=request.top_k,
        )
    return RetrievalPlan(
        context="global",
        sql_sources=["prospect_evidence_items"],
        required_filters={k: v for k, v in filters.items() if k in {"region", "industry", "source", "date_from", "date_to"}},
        use_vector=True,
        top_k=request.top_k,
    )
```

- [ ] **Step 4: Refactor CopilotService to use RetrievalPlan**

Modify `insightsync/backend/services/copilot_service.py` imports:

```python
from insightsync.backend.ai.providers.openai_client import OpenAIProvider
from insightsync.backend.services.embedding_service import vector_literal
from insightsync.backend.services.copilot_retrieval import RetrievalRequest, build_retrieval_plan
```

At the top of `retrieve_evidence()` add:

```python
        plan = build_retrieval_plan(RetrievalRequest(message=message, context=context, filters=filters, top_k=top_k))
```

Use `plan.required_filters` instead of direct `filters` for context-specific constraints:

```python
        prospect_id = plan.required_filters.get("prospect_id") or filters.get("prospect_id")
```

Keep the existing SQL retrieval as the first implementation, and add a call to `_retrieve_vector_evidence()` after SQL rows:

```python
        sql_evidence = [...]
        if plan.use_vector:
            vector_evidence = self._retrieve_vector_evidence(message=message, filters=filters, top_k=top_k)
            return self._dedupe_evidence(sql_evidence + vector_evidence)[:top_k]
        return sql_evidence[:top_k]
```

Add helper methods with real pgvector similarity:

```python
    def _retrieve_vector_evidence(self, *, message: str, filters: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        query_embedding = OpenAIProvider(self.settings).embed_texts([message])[0]
        rows = self.db.execute(
            text(
                """
                SELECT pei.evidence_id, pei.title, pei.summary, pei.source, pei.dataset, pei.event_time,
                       pei.url, pei.prospect_id, pei.evidence_type,
                       1 - (re.embedding <=> CAST(:query_embedding AS vector)) AS score
                FROM rag_documents rd
                JOIN rag_chunks rc ON rc.document_id = rd.id
                JOIN rag_embeddings re ON re.chunk_id = rc.id
                JOIN prospect_evidence_items pei
                  ON rd.source_table = 'prospect_evidence_items'
                 AND rd.source_id = pei.id
                WHERE re.embedding_model = :embedding_model
                ORDER BY re.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
                """
            ),
            {
                "query_embedding": vector_literal(query_embedding),
                "embedding_model": self.settings.openai_embedding_model,
                "limit": top_k,
            },
        ).mappings().all()
        return [self._evidence_row_to_dict(row) for row in rows]

    def _dedupe_evidence(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in items:
            evidence_id = item.get("evidence_id")
            if not evidence_id or evidence_id in seen:
                continue
            seen.add(evidence_id)
            out.append(item)
        return out

    def _evidence_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "evidence_id": row["evidence_id"],
            "title": row["title"],
            "text": row.get("summary") or row.get("title"),
            "summary": row.get("summary"),
            "source": row.get("source"),
            "dataset": row.get("dataset"),
            "event_time": row.get("event_time"),
            "url": row.get("url"),
            "prospect_id": row.get("prospect_id"),
            "evidence_type": row.get("evidence_type"),
            "score": float(row.get("score") or 0),
        }
```

- [ ] **Step 5: Run retrieval tests**

Run:

```bash
pytest insightsync/backend/tests/test_copilot_retrieval.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add insightsync/backend/services/copilot_retrieval.py insightsync/backend/services/copilot_service.py insightsync/backend/tests/test_copilot_retrieval.py
git commit -m "feat: add hybrid copilot retrieval plan"
```

Expected: commit succeeds or non-git workspace is noted.

## Task 5: Enforce GLM Citation Gate and Audit Behavior

**Files:**
- Modify: `insightsync/backend/services/copilot_service.py`
- Modify: `insightsync/backend/ai/providers/openai_client.py`
- Test: `insightsync/backend/tests/test_copilot_glm_gate.py`

- [ ] **Step 1: Write tests for invalid citations and insufficient evidence**

Create `insightsync/backend/tests/test_copilot_glm_gate.py`:

```python
from insightsync.backend.services.copilot_service import CopilotService


def test_validate_citations_rejects_ids_not_retrieved() -> None:
    service = object.__new__(CopilotService)
    evidence = [{"evidence_id": "ev_allowed", "title": "Allowed", "summary": "Allowed summary"}]
    output = {"citations": [{"evidence_id": "ev_fake"}]}

    citations = CopilotService._validate_citations(service, output, evidence)

    assert citations == []


def test_validate_citations_keeps_retrieved_ids() -> None:
    service = object.__new__(CopilotService)
    evidence = [{"evidence_id": "ev_allowed", "title": "Allowed", "summary": "Allowed summary", "source": "hkgov"}]
    output = {"citations": [{"evidence_id": "ev_allowed"}]}

    citations = CopilotService._validate_citations(service, output, evidence)

    assert citations[0]["evidence_id"] == "ev_allowed"
    assert citations[0]["source"] == "hkgov"
```

- [ ] **Step 2: Run tests**

Run:

```bash
pytest insightsync/backend/tests/test_copilot_glm_gate.py -q
```

Expected: PASS if existing validation is correct; otherwise FAIL and fix validation.

- [ ] **Step 3: Make GLM JSON parse failure controlled**

Modify `OpenAIProvider.generate_structured_json()` in `insightsync/backend/ai/providers/openai_client.py` so JSON parse failure returns:

```python
{
    "status": "error",
    "error_code": "LLM_JSON_PARSE_ERROR",
    "answer": "",
    "citations": [],
    "requires_human_review": True,
}
```

The provider must not raise raw JSON exceptions to the API layer for normal malformed model output.

- [ ] **Step 4: Ensure Copilot treats provider errors as insufficient evidence**

Modify `CopilotService.chat()` after provider output:

```python
        if output.get("status") == "error":
            citations = []
            status = "insufficient_evidence"
            answer = "The model response could not be validated against retrieved evidence."
            output = {
                "status": "insufficient_evidence",
                "error_code": output.get("error_code"),
                "requires_human_review": True,
            }
        else:
            citations = self._validate_citations(output, evidence)
            status = "ok" if citations else "insufficient_evidence"
```

- [ ] **Step 5: Run Copilot gate tests**

Run:

```bash
pytest insightsync/backend/tests/test_copilot_glm_gate.py insightsync/backend/tests/test_openai_provider.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add insightsync/backend/services/copilot_service.py insightsync/backend/ai/providers/openai_client.py insightsync/backend/tests/test_copilot_glm_gate.py insightsync/backend/tests/test_openai_provider.py
git commit -m "feat: enforce copilot citation gate"
```

Expected: commit succeeds or non-git workspace is noted.

## Task 6: Add Operational Acceptance Report

**Files:**
- Create: `insightsync/docs/prospecting-readiness-acceptance.md`
- Modify: `insightsync/backend/workflows/build_curated_prospects.py`
- Test: manual Docker commands.

- [ ] **Step 1: Add acceptance doc**

Create `insightsync/docs/prospecting-readiness-acceptance.md`:

```markdown
# Prospecting Readiness Acceptance

Run these checks in order. Business-trustworthy checks must pass before demo-ready checks.

## Business-Trustworthy

```bash
docker compose exec api python -m insightsync.backend.workflows.build_curated_prospects
docker compose exec api python - <<'PY'
from sqlalchemy import text
from insightsync.backend.db.session import SessionLocal
db = SessionLocal()
quality = db.execute(text("select report_json from data_quality_reports order by created_at desc limit 1")).scalar_one()
print(quality)
assert quality["company_mapping"]["coverage"] >= 0.6
tiers = {row[0]: row[1] for row in db.execute(text("select tier, count(*) from prospect_scores group by tier"))}
assert len(tiers) >= 3
top = db.execute(text("select reasons_json from prospect_scores order by score desc limit 20")).all()
assert all(row[0] for row in top)
db.close()
PY
```

## Demo-Ready

```bash
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/summary
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/market-overview
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/priority-prospects
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/trigger-signals
docker compose exec api curl -sS -X POST http://127.0.0.1:8000/api/copilot/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Which prospects show cross-border opportunity?","context":"global","filters":{},"topK":5}'
```
```

- [ ] **Step 2: Ensure build workflow prints quality report**

Inspect `insightsync/backend/workflows/build_curated_prospects.py`. It should already print the builder summary. If not, set it to print:

```python
print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
```

- [ ] **Step 3: Run backend test suite**

Run:

```bash
pytest insightsync/backend/tests -q
```

Expected: PASS.

- [ ] **Step 4: Run acceptance commands**

Run:

```bash
docker compose exec api python -m insightsync.backend.workflows.build_curated_prospects
docker compose exec api python -m insightsync.backend.workflows.build_rag_index --full
```

Expected:

- Company mapping coverage is at least `0.6`.
- Score tier distribution has at least three populated tiers.
- RAG remains curated-first.

- [ ] **Step 5: Commit**

Run:

```bash
git add insightsync/docs/prospecting-readiness-acceptance.md insightsync/backend/workflows/build_curated_prospects.py
git commit -m "docs: add prospecting readiness acceptance checks"
```

Expected: commit succeeds or non-git workspace is noted.

## Final Verification Checklist

- [ ] `pytest insightsync/backend/tests -q` passes.
- [ ] `docker compose exec api python -m insightsync.backend.workflows.build_curated_prospects` passes.
- [ ] Latest `data_quality_reports.company_mapping.coverage >= 0.6`.
- [ ] `prospect_scores` has at least three non-empty tiers.
- [ ] Top 20 `prospect_scores.reasons_json` entries include evidence IDs.
- [ ] `GET /api/dashboard/market-overview` returns chart items with drilldown.
- [ ] `GET /api/dashboard/priority-prospects` returns cited score reasons.
- [ ] `POST /api/copilot/chat` with evidence returns citations.
- [ ] `POST /api/copilot/chat` with no evidence returns `insufficient_evidence`.
- [ ] With `ENABLE_LLM_GENERATION=true`, GLM output without valid citations is rejected.
