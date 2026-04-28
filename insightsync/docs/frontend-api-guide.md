# Frontend API Guide

This document maps the frontend request list to the backend state in this repository.

The goal is to answer three questions clearly:

1. What can the frontend connect to right now
2. What is not available yet but can be added later
3. What is not part of the current backend scope

## Status Legend

- `Available now`: implemented and usable today
- `Planned later`: not implemented yet, but fits the current product direction
- `Not in current roadmap`: not currently implemented and not part of the near-term backend scope

## Global Rules

### JSON shape

Frontend-facing endpoints should return page-ready JSON instead of raw database rows.

The current backend already does this for implemented endpoints, but some future endpoints still need business-layer aggregation before they should be exposed.

### Stable IDs

Current implemented endpoints provide stable numeric IDs for database-backed resources:

- `id` on signals
- `id` on timeline events
- `chunk_id` and `document_id` on RAG citations
- `retrieval_run_id` on RAG query responses

The frontend request document asks for business IDs such as:

- `prospectId`
- `signalId`
- `insightId`
- `entityId`

Current status:

- `signalId`: available now through `id` in `/api/signals`
- `insightId`: not exposed yet as a dedicated field in frontend-ready APIs
- `prospectId`: not available now because the backend does not yet have a proper prospect domain model
- `entityId`: not available now; current APIs expose `entity` as a string label such as `HKG`

### Time format

All new frontend-facing APIs should use ISO-8601 timestamps.

Current status:

- implemented endpoints already serialize datetime-compatible values through FastAPI/Pydantic
- older source data still contains date-like strings from upstream records, so some payload values remain source-shaped

### Optional field rules

Current convention:

- missing scalar value: `null`
- missing list value: `[]`
- missing object value: `null` or `{}` depending on the endpoint

Recommended frontend handling:

- render optional text fields conditionally
- treat missing arrays as empty arrays

### Pagination rules

Current implemented pagination:

- `/api/signals`: `items`, `limit`, `offset`
- `/api/timeline`: `items`, `limit`, `offset`

Requested future pagination:

- `items`
- `total`
- `page`
- `pageSize`

Current status:

- partially implemented now
- should be standardized later across all list endpoints

### Error format

Requested frontend format:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Prospect not found"
  }
}
```

Current status:

- not implemented as a custom global error contract
- FastAPI default validation and HTTP errors are still in use
- `Planned later`

## API Matrix From Frontend Request

### `GET /api/dashboard/summary`

Status:

- `Planned later`

Frontend need:

- top four homepage cards
- `leadPool`
- `highPriority`
- `crossBorder`
- `financingSignals`
- `lastUpdated`

Current backend substitute:

- `GET /api/dashboard/overview`

Why not available yet:

- the backend does not yet have a stable prospect model or ranking model
- `leadPool` and `highPriority` require prospect-level scoring logic that is not implemented yet
- `crossBorder` and `financingSignals` also need explicit counting rules at company level or signal level

Can it exist later:

- yes

Recommended future response shape:

```json
{
  "leadPool": 1247,
  "highPriority": 86,
  "crossBorder": 234,
  "financingSignals": 45,
  "lastUpdated": "2026-04-20T10:32:00Z"
}
```

### `GET /api/dashboard/market-overview`

Status:

- `Planned later`

Frontend need:

- homepage chart section
- `industryBreakdown`
- `regionBreakdown`
- `companySizeBreakdown`

Current backend substitute:

- `GET /api/dashboard/overview` exposes source and signal-type breakdowns only

Why not available yet:

- industry and region breakdown can be derived from current data
- company size breakdown is not available because there is no company financial profile model yet

Can it exist later:

- yes

Notes:

- `industryBreakdown`: feasible later from normalized data
- `regionBreakdown`: feasible later from normalized data
- `companySizeBreakdown`: feasible only after a company/prospect profile layer exists

### `GET /api/dashboard/priority-prospects`

Status:

- `Planned later`

Frontend need:

- homepage priority prospect list

Why not available yet:

- there is no implemented `prospect_scores` generation pipeline
- there is no stable prospect entity API yet

Can it exist later:

- yes

### `GET /api/dashboard/trigger-signals`

Status:

- `Planned later`

Current backend substitute:

- `GET /api/signals`

Why not available yet:

- current `/api/signals` returns general signal records, not a homepage-tailored compact panel response

Can it exist later:

- yes

Frontend can use now:

- call `/api/signals?limit=5&entity=HKG`
- map each item into homepage cards manually

### `GET /api/companies`

Status:

- `Available now`

Purpose:

- company-centric list view built from the latest company snapshot plus linked activity counts

Query params:

- `limit`
- `offset`
- `q`
- `region`
- `segment`
- `industry`

Current response shape:

```json
{
  "items": [
    {
      "source": "company_directory",
      "company_id": "hkg-alpha-fintech",
      "canonical_name": "Alpha Fintech",
      "display_name": "Alpha Fintech Holdings",
      "country": "China",
      "region": "Hong Kong",
      "city": "Hong Kong",
      "segments": ["fintech", "sme"],
      "industries": ["Payments"],
      "website_url": "https://alpha.example.com",
      "linkedin_url": "https://linkedin.com/company/alpha",
      "facebook_url": null,
      "x_url": null,
      "instagram_url": null,
      "wikipedia_url": null,
      "profile_summary": "Latest summary",
      "description": "Latest description",
      "extra": { "seed_source": "manual_seed_v2" },
      "updated_at": "2026-04-20T09:00:00Z",
      "signal_count": 2,
      "timeline_event_count": 1,
      "generated_insight_count": 1,
      "last_signal_at": "2026-04-22T10:00:00Z",
      "last_event_at": "2026-04-22T10:00:00Z",
      "last_insight_at": "2026-04-22T11:00:00Z",
      "activity_at": "2026-04-22T10:00:00Z"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

Frontend note:

- This endpoint is the first company-centric substitute for the future prospects list.
- It does not yet provide banker ranking, tiering, or revenue features.
- It is suitable now for a company explorer or candidate list page.

### `GET /api/companies/{company_id}`

Status:

- `Available now`

Purpose:

- company-centric detail view with recent signals, timeline, and generated insights

Current response shape:

```json
{
  "company": {
    "source": "company_directory",
    "company_id": "hkg-alpha-fintech",
    "canonical_name": "Alpha Fintech",
    "display_name": "Alpha Fintech Holdings",
    "country": "China",
    "region": "Hong Kong",
    "city": "Hong Kong",
    "segments": ["fintech", "sme"],
    "industries": ["Payments"],
    "website_url": "https://alpha.example.com",
    "linkedin_url": "https://linkedin.com/company/alpha",
    "facebook_url": null,
    "x_url": null,
    "instagram_url": null,
    "wikipedia_url": null,
    "profile_summary": "Latest summary",
    "description": "Latest description",
    "extra": { "seed_source": "manual_seed_v2" },
    "updated_at": "2026-04-20T09:00:00Z"
  },
  "stats": {
    "signal_count": 2,
    "timeline_event_count": 1,
    "generated_insight_count": 1,
    "last_signal_at": "2026-04-22T10:00:00Z",
    "last_event_at": "2026-04-22T10:00:00Z",
    "last_insight_at": "2026-04-22T11:00:00Z",
    "signal_type_distribution": [
      { "name": "cross_border", "count": 1 },
      { "name": "growth", "count": 1 }
    ]
  },
  "recent_signals": [],
  "recent_timeline": [],
  "recent_insights": []
}
```

Frontend note:

- This endpoint is the first company-centric substitute for the future prospect detail page.
- It is useful now for a company drill-down page and evidence panel.
- It is still not the full final `prospects/:id` contract.

### `GET /api/prospects`

Status:

- `Planned later`

Frontend need:

- prospect list page with search, filters, and pagination

Why not available yet:

- no prospect domain model
- no search layer for named companies
- no ranking, tiering, revenue normalization, or company card assembly yet

Can it exist later:

- yes

### `GET /api/prospects/:prospectId`

Status:

- `Planned later`

Frontend need:

- prospect detail base profile

Why not available yet:

- no prospect record identity
- no company profile aggregation service

Can it exist later:

- yes

### `GET /api/prospects/:prospectId/signals`

Status:

- `Planned later`

Why not available yet:

- current signal data is not consistently linked to a stable `prospectId`

Can it exist later:

- yes

### `GET /api/prospects/:prospectId/timeline`

Status:

- `Planned later`

Why not available yet:

- timeline exists today, but mostly at the `entity` level, not at the fully linked prospect level

Can it exist later:

- yes

### `GET /api/prospects/:prospectId/evidence`

Status:

- `Planned later`

Why not available yet:

- evidence exists today inside RAG citations and source records, but not yet as a dedicated prospect evidence endpoint

Can it exist later:

- yes

### `GET /api/prospects/:prospectId/insights`

Status:

- `Planned later`

Current backend substitute:

- `POST /api/insights/generate`

Why not available yet:

- insight generation exists, but not yet as a prospect-scoped historical list endpoint

Can it exist later:

- yes

### `GET /api/metadata/filters`

Status:

- `Planned later`

Why not available yet:

- filter metadata is derivable from data but not exposed yet as a dedicated endpoint

Can it exist later:

- yes

## APIs Available Now

These are the endpoints the frontend can connect to immediately.

### `GET /healthz`

Status:

- `Available now`

Purpose:

- backend online check

Example response:

```json
{
  "status": "ok",
  "app_env": "local"
}
```

### `GET /api/dashboard/overview`

Status:

- `Available now`

Purpose:

- general dashboard overview

What it is good for:

- backend status card
- ingestion status
- basic KPI cards
- source distribution chart
- signal-type distribution chart

What it is not:

- not the final `dashboard/summary`
- not the final `market-overview`

Example response:

```json
{
  "ingestion_runs": 5,
  "intelligence_records": 177,
  "trigger_signals": 1334,
  "timeline_events": 183,
  "generated_insights": 0,
  "latest_run_status": "success",
  "latest_run_id": "run-20260407T011831Z",
  "signal_type_distribution": [
    { "name": "market", "count": 1168 },
    { "name": "cross_border", "count": 162 }
  ],
  "source_distribution": [
    { "name": "hkma", "count": 100 },
    { "name": "guangdong_stats", "count": 71 }
  ]
}
```

### `GET /api/signals`

Status:

- `Available now`

Purpose:

- paginated trigger signal list

Query params:

- `limit`
- `offset`
- `entity`
- `signal_type`
- `source`
- `date_from`
- `date_to`

Current response shape:

```json
{
  "items": [
    {
      "id": 1220,
      "source": "hkma",
      "dataset": "press_releases_en",
      "signal_key": "press_releases_en|2026-03-31|title|Residential Mortgage Survey Results for February 2026",
      "signal_type": "market",
      "company_id": null,
      "entity": "HKG",
      "event_time": "2026-03-31T00:00:00",
      "indicator": "title",
      "value_num": 2026.0,
      "value_text": "Residential Mortgage Survey Results for February 2026",
      "unit": null,
      "signal_text": "title: Residential Mortgage Survey Results for February 2026",
      "signal_score": null,
      "signal_level": null,
      "evidence_refs": ["hkma", "press_releases_en"],
      "extra": { "lang": "en" }
    }
  ],
  "limit": 20,
  "offset": 0
}
```

Frontend note:

- This endpoint is usable now for a signal list page.
- It is also usable as a temporary data source for the dashboard trigger signals panel.
- Current `id` can be treated as `signalId` for UI state and list rendering.

### `GET /api/timeline`

Status:

- `Available now`

Purpose:

- paginated event timeline

Query params:

- `limit`
- `offset`
- `company_id`
- `entity`
- `event_type`
- `source`
- `date_from`
- `date_to`

Current response shape:

```json
{
  "items": [
    {
      "id": 81,
      "source": "hkma",
      "company_id": null,
      "entity": "HKG",
      "event_time": "2026-04-02T00:00:00",
      "event_type": "event",
      "headline": "Exchange Fund Bills Tender Results",
      "detail": "Exchange Fund Bills Tender Results",
      "evidence_url": null,
      "payload": {
        "source": "hkma",
        "dataset": "press_releases_en",
        "record_key": "press_releases_en|Exchange Fund Bills Tender Results|idx-0"
      }
    }
  ],
  "limit": 20,
  "offset": 0
}
```

Frontend note:

- This endpoint is usable now for a timeline page.
- It can also serve as a temporary detail evidence timeline for entity-level experiences.
- It is not yet a proper `prospectId` timeline API.

### `GET /api/rag/index/status`

Status:

- `Available now`

Purpose:

- admin or debug status page

Current response shape:

```json
{
  "document_count": 1694,
  "chunk_count": 1694,
  "embedded_chunk_count": 1694,
  "embedding_model": "text-embedding-3-small",
  "last_indexed_at": "2026-04-16 19:17:44.04974+00"
}
```

### `POST /api/rag/query`

Status:

- `Available now`

Purpose:

- Copilot / RAG question answering

Request body:

```json
{
  "question": "What cross-border signals are recent for Hong Kong?",
  "filters": {
    "entity": "HKG",
    "signal_type": "cross_border"
  },
  "top_k": 3,
  "include_chunks": false
}
```

Current response shape:

```json
{
  "answer": "Retrieved 3 evidence item(s) relevant to: What cross-border signals are recent for Hong Kong?",
  "status": "ok",
  "retrieval_run_id": 4,
  "citations": [
    {
      "chunk_id": 1588,
      "document_id": 1588,
      "score": 0.125,
      "source": "hkma",
      "dataset": "press_releases_en",
      "record_key": "press_releases_en|Inaugural Guangdong-Hong Kong-Macao-Shenzhen Joint Financial Regulatory Meeting|idx-16",
      "signal_key": null,
      "evidence_url": null,
      "text": null
    }
  ],
  "structured_insight": {
    "status": "ok",
    "insight_type": "explanation",
    "title": "Evidence-grounded summary",
    "summary": "Retrieved 3 evidence item(s) relevant to: What cross-border signals are recent for Hong Kong?"
  }
}
```

Frontend note:

- This is the current endpoint for the Copilot chat panel.
- The frontend should not call OpenAI directly.
- The frontend should call this endpoint and render `answer`, `status`, and `citations`.

### `POST /api/insights/generate`

Status:

- `Available now`

Purpose:

- generate a structured insight and persist it if valid citations exist

Request body:

```json
{
  "question": "Summarize recent cross-border signals for HKG",
  "insight_type": "action",
  "filters": {
    "entity": "HKG"
  }
}
```

Current response shape:

```json
{
  "status": "ok",
  "insight": {
    "status": "ok",
    "insight_type": "action",
    "title": "Evidence-grounded summary",
    "summary": "Retrieved 6 evidence item(s) relevant to: Summarize recent cross-border signals for HKG",
    "recommended_action": "Review the cited evidence before taking client action."
  },
  "citations": [
    {
      "chunk_id": 1578,
      "document_id": 1578,
      "score": 0.3333333333333333,
      "source": "hkma",
      "dataset": "press_releases_en",
      "record_key": "press_releases_en|International Reserves and Foreign Currency Liquidity|idx-6",
      "signal_key": null,
      "evidence_url": null,
      "text": "Title : International Reserves and Foreign Currency Liquidity ..."
    }
  ]
}
```

Frontend note:

- This is the current closest match to future AI insight blocks.
- It is useful now for a generated recommendation panel.
- It is not yet the same as `GET /api/prospects/:id/insights`.

## What Frontend Can Connect To Today

### Homepage

Frontend can connect now:

- `GET /api/dashboard/overview`
- `GET /api/signals?limit=5...`

Frontend cannot connect yet:

- final top-card summary API
- final market overview API
- final priority prospect list API

### Signals Page

Frontend can connect now:

- `GET /api/signals`

### Timeline Page

Frontend can connect now:

- `GET /api/timeline`

### Company Explorer / Detail

Frontend can connect now:

- `GET /api/companies`
- `GET /api/companies/{company_id}`

### Copilot / Ask Page

Frontend can connect now:

- `POST /api/rag/query`
- `POST /api/insights/generate`

### Prospect List / Prospect Detail

Frontend cannot connect yet:

- all `prospects` endpoints are still future work
- frontend can use the `companies` endpoints as the current company-centric substitute

## Filter Metadata

Requested endpoint:

- `GET /api/metadata/filters`

Status:

- `Planned later`

For now, frontend can hardcode or derive temporary options from current API results.

Current feasible temporary values:

- `entity`: currently `HKG` is the most reliable option
- `signal_type`: `market`, `cross_border`, `financing`, `risk`
- `source`: `hkma`, `guangdong_stats`, `adb_kidb`, `kpmg`

## Empty Data Rules

Use these rules in frontend integration:

- list fields: expect `[]`
- optional scalar fields: expect `null`
- optional object fields: expect `null` or `{}` depending on endpoint
- RAG insufficient evidence: expect

```json
{
  "status": "insufficient_evidence",
  "answer": "...",
  "citations": []
}
```

## Recommended Next Backend Additions

If the frontend wants to match the current UI more closely, the next backend additions should be:

1. `GET /api/dashboard/summary`
2. `GET /api/dashboard/market-overview`
3. `GET /api/dashboard/priority-prospects`
4. `GET /api/dashboard/trigger-signals`
5. `GET /api/metadata/filters`
6. full `prospects` resource family

## Development Checklist

Before frontend integration:

```text
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m insightsync.backend.workflows.sync_from_sqlite --full
docker compose exec api python -m insightsync.backend.workflows.build_rag_index --full
```

Then open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```
