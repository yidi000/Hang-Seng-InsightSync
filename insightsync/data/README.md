# InsightSync Data Module

This folder is an independent data ingestion module for Project InsightSync.

## Scope

- Ingest market and report signals from:
  - HKMA Open API
  - ADB KIDB API
  - Hong Kong Census and Statistics Department retail sales / external merchandise trade API
  - KPMG Hong Kong Banking Outlook PDF
  - Guangdong Statistics Bureau webpages
  - InvestHK news feed (JSON + optional article text)
  - Hong Kong Government News (Business & Finance RSS/archive, with JSON/CSV snapshots)
  - HKEX predefined disclosure annual-report feed (PDF with optional Selenium fallback)
  - SZSE/CNINFO announcements (regular reports, temporary announcements, IPO-related disclosures)
  - Dongfang / Eastmoney connect-flow holdings rankings (AKShare fetch or CSV import)
  - Company directory seed and public profile URLs (website / LinkedIn / Facebook / X / Instagram / Wikipedia)
- Normalize records into a common schema.
- Persist cleaned data into SQLite for backend/agent consumption.
- Support one-off and interval scheduling modes.

## Data Layers

This module follows a 3-layer data architecture:

1. `intelligence_records` (Fact Layer)
- Raw + structured intelligence records from external sources.
- Examples: HKMA rate rows, HKMA press releases, ADB macro series snapshots, Guangdong table rows, KPMG report docs.

2. `trigger_signals` (Candidate Layer)
- Automatically extracted possible signals from facts.
- These are candidate signals, not final business conclusions.
- Examples: unusual macro movement candidates, cross-border related metric candidates, potential risk-related metric candidates.

3. `generated_insights` (Insight Layer)
- GenAI-validated insights generated from facts + candidate signals.
- Final output types: `opportunity`, `risk`, `action`.
- Current status: table is created, generation workflow not enabled yet.

## Install

```bash
python -m pip install -r insightsync/data/requirements.txt
```

## Run

Run once:

```bash
python -m insightsync.data --once
```

Run every 60 minutes:

```bash
python -m insightsync.data --interval-minutes 60
```

Run only selected sources:

```bash
python -m insightsync.data --sources hkma,adb --once
```

Run Hong Kong Census and Statistics Department retail / trade data:

```bash
python -m insightsync.data --sources censtatd --once
```

Run InvestHK only:

```bash
python -m insightsync.data --sources investhk --once
```

Run InvestHK with article text crawling enabled:

```bash
python -m insightsync.data --sources investhk --investhk-include-article-text --once
```

Run Hong Kong Government Business & Finance news (default last 3 months):

```bash
python -m insightsync.data --sources hkgov --once
```

Run Hong Kong Government news with explicit date range:

```bash
python -m insightsync.data --sources hkgov --hkgov-start-date 2026-01-01 --hkgov-end-date 2026-03-31 --once
```

Run HKEX annual reports only:

```bash
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-target-month 04 --once
```

Run HKEX with Selenium fallback enabled (for JS/blob pages):

```bash
python -m insightsync.data --sources hkex --hkex-target-year 2026 --hkex-use-selenium-fallback --once
```

Run SZSE CNINFO announcements (default last 180 days):

```bash
python -m insightsync.data --sources szse --once
```

Run SZSE CNINFO with explicit date range:

```bash
python -m insightsync.data --sources szse --szse-start-date 2026-01-01 --szse-end-date 2026-04-20 --once
```

Run company directory seed build (default segments: SME, Fintech, Cross-border):

```bash
python -m insightsync.data --sources company --once
```

Run company directory with public profile enrichment (website title and Wikipedia summary):

```bash
python -m insightsync.data --sources company --company-enable-enrichment --once
```

Run Dongfang / Eastmoney connect-flow direct fetch:

```bash
python -m insightsync.data --sources dongfang --dongfang-fetch --once
```

Run Dongfang / Eastmoney connect-flow CSV import:

```bash
python -m insightsync.data --sources dongfang --dongfang-csv-paths "C:\\data\\北向资金持股排行.csv,C:\\data\\沪股通持股排行.csv" --dongfang-snapshot-date 2026-05-01 --once
```

Run only market company sync (import HKEX/SZSE historical codes into `companies`):

```bash
python -m insightsync.data --skip-ingestion --sync-market-companies
```

Run historical company_id backfill for `intelligence_records` and `trigger_signals`:

```bash
python -m insightsync.data --skip-ingestion --backfill-company-ids
```

Dry-run company mapping (no DB update) with row limit:

```bash
python -m insightsync.data --skip-ingestion --sync-market-companies --backfill-company-ids --mapping-dry-run --mapping-limit 200
```

Useful InvestHK flags:

- `--investhk-language` (default: `zh-cn`)
- `--investhk-max-items` (default: `500`)
- `--investhk-request-timeout-seconds` (default: `30`)
- `--investhk-article-delay-seconds` (default: `0.3`)
- `--investhk-json-url` (override feed URL if needed)

Useful Hong Kong Census and Statistics Department flags:

- `--censtatd-language` (default: `en`)
- `--censtatd-no-full-series` (fetch default response window instead of full history)
- `--censtatd-request-timeout-seconds` (default: `60`)

Useful Hong Kong Government news flags:

- `--hkgov-language` (`en` or `tc`, default: `en`)
- `--hkgov-since-months` (default: `3`; `0` means latest RSS window)
- `--hkgov-since-days` (optional day-based window)
- `--hkgov-start-date` and `--hkgov-end-date` (explicit range, format: `YYYY-MM-DD`)
- `--hkgov-max-items` (default: `1000`)
- `--hkgov-filter-limit` (default: `50`)
- `--hkgov-no-require-geo-and-business` (relax GBA enterprise filter)
- `--hkgov-request-timeout-seconds` (default: `60`)

Useful HKEX flags:

- `--hkex-list-url` (override predefined documents list URL)
- `--hkex-target-year` (for example `2026`)
- `--hkex-target-month` (for example `04`)
- `--hkex-max-items` (default: `200`)
- `--hkex-use-selenium-fallback` (enable browser fallback for tricky pages)
- `--hkex-no-headless` (open browser UI for debugging)
- `--hkex-request-timeout-seconds` (default: `30`)
- `--hkex-download-wait-seconds` (default: `30`)
- `--hkex-page-wait-seconds` (default: `1.0`)

Useful SZSE/CNINFO flags:

- `--szse-days-back` (default: `180`)
- `--szse-start-date` and `--szse-end-date` (override days-back range, format: `YYYY-MM-DD`)
- `--szse-max-records` (default: `50000`)
- `--szse-page-size` (default: `30`)
- `--szse-delay-seconds` (default: `0.3`)
- `--szse-plate` (default: `sz`)
- `--szse-stock` (optional stock code filter)
- `--szse-tab-name` (default: `fulltext`)
- `--szse-request-timeout-seconds` (default: `15`)

Useful company-directory flags:

- `--company-seed-path` (optional path to custom company seed JSON)
- `--company-segments` (default: `sme,fintech,cross_border`)
- `--company-max-items` (default: `500`)
- `--company-enable-enrichment` (fetch website title and Wikipedia summary)
- `--company-request-timeout-seconds` (default: `15`)

Useful Dongfang / Eastmoney flags:

- `--dongfang-fetch` (fetch latest rankings directly via AKShare instead of importing existing CSV)
- `--dongfang-fetch-markets` (default: `northbound,shanghai_connect,shenzhen_connect`; run `southbound` separately)
- `--dongfang-fetch-retry` (default: `3`)
- `--dongfang-fetch-sleep-seconds` (default: `1.0`)
- `--dongfang-csv-paths` (comma-separated CSV paths exported from the notebook)
- `--dongfang-snapshot-date` (optional fallback date if CSV does not contain `日期`)
- `--dongfang-min-increase-value` (default: `0.0`; only larger inflows trigger increase-value signals)
- `--dongfang-min-holding-ratio` (default: `0.0`; only larger float-holding ratios trigger holding-depth signals)
- `--dongfang-top-n-rank-signal` (default: `20`; generate ranking signal for top N names)

Useful company-mapping flags:

- `--sync-market-companies` (discover companies from historical HKEX/SZSE records)
- `--backfill-company-ids` (map historical rows with empty `company_id`)
- `--mapping-dry-run` (preview mapping results without update)
- `--mapping-limit` (max rows per table, default: `0` means all)
- `--skip-ingestion` (run mapping operations only)

## Output

- DB: `insightsync/data/storage/insightsync.db`
- Raw files: `insightsync/data/storage/raw`

SQLite tables:
- `ingestion_runs`
- `intelligence_records`
- `trigger_signals`
- `client_one_view_timeline`
- `prospect_scores`
- `generated_insights`
- `companies`
- `company_mapping_audit`

## Current Database Status

As of 2026-04-07 (local run environment), `insightsync/data/storage/insightsync.db` has:

- `ingestion_runs`: 5
- `intelligence_records`: 177
- `trigger_signals`: 1334
- `client_one_view_timeline`: 183
- `prospect_scores`: 0
- `generated_insights`: 0

Notes:
- `trigger_signals` are candidate-level extracted signals.
- Final opportunities/risks/actions will be written into `generated_insights` after the GenAI reasoning module is added.
