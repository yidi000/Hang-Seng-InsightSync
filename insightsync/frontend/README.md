# InsightSync Frontend

This is the lightweight frontend MVP for the InsightSync banker-facing dashboard.
It is intentionally dependency-free for now, so it can be opened directly in a browser
or served by any static file server while the backend contract continues to mature.

## Run

From the repository root:

```bash
python -m http.server 5173 --directory insightsync/frontend
```

Open:

```text
http://127.0.0.1:5173
```

The default backend base URL is:

```text
http://127.0.0.1:8000
```

You can change it from the header input in the UI. The value is saved in browser
local storage as `INSIGHTSYNC_API_BASE`.

If `API_KEYS` is configured on the backend, set the key in the UI. The frontend
sends it as:

```text
X-API-Key: <key>
```

## Scope

Implemented screens:

- dashboard overview
- priority prospect list
- trigger signal explorer
- company explorer
- prospect detail with evidence, score audit, LLM review, and workflow update
- general/prospect-scoped copilot queries

The app consumes the FastAPI contract documented in:

```text
insightsync/docs/frontend-api-guide.md
```

## Notes

The app includes a small mock fallback dataset so frontend work can continue when
the backend is not running. The UI marks this as sample data and does not treat it
as scoring output.

