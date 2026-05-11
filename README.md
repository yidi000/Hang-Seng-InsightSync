# Hang Seng InsightSync

InsightSync is a GenAI-driven actionable intelligence platform for Hang Seng Bank commercial banking scenarios.
It combines company reports, company-related signals, and external market intelligence to support faster and more consistent RM decisions across prospecting, relationship deepening, and risk monitoring.

PRD framework UI demo: https://v0-hang-seng.vercel.app/

## Quick Start (Docker)

Docker Compose is the recommended way to run the backend locally because it provides PostgreSQL with pgvector.

```bash
cp .env.example .env
docker compose up --build
```

In another terminal, initialize the backend database and load the bundled demo SQLite snapshot:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m insightsync.backend.workflows.sync_from_sqlite --full
docker compose exec api python -m insightsync.backend.workflows.build_rag_index --full
```

Verify the service:

```bash
curl "http://127.0.0.1:8000/healthz"
curl "http://127.0.0.1:8000/api/companies?limit=20"
curl "http://127.0.0.1:8000/api/prospects?limit=20"
curl "http://127.0.0.1:8000/api/signals?limit=20"
curl "http://127.0.0.1:8000/api/timeline?limit=20"
curl "http://127.0.0.1:8000/api/dashboard/overview"
curl "http://127.0.0.1:8000/api/rag/index/status"
```

RAG insight generation is evidence-gated. Without `OPENAI_API_KEY`, the system uses deterministic local fallback embeddings and fallback explanations so the demo remains runnable.

The bundled demo SQLite snapshot is intentionally committed at `insightsync/data/storage/demo/insightsync_demo.db`. Current snapshot coverage:

- 19 company profiles
- 248 intelligence records
- 1,394 trigger signals
- 254 timeline events
- 240 parsed documents
- 4 parsed metrics, 22 parsed risk factors, and 8 parsed business events
- 0 generated insights by default; generated insights are created after RAG/LLM calls with validated citations

## Local Development Without Docker

Install dependencies:

```bash
python -m pip install -r insightsync/data/requirements.txt -r insightsync/backend/requirements.txt
```

Run PostgreSQL locally with pgvector enabled, then configure `.env`:

```bash
cp .env.example .env
```

Run migrations, sync data, build the RAG index, and start the API:

```bash
alembic upgrade head
python -m insightsync.backend.workflows.sync_from_sqlite --full
python -m insightsync.backend.workflows.build_rag_index --full
uvicorn insightsync.backend.main:app --reload --port 8000
```

Useful backend endpoints:

- `GET /healthz`
- `GET /api/companies`
- `GET /api/companies/{company_id}`
- `GET /api/prospects`
- `GET /api/prospects/{prospect_id}`
- `GET /api/prospects/{prospect_id}/evidence`
- `GET /api/prospects/{prospect_id}/brief`
- `GET /api/prospects/{prospect_id}/copilot`
- `GET /api/prospects/{prospect_id}/review`
- `POST /api/prospects/{prospect_id}/question`
- `GET /api/signals`
- `GET /api/timeline`
- `GET /api/dashboard/overview`
- `GET /api/rag/index/status`
- `POST /api/rag/query`
- `POST /api/insights/generate`

## Business Objective

The platform is designed to answer three core business questions:

1. Where are the highest-value client acquisition opportunities?
2. What relationship deepening opportunities exist in the current portfolio?
3. Which risk and attrition signals should be flagged earlier?

## Current Scope and Status

Current implementation focus is the data and backend intelligence foundation.

- Implemented: multi-source ingestion, normalization, signal extraction, SQLite persistence, scheduler loop
- Implemented: document parsing for PDF/text/HTML/JSON/CSV/XBRL paths, including structured metrics, risks, business events, and management discussion extraction
- Implemented: SQLite to PostgreSQL sync, RAG indexing, OpenAI-compatible AI provider, evidence-gated RAG Q&A, and generated insight persistence when citations validate
- Implemented: company and prospect APIs, dashboard summary APIs, prospect evidence/brief/copilot/review payloads, and frontend API handover guide
- Implemented: prospect scorecard metadata, linkage-quality metrics, and governance flags to separate business score from evidence confidence
- Added: multilingual parsing evaluation samples covering English, simplified Chinese, traditional Chinese, and Cantonese-style traditional Chinese text
- Still maturing: score calibration, company identity resolution, generated insight evaluation, frontend dashboard implementation, and production handover runbooks

## Data Sources Integrated

- HKMA Open API (exchange rates, interbank rates, composite interest rates, press releases)
- ADB KIDB (macro indicator time series)
- KPMG Hong Kong Banking Outlook (PDF artifact ingestion)
- Guangdong Statistics Bureau (CSV/table extraction)
- InvestHK news feed (policy, expansion, financing, and market-news signals)
- Hong Kong Government News (news.gov.hk Business & Finance, JSON/CSV snapshots)
- HKEX disclosure feed for listed-company annual reports (PDF collection)
- SZSE/CNINFO announcement feed (A-share and partial HK-listed company disclosures with PDF links)
- Project structure can support additional sources such as Yahoo Finance (next integration target)

## Data Pipeline Overview

The pipeline follows four stages:

1. Ingestion
- Collect from configured external sources (batch run or scheduled loop)

2. Standardization
- Normalize records into a unified schema with consistent keys, timestamps, and metadata

3. Signal Layer
- Generate candidate signals (growth, financing, cross-border, risk) from normalized facts

4. Output Layer
- Persist timeline, signals, parsed evidence, RAG index artifacts, and generated insight artifacts for API/copilot consumption

Data is organized into three logical layers:

- Fact layer: `intelligence_records`
- Candidate signal layer: `trigger_signals`
- Parsed evidence layer: `parsed_documents`, `parsed_metrics`, `parsed_risk_factors`, `parsed_business_events`
- Company/prospect serving layer: `/api/companies`, `/api/prospects`, `/api/dashboard/*`
- Insight layer: `generated_insights`

## Repository Structure

```text
Hang-Seng-InsightSync/
	README.md                  # Repository-level documentation
	insightsync/
		README.md                # Package/module-level notes
		backend/                 # FastAPI backend, RAG, company/prospect services
		frontend/                # Frontend application area
		docs/                    # Architecture, scoring, and frontend API handover docs
		infrastructure/          # Deployment placeholder
		data/                    # Ingestion, parsing persistence, demo SQLite snapshot
			cli.py
			connectors/
			pipeline/
			storage/
```

## Quick Start (Data Module Only)

From the repository root:

```bash
python -m pip install -r insightsync/data/requirements.txt
python -m insightsync.data --once
```

Run with scheduler:

```bash
python -m insightsync.data --interval-minutes 60
```

Run selected sources only:

```bash
python -m insightsync.data --sources hkma,adb,investhk --once
```

Run HKEX annual-report collection only:

```bash
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-target-month 04 --once
```

Run Hong Kong Government Business & Finance news collection (default last 3 months):

```bash
python -m insightsync.data --sources hkgov --once
```

Run SZSE/CNINFO announcement collection (default last 180 days):

```bash
python -m insightsync.data --sources szse --once
```

Run local-only company seed refresh and mapping without external network calls:

```bash
python -m insightsync.data --sources company --once
python -m insightsync.data --skip-ingestion --sync-market-companies --backfill-company-ids
```

Run multilingual parsing evaluation:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ENABLE_LLM_GENERATION=false python -m pytest insightsync/backend/tests/test_multilingual_parsing_eval.py -q
```

Run company identity/linkage evaluation:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest insightsync/data/tests/test_company_identity_linkage_eval.py -q
```

## Collaboration Workflow

1. Sync main branch

```bash
git checkout main
git pull origin main
```

2. Work in your collaboration branch

```bash
git checkout collab_li_ruisen
```

3. Commit and push

```bash
git add -A
git commit -m "feat: <summary>"
git push
```

4. Open a PR to `main`

- https://github.com/yidi000/Hang-Seng-InsightSync/pull/new/collab_li_ruisen

## Recommended Next Milestones

1. Calibrate prospect scoring and linkage rules with labeled examples and RM/product review
2. Expand multilingual evaluation cases for annual reports, announcements, market news, and Cantonese-style business text
3. Improve company identity resolution across English, simplified Chinese, traditional Chinese, stock codes, aliases, and subsidiaries
4. Add metadata/filter APIs and prospect insight history endpoints requested by frontend integration
5. Add governance, evaluation logs, model/prompt configuration records, and backend handover runbooks

## Notes

- Keep PRD/business requirement documents under `insightsync/docs/` (for example `insightsync/docs/prd/`).
- Keep repository README focused on engineering reality and collaboration setup.
