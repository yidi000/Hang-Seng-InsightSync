# Prospecting Dashboard and Copilot Readiness Design

Date: 2026-05-06

## Goal

Bring InsightSync to a trustworthy pre-acquisition demo state for four product
capabilities:

- Market Opportunity Overview
- Priority Prospect List
- Prospect Intelligence
- Trigger Signals

The work must be validated in two phases:

1. **Business-trustworthy first**: scoring, mapping, evidence quality, and LLM
   citation behavior must be defensible.
2. **Demo-ready second**: dashboard and Copilot must render the four product
   capabilities directly from backend APIs.

## Current State

The database snapshot has enough volume for a first demo:

- `companies`: 2,775
- `prospects`: 2,775
- `prospect_evidence_items`: 117,448
- `prospect_signals`: 45,629
- `prospect_scores`: 2,775
- `market_opportunity_snapshots`: 184
- `rag_documents`: 20,000
- `rag_chunks`: 20,000
- `rag_embeddings`: 20,000

The RAG index is curated-first. Current `rag_documents` are sourced from
`prospect_evidence_items`, not the old raw fallback path.

Known gaps:

- Company mapping coverage is only `18.2%`, below the target of `60%`.
- Score distribution is not useful enough: `A = 2,748`, `B = 19`, `D = 8`.
- Copilot has citation validation and evidence-gated fallback behavior, but it
  currently retrieves mostly through SQL keyword/filter search rather than
  hybrid SQL plus vector retrieval.
- `LLM_API_KEY` is configured, but real GLM generation depends on
  `ENABLE_LLM_GENERATION=true`.

## Design Principles

Dashboard core numbers and rankings must be deterministic. LLMs may explain,
summarize, and generate RM-facing text, but they must not be the source of truth
for score, tier, counts, or chart values.

LLM output must be citation-gated. Any generated priority reason, market
narrative, prospect brief, recommended entry angle, or Copilot answer must cite
valid `evidence_id` values from retrieved evidence. Output without valid
citations is either rejected or marked for human review.

Retrieval should be hybrid:

- SQL handles structured filters such as prospect, region, industry, tier,
  source, date range, signal subtype, and score factors.
- Vector RAG handles semantic questions, vague business intent, policy or macro
  interpretation, and similar-evidence discovery.

## Product Capability Mapping

| Capability | Backend source of truth | LLM role |
| --- | --- | --- |
| Market Opportunity Overview | `market_opportunity_snapshots`, `prospect_signals`, `prospects` | Generate cited market narrative and hotspot explanation. |
| Priority Prospect List | `prospects` + `prospect_scores` | Generate cited reasons, likely needs, product fit, and entry angle from score factors and evidence. |
| Prospect Intelligence | `prospects`, `prospect_evidence_items`, `prospect_signals`, timeline endpoints | Generate cited company summary, likely needs, RM action, and outreach brief. |
| Trigger Signals | `prospect_signals` + evidence IDs | Refine subtype where needed and explain business impact with citations. |

## Priority Prospect List Boundary

Priority ranking must be deterministic.

The scoring pipeline owns:

- `score`
- `tier`
- rank ordering
- score factors
- evidence-based feature counts

GLM owns only the explanation layer:

- why this prospect is ranked here
- recommended products
- likely needs
- recommended entry angle
- RM next action

Every LLM-generated reason must cite one or more `evidence_id` values. Reasons
with no valid citations must not be shown as trusted dashboard content.

## Copilot Design

Copilot should always be called through the backend. The frontend must not call
GLM or vector storage directly.

Request flow:

```text
User question
-> parse context: global / market / prospect / signal
-> build SQL retrieval scope from filters
-> retrieve structured records and semantic RAG matches
-> merge evidence, score factors, signals, timeline, and market buckets
-> ask GLM for JSON-only answer using retrieved evidence
-> validate citation ids
-> store conversation, messages, and citations
-> return answer plus evidence cards
```

Context-specific retrieval:

- `prospect`: retrieve `prospect_evidence_items`, `prospect_signals`,
  `prospect_scores`, score reasons, and timeline for the requested prospect.
- `market`: retrieve `market_opportunity_snapshots` plus macro, policy, GBA,
  sector, HKMA, government, and research evidence.
- `signal`: retrieve the signal, linked evidence, nearby evidence for the same
  prospect, and similar vector matches.
- `global`: retrieve from curated evidence with structured filters and vector
  similarity.

Answer rules:

- Use only retrieved evidence.
- Every material claim must cite at least one valid `evidence_id`.
- If no evidence is retrieved, return `insufficient_evidence`.
- If GLM returns citations that are not in the retrieved evidence set, discard
  them. If no valid citation remains, return `insufficient_evidence`.
- Store `model_name`, `prompt_version`, `confidence`, `requires_human_review`,
  and citation records.

## Business-Trustworthy Acceptance Checklist

All items in this section must be completed before the demo-readiness phase is
accepted.

### Company Mapping

- Current coverage: `18.2%`.
- Target coverage: at least `60%`.
- Acceptance query: latest `data_quality_reports.company_mapping.coverage >= 0.6`.
- Rationale: evidence and signals must map reliably to prospects before RM-facing
  ranking is credible.

### Priority Scoring

- Recalculate score and tier so A/B/C/D have meaningful separation.
- Avoid the current pattern where almost every prospect is tier A.
- Suggested distribution:
  - A: top 10-15%
  - B: next 20-30%
  - C: next 30-40%
  - D: remaining or insufficient evidence
- Acceptance: top 20 prospects each have clear score factors and evidence-backed
  reasons.

### Evidence-Backed Score Reasons

- Every A/B prospect must have at least one curated evidence item.
- Every A/B prospect must have at least one meaningful signal when available:
  `growth`, `expansion`, `funding`, `cross_border`, or `market_attention`.
- Every score reason shown to users must include valid `evidence_id` citations.

### Product Fit and Entry Angle

Recommended products and entry angles must be explainable from signals and
evidence.

Initial mapping:

- `cross_border` -> trade finance, cash management, cross-border services
- `funding` -> lending, capital markets, working capital
- `expansion` -> cash management, working capital, treasury services
- `policy` or GBA relevance -> treasury, cross-border services, advisory angle
- `market_attention` -> RM review, relationship warm-up, capital markets watch

Acceptance: top prospects expose `recommended_products` and
`recommended_entry_angle` with cited evidence.

### Signal Subtype Quality

Current subtype distribution includes:

- `growth`: 35,015
- `market_attention`: 7,176
- `cross_border`: 2,783
- `trade`: 266
- `funding`: 228
- `expansion`: 138
- `policy`: 13
- `risk`: 9
- `hiring`: 1

Acceptance: sample the top 50 dashboard signals and verify that subtype matches
the underlying evidence. Incorrect subtype assignment must be fixed by rules or
GLM structured extraction with citations.

### Market Overview Trust

Market overview must not be only a count of companies.

It must support:

- industry hotspots
- region hotspots
- size-band distribution
- signal-type distribution
- GBA, policy, macro, or sector evidence where available
- drill-down from each chart bucket to evidence

Acceptance: every market chart bucket can be traced to underlying evidence or
signals.

### LLM Insight Persistence

Generated insight records must include:

- JSON output
- valid citations
- confidence
- `requires_human_review`
- prompt version
- model name, expected `glm-4.7-flash`

No-citation output must not enter trusted dashboard fields.

## Demo-Ready Acceptance Checklist

These items are accepted after the business-trustworthy checklist passes.

### Market Opportunity Overview

Dashboard must show:

- lead pool size
- opportunity hotspots by industry
- region breakdown
- size-band breakdown
- signal breakdown
- optional GLM-generated cited market narrative

API:

- `GET /api/dashboard/market-overview`

Acceptance: frontend renders charts from backend response without client-side
business aggregation.

### Priority Prospect List

Dashboard must show:

- ranked prospects
- score
- tier
- industry
- region
- product fit
- recommended entry angle
- cited reasons

API:

- `GET /api/dashboard/priority-prospects`

Acceptance: opening a top prospect shows evidence supporting its ranking and
entry angle.

### Prospect Intelligence

Prospect detail must show:

- profile
- business model or description
- latest evidence
- signals
- timeline
- likely needs
- possible banking opportunities
- Copilot brief

APIs:

- `GET /api/prospects/{prospectId}`
- `GET /api/prospects/{prospectId}/signals`
- `GET /api/prospects/{prospectId}/timeline`
- `GET /api/prospects/{prospectId}/evidence`
- `GET /api/prospects/{prospectId}/insights`
- `POST /api/copilot/prospect/{prospectId}/brief`

### Trigger Signals

Dashboard and prospect detail must show:

- signal subtype
- signal text
- event time
- source
- evidence link
- optional GLM-generated cited impact explanation

APIs:

- `GET /api/dashboard/trigger-signals`
- `GET /api/prospects/{prospectId}/signals`

### Copilot

Copilot must support:

- `global`
- `market`
- `prospect`
- `signal`

Response must include:

- `answer`
- `status`
- `citations`
- `suggestedActions`
- `structuredInsight`

Acceptance:

- Evidence-backed questions return citation cards.
- No-evidence questions return `insufficient_evidence`.
- GLM output with no valid citations is not accepted as a normal answer.
- Prospect questions use prospect-scoped evidence, signals, score factors, and
  timeline.
- Market questions use market snapshots plus macro, policy, sector, and GBA
  evidence.
- Semantic questions use vector RAG in addition to SQL filters.

## Error Handling

Dashboard APIs should return empty arrays and quality warnings rather than
silently fabricating values when data is missing.

Copilot should return `insufficient_evidence` when retrieval fails or when GLM
does not cite retrieved evidence.

GLM JSON parse failure should return a controlled error and write an
`llm_generation_runs` audit record where applicable.

## Testing Strategy

Business-quality tests:

- Company mapping coverage is at least `60%`.
- A/B/C/D tier distribution is not collapsed into one tier.
- Each top 20 prospect has evidence-backed score reasons.
- Top 50 signals pass subtype spot-check or structured validation.
- Market buckets drill down to evidence.

Copilot tests:

- `global`, `market`, `prospect`, and `signal` contexts return valid structures.
- Prospect context retrieves prospect-specific evidence, score factors, signals,
  and timeline.
- Market context retrieves market snapshots and macro/policy evidence.
- Semantic questions use vector RAG results.
- No-evidence questions return `insufficient_evidence`.
- Invalid GLM citations are rejected.

Frontend acceptance tests:

- Dashboard renders all four product capability areas without frontend-side
  business aggregation.
- Priority prospects show score, tier, product fit, entry angle, and cited
  reasons.
- Prospect detail shows profile, evidence, signals, timeline, insights, and
  Copilot brief.
- Copilot chat supports follow-up questions and renders citation cards.

## Non-Goals

- Do not let GLM directly decide ranking.
- Do not require full 117,448-row RAG coverage before first demo acceptance.
- Do not treat uncited generated text as trusted insight.
- Do not require hiring trends for MVP acceptance, although the subtype remains
  available for future data sources.

