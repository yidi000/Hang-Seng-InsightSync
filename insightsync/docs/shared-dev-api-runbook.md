# Shared Dev API Runbook

This runbook is for the backend owner who will provide a ready-to-use API for frontend developers.

Frontend developers should not deploy PostgreSQL, run migrations, or sync demo data. They only need the final API base URL and optional `X-API-Key`.

## What You Need First

You need one server or cloud VM with:

- Docker Engine
- Docker Compose plugin
- outbound internet access for Docker image pulls and Python package installs
- an open inbound API port, usually `8000`, or a reverse proxy on `443`
- enough disk for PostgreSQL data and Docker images

Do not expose PostgreSQL to the frontend. PostgreSQL should only be reachable by the backend container.

## Deployment Files

Use:

- `docker-compose.shared-dev.yml`
- `deploy/shared-dev.env.example`
- `insightsync/backend/workflows/init_dev_backend.py`

The shared-dev compose file differs from the local compose file:

- PostgreSQL is not published on host port `5432`.
- API is published on `${API_PORT:-8000}`.
- A one-off `init` service runs migrations, SQLite sync, and RAG index build.

## Step 1: Prepare The Server

Install Docker and the Docker Compose plugin on the server.

Clone the repository:

```bash
git clone <repo-url>
cd Hang-Seng-InsightSync
git checkout main
```

If this work is still on a PR branch:

```bash
git fetch origin
git checkout feature/from-main-20260422
```

## Step 2: Create Environment File

Copy the template:

```bash
cp deploy/shared-dev.env.example .env.shared-dev
```

Edit `.env.shared-dev`:

```bash
POSTGRES_PASSWORD=<long-random-password>
DATABASE_URL=postgresql+psycopg://insightsync:<same-password>@postgres:5432/insightsync
CORS_ALLOW_ORIGINS=<frontend-origin-or-*>
API_KEYS=<optional-shared-dev-api-key>
```

For live GLM behavior, also set:

```bash
ENABLE_LLM_GENERATION=true
ENABLE_LLM_BRIEF_GENERATION=false
LLM_API_KEY=<z-ai-key>
LLM_BASE_URL=https://api.z.ai/api/paas/v4/
LLM_CHAT_MODEL=glm-4.7-flash
LLM_ENABLE_THINKING=false
LLM_TIMEOUT_SECONDS=45
```

For frontend UI development, live GLM is optional. If disabled, the API returns deterministic fallback output for LLM-assisted features. Keep `ENABLE_LLM_BRIEF_GENERATION=false` for a responsive shared UI; `/review` and `/question` still exercise the live LLM when `ENABLE_LLM_GENERATION=true`.

## Step 3: Start PostgreSQL

```bash
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml up -d postgres
```

Check health:

```bash
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml ps
```

## Step 4: Initialize Demo Data

Run the one-off init service:

```bash
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml run --rm init
```

This performs:

- Alembic migration to latest schema
- demo SQLite snapshot sync into PostgreSQL
- RAG document/chunk/embedding build

You can rerun this command after pulling new backend code or a new demo snapshot.

## Step 5: Start API

```bash
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml up -d api
```

Check logs:

```bash
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml logs -f api
```

## Step 6: Smoke Test

From the server:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/dashboard/summary
curl "http://127.0.0.1:8000/api/prospects?limit=20"
curl http://127.0.0.1:8000/api/prospects/prospect:hkg-alpha-fintech
curl http://127.0.0.1:8000/api/prospects/prospect:hkg-alpha-fintech/evidence
curl http://127.0.0.1:8000/api/metadata/filters
```

If `API_KEYS` is configured:

```bash
curl -H "X-API-Key: <key>" http://127.0.0.1:8000/api/prospects?limit=20
```

From your laptop, replace `127.0.0.1` with the server domain or IP.

If frontend is also running, use the live acceptance workflow:

```bash
python -m insightsync.backend.workflows.acceptance_check --api-base http://127.0.0.1:8000 --frontend-base http://127.0.0.1:3000 --strict
```

Add `--include-review --include-rag --timeout-seconds 45` when live GLM endpoints should be checked.

## Step 7: Give Frontend The Handover Package

Give frontend:

```text
API_BASE_URL=http://<server-host>:8000
Swagger=http://<server-host>:8000/docs
OpenAPI=http://<server-host>:8000/openapi.json
Demo prospect_id=prospect:hkg-alpha-fintech
X-API-Key=<only if API_KEYS is configured>
```

If frontend is hosted on HTTPS, the API should also be served through HTTPS to avoid browser mixed-content blocking. Put a reverse proxy or platform load balancer in front of port `8000` and share the HTTPS URL.

## Update Procedure

When backend code changes:

```bash
git pull
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml build api init
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml run --rm init
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml up -d api
```

## Data Refresh Procedure

For frontend UI development, the committed demo snapshot is enough.

When backend has new demo data or parsed outputs:

```bash
git pull
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml run --rm init
docker compose --env-file .env.shared-dev -f docker-compose.shared-dev.yml restart api
```

## Troubleshooting

API returns `{"detail":"Invalid API key"}`:

- `API_KEYS` is configured.
- Frontend must send `X-API-Key`.

Browser CORS error:

- set `CORS_ALLOW_ORIGINS` to the frontend origin, or `*` for shared dev.
- restart API after changing env.

`/api/prospects` returns empty data:

- rerun the init service.
- check that `SQLITE_SOURCE_PATH` points to `insightsync/data/storage/demo/insightsync_demo.db`.

RAG status has no chunks or embeddings:

- rerun the init service.
- inspect API logs for embedding or database errors.

Live GLM review/extraction returns fallback:

- check `ENABLE_LLM_GENERATION=true`.
- check `LLM_API_KEY`.
- GLM fallback is still renderable for frontend development.

PostgreSQL connection fails:

- make sure `DATABASE_URL` password matches `POSTGRES_PASSWORD`.
- make sure services were started with `--env-file .env.shared-dev`.
