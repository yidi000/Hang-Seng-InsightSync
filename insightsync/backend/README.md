# InsightSync Backend

FastAPI backend for InsightSync's company intelligence, prospect scoring, evidence, workflow, RAG, and Copilot APIs.

## Responsibilities

- Serve frontend-facing APIs for dashboard, companies, prospects, signals, timeline, metadata filters, RAG, and generated insights.
- Read application-ready data from PostgreSQL, initialized from the bundled demo SQLite snapshot for local development.
- Assemble company-centric state, prospect ranking, score breakdowns, linkage quality, decision answers, evidence bundles, and RM-ready briefs.
- Keep GenAI out of final score assignment. GenAI is used for structured extraction, evidence-grounded Q&A, explanation, and advisory review.

## Local Run

From the repository root:

```bash
docker compose up --build
docker compose exec api python -m insightsync.backend.workflows.init_dev_backend
```

Or without Docker, configure `DATABASE_URL`, then run:

```bash
alembic upgrade head
python -m insightsync.backend.workflows.sync_from_sqlite --full
python -m insightsync.backend.workflows.build_rag_index --full
uvicorn insightsync.backend.main:app --reload --port 8000
```

## Acceptance

Deterministic backend/data tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ENABLE_LLM_GENERATION=false python -m pytest insightsync/backend/tests insightsync/data/tests -q
```

Multilingual GenAI extraction fixture check:

```bash
python -m insightsync.backend.workflows.glm_extraction_demo --mock --strict --api-preview
```

Live API/frontend contract check:

```bash
python -m insightsync.backend.workflows.acceptance_check --api-base http://127.0.0.1:8000 --frontend-base http://127.0.0.1:3000 --strict
```

Optional live GLM 4.7 Flash smoke check:

```bash
python -m insightsync.backend.workflows.glm_smoke_check
```

## Core Endpoints

- `GET /healthz`
- `GET /api/metadata/filters`
- `GET /api/dashboard/overview`
- `GET /api/dashboard/summary`
- `GET /api/companies`
- `GET /api/companies/{company_id}`
- `GET /api/prospects`
- `GET /api/prospects/{prospect_id}`
- `GET /api/prospects/{prospect_id}/evidence`
- `GET /api/prospects/{prospect_id}/brief`
- `GET /api/prospects/{prospect_id}/copilot`
- `GET /api/prospects/{prospect_id}/review`
- `GET /api/prospects/{prospect_id}/workflow`
- `PUT /api/prospects/{prospect_id}/workflow`
- `POST /api/prospects/{prospect_id}/question`
- `GET /api/signals`
- `GET /api/timeline`
- `POST /api/rag/query`
- `POST /api/insights/generate`

## Architecture

```text
backend/
  api/            REST route handlers
  services/       company/prospect/fusion/scoring/RAG business logic
  repositories/   read models and database access helpers
  db/             SQLAlchemy session and table definitions
  schemas/        Pydantic response and request contracts
  ai/             OpenAI-compatible provider layer, including GLM-compatible config
  workflows/      local initialization, sync, RAG build, smoke, and acceptance scripts
```
