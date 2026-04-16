# InsightSync Data Module

This folder is an independent data ingestion module for Project InsightSync.

## Scope

- Ingest market and report signals from:
  - HKMA Open API
  - ADB KIDB API
  - KPMG Hong Kong Banking Outlook PDF
  - Guangdong Statistics Bureau webpages
  - InvestHK news feed (JSON + optional article text)
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

Run InvestHK only:

```bash
python -m insightsync.data --sources investhk --once
```

Run InvestHK with article text crawling enabled:

```bash
python -m insightsync.data --sources investhk --investhk-include-article-text --once
```

Useful InvestHK flags:

- `--investhk-language` (default: `zh-cn`)
- `--investhk-max-items` (default: `500`)
- `--investhk-request-timeout-seconds` (default: `30`)
- `--investhk-article-delay-seconds` (default: `0.3`)
- `--investhk-json-url` (override feed URL if needed)

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
