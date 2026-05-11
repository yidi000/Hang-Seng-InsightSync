# Frontend API Guide

This document maps the frontend request list to the backend state in this repository.

The goal is to answer three questions clearly:

1. What can the frontend connect to right now
2. What is not available yet but can be added later
3. What is not part of the current backend scope

API payloads are intentionally page-ready where possible so the frontend team does not need to reproduce backend scoring or linkage logic.

## Frontend Start Pack

### Can frontend start now?

Yes. The current backend contracts are ready for frontend implementation of the main application flows:

- homepage/dashboard summary
- prospect list and prospect detail
- company explorer and company detail
- parsed-evidence drill-down
- prospect brief, copilot workspace, RAG question answering, and LLM review panels
- workflow state update for owner/stage/status/notes

The frontend should treat this guide plus `/openapi.json` as the integration contract. The backend will continue improving real-sample coverage, scoring calibration, and evaluation quality, but those improvements should be additive rather than blocking UI build-out.

### Base URL and Docs

Local Docker default:

```text
http://127.0.0.1:8000
```

Useful service URLs:

```text
GET http://127.0.0.1:8000/healthz
GET http://127.0.0.1:8000/openapi.json
GET http://127.0.0.1:8000/docs
```

### Auth, CORS, and Rate Limits

Current local defaults:

- auth is disabled when `API_KEYS` is empty
- if `API_KEYS` is configured, frontend must send `X-API-Key: <key>`
- CORS defaults to `*` through `CORS_ALLOW_ORIGINS=*`
- rate limiting is disabled when `RATE_LIMIT_PER_MINUTE=0`

Public paths even when API key auth is enabled:

- `/healthz`
- `/openapi.json`
- `/docs`
- `/redoc`

### Naming Convention

Backend responses use `snake_case`. The frontend can either use `snake_case` directly or map to `camelCase` in a thin API adapter. Do not ask the backend to emit both conventions for the same field.

### Recommended Page-to-API Map

| Frontend surface | Primary APIs |
| --- | --- |
| Home dashboard | `GET /api/dashboard/summary`, `GET /api/dashboard/market-overview`, `GET /api/dashboard/priority-prospects`, `GET /api/dashboard/trigger-signals` |
| Prospect list | `GET /api/prospects`, `GET /api/metadata/filters` |
| Prospect detail | `GET /api/prospects/{prospect_id}`, `GET /api/prospects/{prospect_id}/evidence`, `GET /api/prospects/{prospect_id}/brief` |
| Prospect copilot | `GET /api/prospects/{prospect_id}/copilot`, `POST /api/prospects/{prospect_id}/question`, `GET /api/prospects/{prospect_id}/review` |
| Prospect workflow | `GET /api/prospects/{prospect_id}/workflow`, `PUT /api/prospects/{prospect_id}/workflow` |
| Company explorer | `GET /api/companies`, `GET /api/metadata/filters` |
| Company detail | `GET /api/companies/{company_id}` |
| Signal/timeline debug views | `GET /api/signals`, `GET /api/timeline` |
| Admin/debug | `GET /api/dashboard/overview`, `GET /api/rag/index/status` |

### First Integration Smoke Test

After backend startup and SQLite sync, frontend can verify:

```text
GET /healthz
GET /api/dashboard/summary
GET /api/prospects?limit=20
GET /api/prospects/prospect:hkg-alpha-fintech
GET /api/prospects/prospect:hkg-alpha-fintech/evidence
GET /api/prospects/prospect:hkg-alpha-fintech/review
GET /api/metadata/filters
```

Expected local demo behavior:

- `/healthz` returns `{"status":"ok", ...}`
- demo prospect IDs follow `prospect:{company_id}`, for example `prospect:hkg-alpha-fintech`
- `generated_insights` may be empty until generation flows are run
- `company_size_breakdown` is currently `[]`
- GLM/LLM endpoints return deterministic fallback states if LLM generation is disabled or the provider fails

### Frontend Should Not Recompute

The frontend should display these backend fields, not recompute them:

- `priority_score`, `opportunity_score`, `risk_score`
- `evidence_confidence_score`
- `priority_level`
- `score_breakdown`
- `linkage_quality`
- `governance_flags`
- `scoring_eligibility`
- LLM review `review_status`

This matters because scoring and linkage rules are part of the auditable backend decision layer.

### Status Handling Rules

Treat these statuses as normal, renderable states:

| Field/location | Values | Frontend handling |
| --- | --- | --- |
| `priority_level` | `high`, `medium`, `monitor` | use for badges and sorting; do not recompute from raw scores |
| `workflow_state.status` | `open`, `in_progress`, `closed`, or custom saved value | render as banker workflow state |
| `workflow_state.review_status` | `not_reviewed`, `reviewed`, or custom saved value | render as human workflow status, separate from LLM review |
| `/review.status` | `ok`, `fallback`, `llm_error_fallback` | `ok` means live LLM review; fallback statuses are still usable advisory output |
| `/question.status` and `/rag/query.status` | `ok`, `insufficient_evidence`, `llm_error_fallback` | show answer when present; for insufficient evidence, prompt user to refine question or inspect evidence |
| `recent_documents[].genai_extraction.status` | `ok`, `skipped`, `model_error`, or `null` | show extraction audit when present; `null` means document was parsed before GLM extraction or extraction was not run |
| `scoring_eligibility.eligible` | `true`, `false` | only render eligible facts as score inputs; render non-eligible facts as context/audit evidence |

### Non-Blocking Backend Work Still Continuing

Frontend can start while backend continues:

- real-sample end-to-end validation on more reports and announcements
- score/linkage calibration against labeled examples
- multilingual extraction quality review across English, simplified Chinese, traditional Chinese, and Cantonese-style text
- external market-intelligence fusion quality checks
- production handover runbook hardening

These should not require frontend contract rewrites unless new UI surfaces are requested.

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
- review objects on `/api/prospects/{prospect_id}/review`

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

Demo data note:

- the bundled SQLite demo snapshot includes company profiles, parsed document outputs, structured risks/events/metrics, and current prospect APIs can be exercised after PostgreSQL sync
- `generated_insights` is empty until `/api/insights/generate` or prospect/RAG generation flows persist citation-validated outputs

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
- exposes `scorecard_version`, `calibration_status`, `priority_formula`, `score_inputs`, `linkage_quality`, and `governance_flags`
- keeps `evidence_confidence_score` separate from `opportunity_score` so weak evidence is visible instead of hidden inside the business score
- includes `recommended_next_step` and `recommended_product_themes`
- includes `workflow_state` with owner/stage/status/action fields when workflow state has been saved
- supports search and basic filters aligned to company fields

Scoring contract:

- current scorecard version is `prospect-scorecard-v0.2`
- current calibration status is `expert_defined_unvalidated_v0`
- final prospect scores are generated by deterministic scorecard logic; LLM output is not used for final score assignment
- `linkage_quality` summarizes direct evidence ratio, scoreable evidence ratio, context-only evidence count, and linkage-type counts
- `governance_flags` should be displayed as caution/review indicators, not as primary RM calls to action

Current limitation:

- no dedicated persisted prospect table yet
- no revenue normalization or banker-assignment logic yet

### `GET /api/prospects/{prospect_id}`

Status:

- `Available now`

Frontend need:

- prospect detail base profile

Current scope:

- returns a business-facing prospect object plus linked company evidence
- detail is derived from the existing company-centric evidence layer
- includes the current `workflow_state`

Current limitation:

- prospect identity is still derived from `company_id`
- identity/linkage matching is evaluated with a small local gold set, but subsidiary and alias coverage still needs expansion before production use

### `GET /api/prospects/{prospect_id}/workflow`

Status:

- `Available now`

Current scope:

- returns persisted banker workflow state for the prospect
- returns a default open/new/not-reviewed state before the prospect has been updated

### `PUT /api/prospects/{prospect_id}/workflow`

Status:

- `Available now`

Current scope:

- updates owner, stage, status, last action, next action, review status, and notes
- persists state by `prospect_id`

Current limitation:

- this is a lightweight workflow state, not a full CRM task model

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
- when GLM-assisted extraction has been run, `recent_documents[].genai_extraction` includes the model extraction audit trail: status, prompt version, accepted/rejected counts, scoring eligibility counts, rejected reason counts, normalized facts, and evidence spans
- `management_statement` and `opportunity_signal_candidate` facts are context-only and should not be rendered as scoring inputs unless `scoring_eligibility.eligible=true`

Example `recent_documents[].genai_extraction`:

```json
{
  "status": "ok",
  "prompt_version": "genai-section-extraction-v0.1",
  "candidate_count": 1,
  "accepted_count": 3,
  "rejected_count": 1,
  "scoring_eligible_counts": {
    "risk_factor": 1,
    "business_event": 1
  },
  "context_only_count": 1,
  "rejected_reason_counts": {
    "duplicate_existing_fact": 1
  },
  "accepted_facts": [
    {
      "fact_type": "risk_factor",
      "category": "regulatory",
      "description": "Cross-border licensing requirements are tightening.",
      "extraction_confidence": 0.91,
      "evidence_span": {
        "document_id": "hkex-annual-1",
        "section_id": 2,
        "paragraph_id": 4,
        "chunk_id": "s2:p4",
        "page": 11,
        "quoted_text": "cross-border licensing requirements are tightening",
        "language": "en"
      },
      "scoring_eligibility": {
        "eligible": true,
        "reasons": ["valid_evidence_span", "allowed_candidate_section"]
      }
    }
  ],
  "rejected_facts": [
    {
      "fact_type": "metric",
      "reasons": ["duplicate_existing_fact"]
    }
  ]
}
```

Current limitation:

- does not yet include curated banker notes or human review state
- documents parsed before GLM extraction was enabled return `genai_extraction: null`

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

### `GET /api/prospects/{prospect_id}/review`

Status:

- `Available now`

Current scope:

- returns linkage-quality review items
- returns audit findings about subjective or over-eager decision logic
- returns extraction opportunities that would improve evidence quality
- uses GLM-assisted review when LLM generation is enabled and configured
- uses deterministic fallback review when LLM generation is disabled

Frontend use:

- show this in an analyst/debug/governance panel, not as the primary RM call-to-action
- useful labels include `review_status`, `severity`, `area`, and `suggested_action`
- treat `status=ok` with `model_name=glm-4.7-flash` as live LLM review, and `status=fallback` or `status=llm_error_fallback` as deterministic fallback review

Current limitation:

- the review is advisory and does not rewrite scores
- LLM-assisted review quality depends on `ENABLE_LLM_GENERATION`, `LLM_API_KEY`, `LLM_TIMEOUT_SECONDS`, and prompt/model configuration

### `GET /api/prospects/{prospect_id}/insights`

Status:

- `Available now`

Current scope:

- returns generated insight history linked to the prospect company
- supports `limit`, `offset`, and optional `insight_type`
- useful after `/api/insights/generate` has persisted citation-validated outputs

Current limitation:

- demo snapshot may return an empty list when no generated insights have been persisted

### `GET /api/metadata/filters`

Status:

- `Available now`

Current scope:

- returns current filter options with counts for `regions`, `segments`, `industries`, `signal_types`, `sources`, and `datasets`
- intended for filter controls and debugging

Current limitation:

- values are derived from current data coverage, so they are not a static business taxonomy

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
- `GET /api/prospects/{prospect_id}/review`
- `GET /api/prospects/{prospect_id}/insights`

### Prospect List / Prospect Detail

Frontend can connect now:

- `GET /api/prospects`
- `GET /api/prospects/{prospect_id}`
- `GET /api/prospects/{prospect_id}/signals`
- `GET /api/prospects/{prospect_id}/timeline`
- `GET /api/prospects/{prospect_id}/workflow`
- `PUT /api/prospects/{prospect_id}/workflow`
- `GET /api/prospects/{prospect_id}/evidence`
- `GET /api/prospects/{prospect_id}/brief`
- `POST /api/prospects/{prospect_id}/question`
- `GET /api/prospects/{prospect_id}/copilot`
- `GET /api/prospects/{prospect_id}/review`
- `GET /api/prospects/{prospect_id}/insights`

Current limitation:

- `prospect_id` is currently derived from `company_id`
- workflow state is persisted, but there is not yet a full task/activity history model

## Filter Metadata

Requested endpoint:

- `GET /api/metadata/filters`

Status:

- `Available now`

Frontend can use this endpoint for filter controls. Workflow state values are persisted through the prospect workflow endpoint rather than returned as global static taxonomy values.

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

1. prospect task/activity history beyond the latest workflow state
2. company size segmentation once a reliable size/profile model exists
3. standardized frontend error contract
4. richer generated-insight history with citations and reviewer feedback

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

Recommended smoke checks:

```text
GET /healthz
GET /api/companies?limit=20
GET /api/prospects?limit=20
GET /api/dashboard/summary
GET /api/dashboard/priority-prospects
GET /api/rag/index/status
```
