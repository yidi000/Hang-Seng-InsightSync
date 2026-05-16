# InsightSync Frontend

This is the formal InsightSync frontend application.

## Stack

- Next.js
- React
- TypeScript
- Tailwind CSS v4
- Radix/shadcn-style UI primitives
- Recharts
- lucide-react

## Local Setup

From `insightsync/frontend`:

```bash
cp .env.example .env.local
npm install
npm run dev
```

Then open:

```text
http://127.0.0.1:3000
```

The frontend expects the backend API at:

```text
http://127.0.0.1:8000
```

Override that with `NEXT_PUBLIC_INSIGHTSYNC_API_BASE` in `.env.local` if needed.

## Current Backend Integration

- Dashboard summary and market overview
- Metadata-backed filters for industries, regions, signal types, and sources
- Prospect list and priority views
- Prospect detail with company profile, evidence bundle, score audit, decision answers, advisory LLM review, timeline, generated insights, and workflow state
- Signal feed with company-brief linkage
- Prospect-scoped Copilot questions
- Global RAG Copilot questions
- Persisted prospect workflow updates

## Acceptance Check

With backend and frontend running:

```bash
python -m insightsync.backend.workflows.acceptance_check --api-base http://127.0.0.1:8000 --frontend-base http://127.0.0.1:3000 --strict
```

Use `--include-review --include-rag --timeout-seconds 45` when live GLM endpoints are enabled and should be checked too.

The previous static prototype is retained under `legacy-static/` for reference only.
