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

Current status:

- implemented company, prospect, and dashboard endpoints already return frontend-friendly business payloads
- older low-level endpoints such as `/api/signals` and `/api/timeline` still look closer to source-shaped records

### Stable IDs

Current implemented endpoints provide stable IDs for database-backed or derived resources:

- `id` on signals
- `id` on timeline events
- `chunk_id` and `document_id` on RAG citations
- `retrieval_run_id` on RAG query responses
- `prospect_id` on `/api/prospects*` and dashboard prospect blocks

The frontend request document asks for business IDs such as:

- `prospectId`
- `signalId`
- `insightId`
- `entityId`

Current status:

- `signalId`: available now through `id` in `/api/signals` and `signal_id` in dashboard trigger cards
- `insightId`: not exposed yet as a dedicated field in frontend-ready APIs
- `prospectId`: available now as `prospect:{company_id}`
- `entityId`: not available now as a separate normalized business object ID; current APIs still mainly expose company IDs and string entity labels such as `HKG`

### Time format

All new frontend-facing APIs should use ISO-8601 timestamps.

Current status:

- implemented endpoints serialize datetime-compatible values through FastAPI/Pydantic
- older source data still contains date-like strings from upstream records, so some low-level payload values remain source-shaped

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
- `/api/prospects`: `items`, `limit`, `offset`
- `/api/prospects/{prospect_id}/signals`: `items`, `limit`, `offset`
- `/api/prospects/{prospect_id}/timeline`: `items`, `limit`, `offset`

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

- `Available now`

Purpose:

- homepage summary cards derived from the current prospect layer

Current response shape:

```json
{
  "lead_pool": 1247,
  "high_priority": 86,
  "cross_border": 234,
  "financing_signals": 45,
  "last_updated": "2026-05-06T10:32:00Z"
}
```

Current logic:

- `lead_pool`: count of current prospects
- `high_priority`: prospects whose `priority_level` is `high`
- `cross_border`: prospects whose `focus_tags` include `cross_border`
- `financing_signals`: prospects whose `focus_tags` include financing-oriented tags such as `financing`, `market`, `growth`, or `expansion`

Frontend note:

- backend field names are currently `snake_case`
- if the UI expects `camelCase`, the frontend adapter should map them explicitly

### `GET /api/dashboard/market-overview`

Status:

- `Available now`

Purpose:

- homepage chart section
- `industry_breakdown`
- `region_breakdown`
- `company_size_breakdown`

Current response shape:

```json
{
  "industry_breakdown": [
    { "name": "Payments", "count": 8 }
  ],
  "region_breakdown": [
    { "name": "Hong Kong", "count": 12 }
  ],
  "company_size_breakdown": []
}
```

Current logic:

- `industry_breakdown`: aggregated from current prospect/company industries
- `region_breakdown`: aggregated from current prospect/company regions
- `company_size_breakdown`: intentionally empty today because there is no reliable size model yet

Frontend note:

- `company_size_breakdown` being `[]` is expected, not an error
- backend does not fabricate size buckets without real company profile data

### `GET /api/dashboard/priority-prospects`

Status:

- `Available now`

Purpose:

- homepage priority prospect list

Current response shape:

```json
{
  "items": [
    {
      "prospect_id": "prospect:hkg-alpha-fintech",
      "company_id": "hkg-alpha-fintech",
      "display_name": "Alpha Fintech Holdings",
      "priority_level": "high",
      "priority_score": 82,
      "opportunity_score": 74,
      "risk_score": 21,
      "region": "Hong Kong",
      "industries": ["Payments"],
      "focus_tags": ["growth", "cross_border"],
      "why_prioritized": ["Recent expansion signals", "Cross-border activity"],
      "recommended_next_step": "Review recent expansion and treasury needs."
    }
  ]
}
```

Current logic:

- list is derived from the current prospect layer
- top items are sorted by prospect priority
- payload is intentionally compact for homepage use

### `GET /api/dashboard/trigger-signals`

Status:

- `Available now`

Purpose:

- homepage trigger-signal cards

Current response shape:

```json
{
  "items": [
    {
      "signal_id": 11,
      "company_id": "hkg-alpha-fintech",
      "prospect_id": "prospect:hkg-alpha-fintech",
      "signal_type": "growth",
      "source": "hk_gov_news",
      "title": "Alpha Fintech expands into UAE",
      "event_time": "2026-05-05T08:00:00Z",
      "focus_tags": ["growth", "cross_border"]
    }
  ]
}
```

Current logic:

- cards are pulled from recent signals
- when a signal is linked to a company, the API also derives the linked `prospect_id`
- `focus_tags` are backfilled from the linked prospect for lightweight UI context

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

- this endpoint is the company explorer and base company list
- it is not the same thing as the business-facing prospect list

### `GET /api/companies/{company_id}`

Status:

- `Available now`

Purpose:

- company-centric detail view with recent signals, timeline, and generated insights

Frontend note:

- this is the fact-layer company detail
- it is useful for evidence drill-down and raw company context
- it is not the same thing as the banker-facing prospect detail contract

### `GET /api/prospects`

Status:

- `Available now`

Frontend need:

- prospect list page with search, filters, and pagination

Current scope:

- business-facing list derived from `company latest-state`
- includes `priority_level`, `priority_score`, `opportunity_score`, `risk_score`
- includes `score_breakdown` so the frontend can explain where the scores came from
- includes `recommended_next_step` and `recommended_product_themes`
- supports search and basic filters aligned to company fields

Current limitation:

- no dedicated persisted prospect table yet
- no RM ownership model yet
- no revenue normalization or banker-assignment logic yet

### `GET /api/prospects/{prospect_id}`

Status:

- `Available now`

Frontend need:

- prospect detail base profile

Current scope:

- returns a business-facing prospect object plus linked company evidence
- detail is derived from the existing company-centric evidence layer

Current limitation:

- prospect identity is still derived from `company_id`
- no separate persisted prospect lifecycle yet

### `GET /api/prospects/{prospect_id}/signals`

Status:

- `Available now`

Current scope:

- returns recent signals using the company-linked prospect identifier

### `GET /api/prospects/{prospect_id}/timeline`

Status:

- `Available now`

Current scope:

- returns company-linked timeline events through the prospect identifier

### `GET /api/prospects/{prospect_id}/evidence`

Status:

- `Available now`

Current scope:

- returns parsed-document evidence bundle for the linked company
- includes coverage flags, evidence summary, parsed documents, metrics, risks, and business events

Current limitation:

- does not yet include curated banker notes or human review state

### `GET /api/prospects/{prospect_id}/brief`

Status:

- `Available now`

Current scope:

- returns a banker-facing summary block for quick briefing
- derived from the current prospect and evidence state

### `POST /api/prospects/{prospect_id}/question`

Status:

- `Available now`

Current scope:

- answers a prospect-scoped question through evidence-grounded retrieval
- can optionally return chunk text when `include_chunks=true`

Current limitation:

- response quality still depends on current retrieval coverage and prompt quality

### `GET /api/prospects/{prospect_id}/copilot`

Status:

- `Available now`

Current scope:

- returns a prospect-centered copilot workspace payload
- intended to give the frontend a single entry payload for ask/brief/evidence context

### `GET /api/prospects/{prospect_id}/insights`

Status:

- `Planned later`

Current backend substitute:

- `POST /api/insights/generate`
- `POST /api/prospects/{prospect_id}/question`

Why not available yet:

- insight generation exists, but not yet as a dedicated prospect-scoped historical list endpoint

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

### `GET /api/dashboard/overview`

Status:

- `Available now`

Purpose:

- operational dashboard overview

What it is good for:

- backend status card
- ingestion status
- source distribution chart
- signal-type distribution chart

What it is not:

- not the homepage business summary
- not the priority prospect list
- not the market opportunity overview expected by the banker-facing homepage

### `GET /api/dashboard/summary`

Status:

- `Available now`

Purpose:

- homepage summary cards

### `GET /api/dashboard/market-overview`

Status:

- `Available now`

Purpose:

- homepage market opportunity charts

### `GET /api/dashboard/priority-prospects`

Status:

- `Available now`

Purpose:

- homepage top prospects panel

### `GET /api/dashboard/trigger-signals`

Status:

- `Available now`

Purpose:

- homepage trigger signals panel

### `GET /api/signals`

Status:

- `Available now`

Purpose:

- paginated low-level trigger signal list

Frontend note:

- usable now for signal pages and debug/detail experiences
- current `id` can be treated as `signalId` for UI state and list rendering

### `GET /api/timeline`

Status:

- `Available now`

Purpose:

- paginated low-level event timeline

### `GET /api/rag/index/status`

Status:

- `Available now`

Purpose:

- admin or debug status page

### `POST /api/rag/query`

Status:

- `Available now`

Purpose:

- general Copilot / RAG question answering

Frontend note:

- this remains the generic ask endpoint
- for prospect-specific pages, prefer the prospect-scoped APIs first

### `POST /api/insights/generate`

Status:

- `Available now`

Purpose:

- generate a structured insight and persist it if valid citations exist

## What Frontend Can Connect To Today

### Homepage

Frontend can connect now:

- `GET /api/dashboard/summary`
- `GET /api/dashboard/market-overview`
- `GET /api/dashboard/priority-prospects`
- `GET /api/dashboard/trigger-signals`
- `GET /api/dashboard/overview` for operational/admin panels

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
- `GET /api/prospects/{prospect_id}/copilot`
- `GET /api/prospects/{prospect_id}/brief`
- `POST /api/prospects/{prospect_id}/question`

### Prospect List / Prospect Detail

Frontend can connect now:

- `GET /api/prospects`
- `GET /api/prospects/{prospect_id}`
- `GET /api/prospects/{prospect_id}/signals`
- `GET /api/prospects/{prospect_id}/timeline`
- `GET /api/prospects/{prospect_id}/evidence`
- `GET /api/prospects/{prospect_id}/brief`
- `POST /api/prospects/{prospect_id}/question`
- `GET /api/prospects/{prospect_id}/copilot`

Current limitation:

- `prospect_id` is currently derived from `company_id`
- there is not yet a separately persisted banker workflow state

## Filter Metadata

Requested endpoint:

- `GET /api/metadata/filters`

Status:

- `Planned later`

For now, frontend can hardcode or derive temporary options from current API results.

Current feasible temporary values:

- `entity`: currently `HKG` is the most reliable option on low-level signal/timeline views
- `signal_type`: `market`, `cross_border`, `financing`, `risk`, `growth`
- `source`: depends on loaded source coverage
- `priority_level`: `high`, `medium`, `low` on the prospect layer

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

If the frontend wants to match the target product more closely, the next backend additions should be:

1. `GET /api/metadata/filters`
2. persisted prospect workflow state such as owner, stage, and last-action
3. prospect insight history endpoint
4. company size segmentation once a reliable size/profile model exists
5. standardized frontend error contract

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
