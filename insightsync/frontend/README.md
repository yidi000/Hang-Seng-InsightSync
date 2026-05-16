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
- Prospect list and priority views
- Signal feed
- Prospect-scoped Copilot questions
- Global RAG Copilot questions
- Persisted prospect workflow updates

The previous static prototype is retained under `legacy-static/` for reference only.
