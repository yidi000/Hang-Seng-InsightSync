# InsightSync Database Snapshot Guide

Last updated: 2026-05-06

## Snapshot File

The current local backup is:

```text
backups/insightsync_postgres_2026-05-06_curated_snapshot.dump
```

It is a PostgreSQL custom-format dump created with `pg_dump -Fc`. It contains the
raw synchronized tables, parsed document tables, curated prospect layer, Copilot
conversation tables, and the current RAG index.

The API container's SQLite file is not the reliable artifact for this snapshot.
The current Docker Compose setup does not mount `/app/insightsync/data/storage`
to the host, and the API container was rebuilt after ingestion. The durable
snapshot for handoff is therefore the Postgres dump above.

## Restore

Start the Postgres service:

```bash
docker compose up -d postgres
```

Restore into an empty `insightsync` database:

```bash
docker compose exec -T postgres pg_restore \
  -U insightsync \
  -d insightsync \
  --clean \
  --if-exists \
  /path/inside/container/insightsync_postgres_2026-05-06_curated_snapshot.dump
```

If restoring from the host path, copy the dump into the Postgres container first:

```bash
docker cp backups/insightsync_postgres_2026-05-06_curated_snapshot.dump \
  hangseng55-postgres-1:/tmp/insightsync_snapshot.dump

docker compose exec postgres pg_restore \
  -U insightsync \
  -d insightsync \
  --clean \
  --if-exists \
  /tmp/insightsync_snapshot.dump
```

After restore, start the backend:

```bash
docker compose up -d api
```

## Data Layers

The database is organized into five layers.

### 1. Ingestion and Raw Intelligence

These tables store source-level data after crawler ingestion and SQLite-to-Postgres sync.

| Table | Rows | Purpose |
| --- | ---: | --- |
| `ingestion_runs` | 10 | One record per crawler run. |
| `companies` | 2,775 | Company master records and enrichment attributes. |
| `intelligence_records` | 30,470 | Raw normalized records from company, government, market, and research sources. |
| `trigger_signals` | 45,629 | Raw source-derived signals before curated normalization. |
| `client_one_view_timeline` | 11,475 | Timeline events normalized for entity/company views. |
| `company_mapping_audit` | 0 | Reserved for company mapping audit history. |

### 2. Parsed Document Layer

These tables store parser output used to make raw records searchable and structured.

| Table | Rows | Purpose |
| --- | ---: | --- |
| `parsing_runs` | 1 | Parser run metadata. |
| `parsed_documents` | 30,356 | One parsed document per source row/version. |
| `parsed_sections` | 276,788 | Section-level parsed text. |
| `parsed_tables` | 34 | Tables extracted from source documents. |
| `parsed_metrics` | 155 | Structured metrics extracted from source documents. |
| `parsed_risk_factors` | 21 | Risk factor extraction results. |
| `parsed_business_events` | 303 | Business event extraction results. |

### 3. Curated Prospect Layer

This is the primary product-facing data layer. It is built from raw and parsed tables.
Each curated evidence item is intended to have business meaning and a traceable source.

| Table | Rows | Purpose |
| --- | ---: | --- |
| `prospects` | 2,775 | Stable prospect objects. In the first version, `prospect_id = company_id`. |
| `prospect_evidence_items` | 117,448 | Business-usable evidence with source, title, summary, timestamp, and metadata. |
| `prospect_signals` | 45,629 | Curated growth, funding, expansion, policy, trade, cross-border, risk, hiring, and market-attention signals. |
| `prospect_scores` | 2,775 | Score, tier, reasons, recommended products, and recommended entry angle. |
| `market_opportunity_snapshots` | 184 | Aggregated market overview buckets by region, industry, size band, and signal type. |
| `data_quality_reports` | 1 | Snapshot-level quality metrics and known gaps. |

Current quality notes:

- Company mapping coverage is `18.2%`, below the first target of `60%`.
- Tier distribution is too concentrated: `A = 2,748`, `B = 19`, `D = 8`.
  The scoring thresholds or feature weights should be tightened before using the
  score as a real priority ranking.

### 4. RAG Layer

The current RAG index is curated-first. It is built from `prospect_evidence_items`,
not from the old raw fallback path.

| Table | Rows | Purpose |
| --- | ---: | --- |
| `rag_documents` | 20,000 | Search documents generated from curated evidence. |
| `rag_chunks` | 20,000 | Chunked text for retrieval. |
| `rag_embeddings` | 20,000 | Vector embeddings for retrieval. |
| `rag_retrieval_runs` | 0 | Reserved for retrieval telemetry. |

The current index intentionally covers the latest 20,000 curated evidence items.
The full curated evidence set has 117,448 rows. This limit was added to keep local
RAG rebuilds practical while still giving Copilot enough evidence for front-end
testing and demos.

The vector index is:

```text
idx_rag_embeddings_vector
USING hnsw (embedding vector_cosine_ops)
WITH (m='16', ef_construction='64')
```

Embedding configuration is currently separated from chat model configuration.
The snapshot uses the existing 1536-dimension embedding schema and fallback
embedding provider, so switching GLM chat settings does not require rebuilding
the vector table schema.

### 5. LLM and Copilot Layer

| Table | Rows | Purpose |
| --- | ---: | --- |
| `copilot_conversations` | 1 | Copilot conversation metadata. |
| `copilot_messages` | 2 | User and assistant messages. |
| `copilot_citations` | 5 | Evidence citations attached to assistant responses. |
| `generated_insights` | 0 | Reserved for persisted generated insights. |
| `llm_generation_runs` | 0 | Reserved for LLM generation run audit records. |

Current model configuration points to GLM-compatible chat settings:

```env
LLM_PROVIDER=bigmodel
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_CHAT_MODEL=glm-4.7-flash
EMBEDDING_PROVIDER=fallback
```

In the current local environment, `ENABLE_LLM_GENERATION=false`, so Copilot uses
evidence-grounded fallback responses unless an API key is provided and generation
is enabled.

## Important Indexes

The schema includes lookup, deduplication, ranking, and vector indexes.

### Raw and Timeline

- `idx_intelligence_lookup` on `intelligence_records(source, dataset, event_time DESC)`
- `idx_intelligence_entity_time` on `intelligence_records(entity, event_time DESC)`
- `uq_intelligence_record_hash` on `(source, dataset, record_key, content_hash)`
- `idx_trigger_lookup` on `trigger_signals(source, signal_type, event_time DESC)`
- `idx_trigger_entity_type_time` on `trigger_signals(entity, signal_type, event_time DESC)`
- `uq_trigger_signal_hash` on `(source, dataset, signal_key, row_hash)`
- `idx_timeline_lookup` on `client_one_view_timeline(company_id, entity, event_time DESC)`
- `uq_timeline_dedup_hash` on `(source, dedup_hash)`

### Parsed Documents

- `idx_parsed_documents_lookup` on `parsed_documents(source_table, source_id, parsed_at DESC)`
- `idx_parsed_documents_company` on `parsed_documents(company_id, source, dataset, parsed_at DESC)`
- `uq_parsed_document_source_version` on `(source_table, source_id, source_content_hash, parse_version)`

### Curated Prospects

- `idx_prospects_region_industry` on `prospects(region, industry, size_band)`
- `idx_prospect_evidence_lookup` on `prospect_evidence_items(prospect_id, evidence_type, event_time DESC)`
- `idx_prospect_evidence_source` on `prospect_evidence_items(source, dataset, event_time DESC)`
- `uq_prospect_evidence_source_hash` on `(source_table, source_id, content_hash)`
- `idx_prospect_signals_lookup` on `prospect_signals(prospect_id, signal_subtype, event_time DESC)`
- `idx_prospect_scores_rank` on `prospect_scores(score DESC, tier)`
- `uq_market_snapshot_bucket` on `(snapshot_date, region, industry, size_band, signal_type)`

### RAG and Copilot

- `idx_rag_documents_metadata` on `rag_documents(entity, source, dataset, event_time DESC)`
- `uq_rag_document_source_hash` on `(source_table, source_id, content_hash)`
- `idx_rag_chunks_document` on `rag_chunks(document_id, chunk_index)`
- `idx_rag_embeddings_vector` HNSW vector cosine index on `rag_embeddings.embedding`
- `idx_copilot_messages_conversation` on `copilot_messages(conversation_id, created_at)`
- `idx_copilot_citations_message` on `copilot_citations(message_id)`

## Product Coverage

The snapshot is sufficient for first-pass demos of:

- Market Opportunity Overview: `market_opportunity_snapshots`, aggregate signal counts, source evidence.
- Priority Prospect List: `prospects` joined with `prospect_scores`.
- Prospect Intelligence: prospect profile, evidence, timeline, and signals.
- Trigger Signals: `prospect_signals` and evidence-backed signal detail.
- Copilot: `/api/copilot/chat` over curated evidence with citations.

Known limitations before production use:

- Company mapping coverage needs improvement.
- Scoring produces too many A-tier prospects and should be recalibrated.
- RAG currently indexes 20,000 of 117,448 curated evidence rows.
- SZSE six-month ingestion was not included in this snapshot because the local run
  was too slow for the first refresh pass.
- HKEX did not contribute meaningful records in the latest run.

