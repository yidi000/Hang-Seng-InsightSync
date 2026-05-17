# Free Cloud Deployment Guide

This guide describes a low-cost/free deployment path for the InsightSync demo platform.

Recommended stack:

- Frontend: Vercel Hobby
- Backend API: Google Cloud Run
- Database: Supabase Free PostgreSQL

This setup is intended for demo, coursework, and shared development use. It is not a production banking deployment pattern.

## 1. Deployment Shape

The deployed platform has three parts:

```text
Browser
  -> Vercel Next.js frontend
  -> Cloud Run FastAPI backend
  -> Supabase PostgreSQL
```

The frontend must never connect directly to PostgreSQL. It should only call the FastAPI backend.

Current repository entry points:

- Backend Dockerfile: `Dockerfile`
- Backend app: `insightsync.backend.main:app`
- Frontend app: `insightsync/frontend`
- Demo SQLite snapshot: `insightsync/data/storage/demo/insightsync_demo.db`
- Database initializer: `python -m insightsync.backend.workflows.init_dev_backend`
- Acceptance checker: `python -m insightsync.backend.workflows.acceptance_check`

## 2. Why This Stack

### Vercel For Frontend

The frontend is a Next.js app, so Vercel is the simplest free hosting option.

Use it for:

- `/`
- `/prospects`
- `/signals`
- `/prospects/[id]`

### Cloud Run For Backend

The backend already has a root-level Dockerfile. Cloud Run can deploy this container and expose FastAPI over HTTPS.

Use it for:

- `/healthz`
- `/docs`
- `/openapi.json`
- `/api/*`

Keep `min instances = 0` for a free-tier style setup. This may cause cold starts.

### Supabase For PostgreSQL

Supabase Free provides managed PostgreSQL. Current demo data is small enough for the free plan.

Expected demo scale after the current snapshot:

```text
companies: about 45
prospects / lead pool: about 44
intelligence_records: about 274
trigger_signals: about 1394
timeline_events: about 280
```

Supabase Free constraints matter:

- database size is limited
- inactive free projects may pause
- this is suitable for demo/shared development, not regulated production use

## 3. Accounts Needed

Create accounts for:

- GitHub
- Supabase
- Google Cloud
- Vercel

Google Cloud may require a billing account even if Cloud Run usage stays inside free-tier allowances.

## 4. Prepare Supabase

1. Create a new Supabase project.
2. Choose a region close to the user base, preferably near Hong Kong if available.
3. Save:
   - project reference
   - database password
   - database connection string
4. In Supabase, find the direct PostgreSQL connection string.

The backend expects SQLAlchemy/psycopg format:

```text
postgresql+psycopg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require
```

Replace:

- `<password>` with the Supabase database password
- `<project-ref>` with the Supabase project ref

Do not commit this URL into Git.

## 5. Prepare Backend Environment Variables

Use these variables for the Cloud Run service.

Minimal deterministic demo mode:

```env
APP_ENV=prod
PORT=8000
DATABASE_URL=postgresql+psycopg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require
SQLITE_SOURCE_PATH=insightsync/data/storage/demo/insightsync_demo.db

ENABLE_LLM_GENERATION=false
ENABLE_LLM_BRIEF_GENERATION=false
LLM_API_KEY=
LLM_BASE_URL=https://api.z.ai/api/paas/v4/
LLM_CHAT_MODEL=glm-4.7-flash
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=2048
LLM_TIMEOUT_SECONDS=45
LLM_ENABLE_THINKING=false

RAG_TOP_K=6
RAG_MIN_SCORE=0.15

CORS_ALLOW_ORIGINS=https://<your-vercel-domain>
API_KEYS=
RATE_LIMIT_PER_MINUTE=0
```

Live GLM mode:

```env
ENABLE_LLM_GENERATION=true
ENABLE_LLM_BRIEF_GENERATION=false
LLM_API_KEY=<your-z-ai-key>
LLM_BASE_URL=https://api.z.ai/api/paas/v4/
LLM_CHAT_MODEL=glm-4.7-flash
LLM_ENABLE_THINKING=false
LLM_TIMEOUT_SECONDS=45
```

Keep `ENABLE_LLM_BRIEF_GENERATION=false` for a responsive UI. The live GLM paths should be `/api/prospects/{id}/review` and `/api/prospects/{id}/question`, not every brief/detail page load.

### API Key Auth

For the first demo deployment, keep:

```env
API_KEYS=
```

The formal Next.js frontend currently does not expose a production environment variable for injecting `X-API-Key` into every request. If `API_KEYS` is enabled before that frontend support is added, browser requests will fail with auth errors.

For a public demo URL, prefer:

- obscure/non-indexed deployment URL
- strict `CORS_ALLOW_ORIGINS`
- no confidential data
- short-lived demo period

## 6. Deploy Backend To Cloud Run

There are two common routes.

### Option A: Deploy From Source In The Console

1. Open Google Cloud Console.
2. Go to Cloud Run.
3. Create service.
4. Choose deploy from source repository.
5. Connect the GitHub repository.
6. Select the branch containing the current work.
7. Use the repository root as the build context.
8. Ensure Cloud Run uses the root-level `Dockerfile`.
9. Set container port to `8000`.
10. Add the backend environment variables from section 5.
11. Allow unauthenticated invocations.
12. Set min instances to `0`.
13. Deploy.

After deployment, save the Cloud Run HTTPS URL:

```text
https://<service-name>-<hash>-<region>.a.run.app
```

This is the backend API base URL.

### Option B: Deploy With gcloud

Install and initialize the Google Cloud SDK, then run from the repo root:

```bash
gcloud run deploy insightsync-api \
  --source . \
  --region asia-east2 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars APP_ENV=prod,PORT=8000,SQLITE_SOURCE_PATH=insightsync/data/storage/demo/insightsync_demo.db,ENABLE_LLM_GENERATION=false,ENABLE_LLM_BRIEF_GENERATION=false,RAG_TOP_K=6,RAG_MIN_SCORE=0.15,CORS_ALLOW_ORIGINS=https://<your-vercel-domain>,API_KEYS=,RATE_LIMIT_PER_MINUTE=0 \
  --set-env-vars DATABASE_URL="postgresql+psycopg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require"
```

If using live GLM, add:

```bash
--set-env-vars LLM_API_KEY="<your-z-ai-key>",LLM_BASE_URL=https://api.z.ai/api/paas/v4/,LLM_CHAT_MODEL=glm-4.7-flash,LLM_TIMEOUT_SECONDS=45,LLM_ENABLE_THINKING=false,ENABLE_LLM_GENERATION=true
```

For secrets, prefer Google Secret Manager once the demo is stable.

## 7. Initialize The Cloud Database

After Supabase exists and the Cloud Run backend has the correct `DATABASE_URL`, initialize the database once.

You can run this from your local machine.

PowerShell:

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require"
$env:SQLITE_SOURCE_PATH="insightsync/data/storage/demo/insightsync_demo.db"
python -m insightsync.backend.workflows.init_dev_backend
```

Bash:

```bash
export DATABASE_URL="postgresql+psycopg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require"
export SQLITE_SOURCE_PATH="insightsync/data/storage/demo/insightsync_demo.db"
python -m insightsync.backend.workflows.init_dev_backend
```

Expected output should include non-zero scanned counts, for example:

```text
companies.scanned: about 45
intelligence_records.scanned: about 274
trigger_signals.scanned: about 1394
client_one_view_timeline.scanned: about 280
rag_index.documents.scanned: about 1900+
```

If you rerun this command, many rows may show `inserted: 0` and `skipped: ...`. That is expected if the rows already exist.

## 8. Smoke Test Backend

Replace `<api-base>` with the Cloud Run URL.

```bash
curl "<api-base>/healthz"
curl "<api-base>/api/dashboard/summary"
curl "<api-base>/api/metadata/filters"
curl "<api-base>/api/prospects?limit=5"
curl "<api-base>/api/rag/index/status"
```

Expected:

- `/healthz` returns `status: ok`
- dashboard `lead_pool` is positive
- metadata filters include regions, industries, signal types, sources, and datasets
- prospects returns a non-empty `items` list

## 9. Deploy Frontend To Vercel

1. Open Vercel.
2. Add New Project.
3. Import the GitHub repository.
4. Set Root Directory:

```text
insightsync/frontend
```

5. Framework should be detected as Next.js.
6. Add environment variable:

```env
NEXT_PUBLIC_INSIGHTSYNC_API_BASE=https://<your-cloud-run-url>
```

7. Deploy.

After deployment, save the frontend URL:

```text
https://<your-vercel-project>.vercel.app
```

Then update backend `CORS_ALLOW_ORIGINS` to exactly this frontend URL and redeploy/restart the backend if needed.

## 10. End-To-End Acceptance

Run from your local machine:

```bash
python -m insightsync.backend.workflows.acceptance_check \
  --api-base https://<your-cloud-run-url> \
  --frontend-base https://<your-vercel-url> \
  --strict
```

For live GLM review/RAG checks:

```bash
python -m insightsync.backend.workflows.acceptance_check \
  --api-base https://<your-cloud-run-url> \
  --frontend-base https://<your-vercel-url> \
  --strict \
  --include-review \
  --include-rag \
  --timeout-seconds 45
```

Passing checks should include:

- `healthz`
- `metadata_filters`
- `dashboard_summary`
- `signals_and_timeline`
- `prospect_list_scorecard`
- `prospect_detail_contract`
- `prospect_evidence_brief_copilot`
- `frontend_routes`
- optional `prospect_review_optional`
- optional `prospect_rag_optional`

## 11. Manual UI Check

Open the Vercel URL and check:

- `/`
- `/prospects`
- `/signals`
- one `/prospects/{id}` detail page

Verify:

- dashboard cards have non-zero data
- prospect list has about 44 leads
- filters load from backend metadata
- detail page shows evidence, brief, score audit, and workflow state
- Copilot suggested questions render
- optional review/RAG calls complete if GLM is enabled

## 12. Update Procedure

### Frontend-only change

1. Commit and push to GitHub.
2. Vercel rebuilds automatically.
3. Run frontend smoke check.

### Backend code change

1. Commit and push to GitHub.
2. Redeploy Cloud Run.
3. Run:

```bash
curl "<api-base>/healthz"
```

4. Run acceptance check.

### Data snapshot or seed change

1. Update `insightsync/data/seeds/company_candidates.json` or the data pipeline.
2. Rebuild/update `insightsync/data/storage/demo/insightsync_demo.db`.
3. Commit both the seed and demo DB if the demo fixture changed.
4. Redeploy Cloud Run so the container includes the updated demo DB.
5. Rerun:

```bash
python -m insightsync.backend.workflows.init_dev_backend
```

against the Supabase `DATABASE_URL`.

6. Run acceptance check.

## 13. Troubleshooting

### Frontend Shows Empty Data

Check:

- `NEXT_PUBLIC_INSIGHTSYNC_API_BASE` points to Cloud Run, not localhost.
- Cloud Run URL is reachable from your browser.
- Backend `CORS_ALLOW_ORIGINS` includes the Vercel URL.
- `/api/prospects?limit=5` returns data.

### CORS Error In Browser

Set backend:

```env
CORS_ALLOW_ORIGINS=https://<your-vercel-domain>
```

Redeploy backend.

### Database Is Empty

Run:

```bash
python -m insightsync.backend.workflows.init_dev_backend
```

with `DATABASE_URL` pointing to Supabase.

Then check:

```bash
curl "<api-base>/api/dashboard/summary"
curl "<api-base>/api/prospects?limit=5"
```

### Cloud Run Cold Start

Free-style setup usually uses:

```text
min instances = 0
```

The first request after inactivity may be slow. For demos, open `/healthz` once before presenting.

### Live GLM Endpoint Times Out

Use:

```bash
--timeout-seconds 45
```

Keep:

```env
ENABLE_LLM_BRIEF_GENERATION=false
```

so normal pages do not call GLM on every load.

### API Key Auth Breaks Frontend

If backend has:

```env
API_KEYS=<some-key>
```

the frontend must send:

```text
X-API-Key: <some-key>
```

The formal frontend does not currently expose a production env var for that header. Leave `API_KEYS=` empty for the first demo deployment.

## 14. Security And Compliance Notes

This free deployment is only for demo/shared development.

Do not use it for:

- real customer data
- bank confidential documents
- production RM workflows
- regulated decisioning

Before any production-style deployment, add:

- proper authentication
- private networking or managed secrets
- audit logging and retention controls
- encrypted secret management
- stricter CORS
- rate limits
- data deletion procedure
- reviewed model governance

## 15. Useful Links

- Supabase pricing: https://supabase.com/docs/pricing
- Supabase database size: https://supabase.com/docs/guides/platform/database-size
- Vercel Hobby plan: https://vercel.com/docs/accounts/plans/hobby
- Vercel limits: https://vercel.com/docs/limits
- Cloud Run docs: https://cloud.google.com/run/docs
- Cloud Run pricing: https://cloud.google.com/run/pricing
- Render free services: https://render.com/free

