# Dev Backend Handover

This runbook is for frontend developers who need a working InsightSync API.

Frontend should consume the backend through HTTP APIs only. Do not connect the frontend directly to PostgreSQL.

## Option A: Use A Shared Dev API

This is the preferred frontend workflow when a shared backend environment is available.

Backend owner setup instructions are in `insightsync/docs/shared-dev-api-runbook.md`.

The backend owner should provide:

- API base URL, for example `https://dev-api.example.com`
- Swagger/OpenAPI URL, usually `{API_BASE_URL}/docs` and `{API_BASE_URL}/openapi.json`
- whether `X-API-Key` is required
- if required, the API key value
- whether live GLM calls are enabled or deterministic fallback is expected
- demo prospect ID for smoke testing, for example `prospect:hkg-alpha-fintech`

Frontend environment example:

```bash
VITE_API_BASE_URL=https://dev-api.example.com
VITE_INSIGHTSYNC_API_KEY=<only-if-API_KEYS-is-configured>
```

Smoke checks:

```text
GET /healthz
GET /api/dashboard/summary
GET /api/prospects?limit=20
GET /api/prospects/prospect:hkg-alpha-fintech
GET /api/prospects/prospect:hkg-alpha-fintech/evidence
GET /api/prospects/prospect:hkg-alpha-fintech/review
GET /api/metadata/filters
```

## Option B: Run The Backend Locally With Docker

Docker Compose starts PostgreSQL with pgvector and the FastAPI service.

```bash
cp .env.example .env
docker compose up --build
```

In another terminal, initialize the database and demo data:

```bash
docker compose exec api python -m insightsync.backend.workflows.init_dev_backend
```

This command runs:

- Alembic migrations
- SQLite demo snapshot sync into PostgreSQL
- RAG document/chunk/embedding index build

Open:

```text
http://127.0.0.1:8000/healthz
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

## Optional GLM Setup

The UI can be developed without live GLM calls. In that mode, the backend returns deterministic fallback output for LLM-assisted features.

For live GLM-4.7 Flash behavior, configure `.env`:

```bash
ENABLE_LLM_GENERATION=true
LLM_API_KEY=<your-z-ai-key>
LLM_BASE_URL=https://api.z.ai/api/paas/v4/
LLM_CHAT_MODEL=glm-4.7-flash
LLM_ENABLE_THINKING=false
LLM_TIMEOUT_SECONDS=45
```

Then restart the API container.

## Auth, CORS, And Rate Limit

Local defaults:

- `API_KEYS=` means API key auth is disabled.
- If `API_KEYS` is configured, frontend must send `X-API-Key`.
- `CORS_ALLOW_ORIGINS=*` allows local frontend apps.
- `RATE_LIMIT_PER_MINUTE=0` disables rate limiting.

Public paths:

- `/healthz`
- `/openapi.json`
- `/docs`
- `/redoc`

## Expected Demo Data

The bundled demo SQLite snapshot currently includes:

- company profiles
- trigger signals
- timeline events
- parsed documents
- parsed metrics, risk factors, and business events

Generated insights may be empty until generation endpoints are called.

## Frontend Contract

Use these references:

- `insightsync/docs/frontend-api-guide.md`
- `/openapi.json`
- `/docs`

Important frontend rules:

- backend responses use `snake_case`
- frontend should not recompute scores or linkage fields
- `fallback` and `llm_error_fallback` are renderable states, not integration failures
- `scoring_eligibility.eligible=false` means show as context/audit evidence, not as score input

## Backend Work That Can Continue In Parallel

These backend tasks should not block frontend implementation:

- real-sample end-to-end validation
- scoring and linkage calibration
- multilingual extraction quality review
- external market-intelligence fusion checks
- production deployment hardening
