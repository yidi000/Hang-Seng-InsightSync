# Backend

## Purpose

The backend serves as the system layer between the data module and the frontend application. It is responsible for turning normalized market intelligence into stable APIs, business logic, and AI-powered insights for prospecting and client intelligence use cases.

## Planned Responsibilities

- expose frontend-facing APIs for prospecting, company detail, dashboard, and signals
- consume processed outputs from the `insightsync/data` module
- manage business logic such as filtering, sorting, aggregation, and response shaping
- integrate the AI capability layer for signal extraction, insight generation, and explanation
- persist production-ready data in a backend database for application use

## Recommended Architecture

The backend will follow a layered monolithic architecture.

### 1. API Layer
Handles REST endpoints for frontend and internal workflows.

Examples:
- `GET /api/prospects`
- `GET /api/companies/{id}`
- `GET /api/signals`
- `GET /api/dashboard/overview`
- `POST /internal/workflows/extract-signals`

### 2. Service Layer
Contains business logic for:
- prospect ranking and listing
- company detail assembly
- trigger signal retrieval
- dashboard metrics
- insight orchestration

### 3. Repository / Data Access Layer
Responsible for reading and writing application data from the backend database.

### 4. AI Capability Layer
Responsible for tasks that involve unstructured text, including:
- signal extraction from reports and news
- company insight generation
- explanation of prospect priority

### 5. Storage Layer
Backend production database for serving APIs and application workflows.

## Data Integration Plan

The current `insightsync/data` module already ingests external sources and stores normalized outputs in SQLite.

Recommended integration path:

1. data module continues to ingest and normalize source data
2. backend reads or syncs selected tables from SQLite
3. backend stores application-ready data in PostgreSQL
4. frontend consumes data only through backend APIs

This allows the data module to remain the upstream intelligence pipeline, while the backend becomes the stable application service layer.

## Database Direction

### Current upstream storage
- SQLite
- suitable for local ingestion, testing, and intermediate storage

### Recommended backend primary database
- PostgreSQL
- suitable for API serving, concurrent access, filtering, joins, and future deployment

## Suggested Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migration:** Alembic
- **Data Processing Support:** pandas
- **AI Layer:** LLM API integration + structured output parser
- **Scheduling:** APScheduler or cron
- **Containerization:** Docker / Docker Compose

## Suggested Folder Structure

```text
backend/
├── api/
├── services/
├── repositories/
├── db/
├── schemas/
├── ai/
├── workflows/
└── utils/
