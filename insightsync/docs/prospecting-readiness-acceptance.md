# Prospecting Readiness Acceptance

Run these checks in order. The business-trustworthy checks must pass before the demo-ready checks are accepted.

## Business-Trustworthy Checks

Rebuild curated data and inspect the quality report:

```bash
docker compose exec api python -m insightsync.backend.workflows.build_curated_prospects
```

Validate the latest quality report:

```bash
docker compose exec api python -c "
from sqlalchemy import text
from insightsync.backend.db.session import SessionLocal

db = SessionLocal()
quality = db.execute(
    text('select report_json from data_quality_reports order by created_at desc limit 1')
).scalar_one()
print(quality)
assert quality['company_mapping']['coverage'] >= 0.6
assert quality['company_mapping']['raw_coverage'] >= 0
tiers = {
    row[0]: row[1]
    for row in db.execute(text('select tier, count(*) from prospect_scores group by tier'))
}
print(tiers)
assert len(tiers) >= 3
top = db.execute(
    text('select reasons_json from prospect_scores order by score desc limit 20')
).all()
assert all(row[0] for row in top)
db.close()
"
```

Expected:

- `company_mapping.coverage >= 0.6` using the company-mappable denominator.
- `company_mapping.raw_coverage` is reported separately for transparency.
- At least three score tiers are populated.
- Top 20 prospects have non-empty score reasons.

## RAG and Retrieval Checks

Rebuild the curated-first RAG index:

```bash
docker compose exec api python -m insightsync.backend.workflows.build_rag_index --full
```

Check that RAG documents are built from curated evidence:

```bash
docker compose exec api python -c "
from sqlalchemy import text
from insightsync.backend.db.session import SessionLocal

db = SessionLocal()
rows = db.execute(
    text('select source_table, count(*) from rag_documents group by source_table order by count(*) desc')
).all()
print(rows)
assert rows
assert rows[0][0] == 'prospect_evidence_items'
db.close()
"
```

Expected:

- `rag_documents.source_table` is `prospect_evidence_items`.
- `rag_embeddings` has rows for the configured embedding model.

## Demo-Ready API Checks

Dashboard endpoints:

```bash
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/summary
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/market-overview
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/priority-prospects
docker compose exec api curl -sS http://127.0.0.1:8000/api/dashboard/trigger-signals
```

Expected:

- Summary returns lead pool, high-priority count, cross-border count, financing signals, and last updated timestamp.
- Market overview chart items include bounded `drilldown`.
- Priority prospects include `scoreReasons` and `evidenceIds`.
- Trigger signals include source, event time, type, subtype, and signal text.

Copilot endpoint:

```bash
docker compose exec api curl -sS -X POST http://127.0.0.1:8000/api/copilot/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Which prospects show cross-border opportunity?","context":"global","filters":{},"topK":5}'
```

Expected:

- Evidence-backed questions return `status: ok` with citation cards.
- No-evidence questions return `status: insufficient_evidence`.
- Invalid GLM JSON or invalid citations are not accepted as normal answers.

## Focused Test Suites

Run backend readiness tests:

```bash
docker compose exec api env PYTHONPATH=/app pytest \
  insightsync/backend/tests/test_prospect_scoring.py \
  insightsync/backend/tests/test_company_mapping_quality.py \
  insightsync/backend/tests/test_curated_builder.py \
  insightsync/backend/tests/test_dashboard_readiness_api.py \
  insightsync/backend/tests/test_copilot_retrieval.py \
  insightsync/backend/tests/test_copilot_glm_gate.py \
  insightsync/backend/tests/test_openai_provider.py \
  -q
```

Expected:

- All tests pass.

## GLM Configuration Check

Confirm runtime settings:

```bash
docker compose exec api python -c "
from insightsync.backend.core.config import get_settings
s = get_settings()
print('LLM_PROVIDER', s.llm_provider)
print('LLM_BASE_URL', s.llm_base_url)
print('LLM_CHAT_MODEL', s.llm_chat_model)
print('LLM_MIN_INTERVAL_SECONDS', s.llm_min_interval_seconds)
print('LLM_MAX_RETRIES', s.llm_max_retries)
print('ENABLE_LLM_GENERATION', s.enable_llm_generation)
print('LLM_API_KEY', 'SET' if s.llm_api_key else 'MISSING')
print('EMBEDDING_PROVIDER', s.embedding_provider)
"
```

Expected for live GLM testing:

- `LLM_PROVIDER = bigmodel`
- `LLM_CHAT_MODEL = glm-4.7-flash`
- `LLM_MIN_INTERVAL_SECONDS = 2`
- `LLM_MAX_RETRIES = 3`
- `LLM_API_KEY = SET`
- `ENABLE_LLM_GENERATION = true`
- `EMBEDDING_PROVIDER = fallback` or the configured 1536-dimension embedding provider.

## Acceptance Order

1. Pass business-trustworthy checks.
2. Pass RAG and retrieval checks.
3. Pass demo-ready API checks.
4. Pass focused test suites.
5. Run live GLM Copilot smoke tests after `ENABLE_LLM_GENERATION=true`.
