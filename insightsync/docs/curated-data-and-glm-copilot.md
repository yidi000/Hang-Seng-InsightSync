# Curated Data and GLM Copilot Runbook

This runbook describes the backend flow for the prospecting MVP.

## Data Window

Initial rebuild window:

- Start: `2025-11-05`
- End: `2026-05-05`

## Rebuild Order

Run data ingestion into SQLite:

```bash
python -m insightsync.data.rebuild_prospecting_window
python -m insightsync.data.rebuild_prospecting_window --execute
```

Equivalent manual commands:

```bash
python -m insightsync.data --sources company --company-enable-enrichment --once
python -m insightsync.data --sources hkgov --hkgov-start-date 2025-11-05 --hkgov-end-date 2026-05-05 --once
python -m insightsync.data --sources szse --szse-start-date 2025-11-05 --szse-end-date 2026-05-05 --once
python -m insightsync.data --sources investhk --investhk-include-article-text --once
python -m insightsync.data --sources dongfang --dongfang-fetch --once
python -m insightsync.data --sources censtatd,guangdong,hkma,adb,kpmg --once
```

Run HKEX month by month for November 2025 through May 2026:

```bash
python -m insightsync.data --sources hkex --hkex-target-year 2025 --hkex-target-month 11 --once
python -m insightsync.data --sources hkex --hkex-target-year 2025 --hkex-target-month 12 --once
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-target-month 01 --once
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-target-month 02 --once
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-target-month 03 --once
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-target-month 04 --once
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-target-month 05 --once
```

Run mapping and parsing:

```bash
python -m insightsync.data --skip-ingestion --sync-market-companies --backfill-company-ids
python -m insightsync.data --skip-ingestion --run-parsing
```

Sync into Postgres and build serving layers:

```bash
alembic upgrade head
python -m insightsync.backend.workflows.sync_from_sqlite --full
python -m insightsync.backend.workflows.build_curated_prospects
python -m insightsync.backend.workflows.build_rag_index --full
```

## GLM Configuration

```env
LLM_PROVIDER=bigmodel
LLM_API_KEY=<your-bigmodel-key>
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_CHAT_MODEL=glm-4.7-flash
LLM_MIN_INTERVAL_SECONDS=2
LLM_MAX_RETRIES=3
ENABLE_LLM_GENERATION=true
EMBEDDING_PROVIDER=fallback
```

`glm-4.7-flash` is used for structured extraction, prospect summaries, entry angles, and Copilot answers. Embeddings stay on the existing 1536-dimensional path or fallback provider for this phase.
The GLM chat provider is throttled in-process and retries `429` rate-limit responses with a short backoff before returning a controlled `LLM_RATE_LIMITED` error.

## Frontend Integration

Use these endpoints:

- `GET /api/dashboard/summary`
- `GET /api/dashboard/market-overview`
- `GET /api/dashboard/priority-prospects`
- `GET /api/dashboard/trigger-signals`
- `GET /api/prospects`
- `GET /api/prospects/{prospectId}`
- `GET /api/prospects/{prospectId}/signals`
- `GET /api/prospects/{prospectId}/timeline`
- `GET /api/prospects/{prospectId}/evidence`
- `GET /api/prospects/{prospectId}/insights`
- `GET /api/metadata/filters`
- `POST /api/copilot/chat`
- `GET /api/copilot/conversations/{conversationId}`
- `POST /api/copilot/prospect/{prospectId}/brief`
- `POST /api/copilot/prospect/{prospectId}/questions`
