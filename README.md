# Hang Seng InsightSync

InsightSync is a GenAI-driven actionable intelligence platform for Hang Seng Bank commercial banking scenarios.
It combines company-related signals and external market intelligence to support faster and more consistent RM decisions across prospecting, relationship deepening, and risk monitoring.

PRD framework UI demo: https://v0-hang-seng.vercel.app/


## Business Objective

The platform is designed to answer three core business questions:

1. Where are the highest-value client acquisition opportunities?
2. What relationship deepening opportunities exist in the current portfolio?
3. Which risk and attrition signals should be flagged earlier?

## Current Scope and Status

Current implementation focus is the data foundation.

- Implemented: multi-source ingestion, normalization, signal extraction, SQLite persistence, scheduler loop
- Partially implemented: data model for prospect scores and generated insights (structure ready)
- Placeholder modules: backend API, frontend dashboard, infrastructure deployment, handover docs

## Data Sources Integrated

- HKMA Open API (exchange rates, interbank rates, composite interest rates, press releases)
- ADB KIDB (macro indicator time series)
- KPMG Hong Kong Banking Outlook (PDF artifact ingestion)
- Guangdong Statistics Bureau (CSV/table extraction)
- InvestHK news feed (policy, expansion, financing, and market-news signals)
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
- Persist timeline, signals, and future insight artifacts for dashboard/API/copilot consumption

Data is organized into three logical layers:

- Fact layer: `intelligence_records`
- Candidate signal layer: `trigger_signals`
- Insight layer: `generated_insights` (schema ready, generation workflow to be expanded)

## Repository Structure

```text
Hang-Seng-InsightSync/
	README.md                  # Repository-level documentation
	insightsync/
		README.md                # Package/module-level notes
		backend/                 # Backend API placeholder
		frontend/                # Frontend app placeholder
		docs/                    # Architecture and handover docs placeholder
		infrastructure/          # IaC and deployment placeholder
		data/                    # Implemented ingestion + signal pipeline
			cli.py
			connectors/
			pipeline/
			storage/
```

## Quick Start (Data Module)

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

1. Implement prospect scoring and ranking logic
2. Implement generated insight reasoning with evidence linkage
3. Build backend APIs for prospect list, timeline, and risk signals
4. Build frontend dashboard and RM copilot interaction
5. Add governance, evaluation, and handover documentation

## Notes

- Keep PRD/business requirement documents under `insightsync/docs/` (for example `insightsync/docs/prd/`).
- Keep repository README focused on engineering reality and collaboration setup.
