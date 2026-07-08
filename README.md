# Gmail Tasks Dashboard

Interactive dashboard extracting pending tasks from Gmail inbox with priority alerts and due dates. Modern glass-morphism interface, read-only email access.

## Quick Start

Two commands. The backend serves both the API and the dashboard on one port.

### 1. Install dependencies

```bash
cd backend && uv sync && cd ..
```

### 2. Start the server

```bash
uv run --project backend python -m uvicorn app.main:app --port 8000 --reload
```

Or use Claude Code launch: start the `backend` config from the Launch panel.

### 3. Open the dashboard

Open **http://localhost:8000/** in any browser.

- `GET /` → dashboard UI ([frontend/index.html](frontend/index.html))
- `GET /api/tasks` → JSON list of extracted tasks
- `GET /health` → status check

That's it. Refresh button re-fetches from the backend. Filters, search, task
detail modal, and completion toggle all work client-side.

## Gmail data — three sources (auto-selected)

`GET /api/tasks` picks the first available source, in order:

1. **Live Gmail** (read-only) — when OAuth is configured (see below).
2. **Synced snapshot** — real tasks in [backend/app/data/gmail_tasks.json](backend/app/data/gmail_tasks.json),
   pulled read-only from the inbox. This ships populated, so the dashboard shows
   real tasks with zero setup.
3. **Mock emails** — demo fallback if neither above exists.

Everything is **read-only**: no email is ever sent, modified, or deleted.

### Connect Gmail for live refresh (optional)

One-time setup so the Refresh button pulls new mail live:

1. Install the Gmail deps: `cd backend && uv sync --extra gmail`
2. Google Cloud Console → enable the Gmail API → create an OAuth client
   (application type: **Desktop app**).
3. Download the client JSON to `backend/credentials.json`.
4. Restart the server and open the dashboard. The first request opens a browser
   consent screen (scope: `gmail.readonly`). A token caches to
   `backend/token.json`; subsequent refreshes are silent.

`credentials.json` and `token.json` are git-ignored — never commit them.

To re-sync the snapshot instead (no OAuth), ask Claude Code to refresh it via the
connected Gmail connector.

## Architecture

```
┌─────────────────────────────────────┐
│   React Dashboard Artifact           │
│   (browser-based UI)                │
└────────────┬────────────────────────┘
             │ HTTP fetch
             ↓
┌─────────────────────────────────────┐
│   FastAPI Backend (port 8000)       │
│   ├── GET /api/tasks                │
│   ├── Task extraction (regex+Claude)│
│   └── Gmail integration (MCP/API)   │
└─────────────────────────────────────┘
             │
             ↓
    ┌────────────────┐
    │  Gmail Inbox   │
    │  (read-only)   │
    └────────────────┘
```

## Task Extraction Logic

**Hybrid approach (regex + Claude fallback):**

1. **Regex (fast)**: Scan email for task indicators
   - Keywords: `TODO`, `TASK`, `[ACTION]`, etc.
   - Priority detection: `URGENT`/`ASAP`/`CRITICAL` → High, `IMPORTANT` → Medium, default Low
   - Due date extraction: regex for "due [date]", "deadline:", fallback to email date + 7 days

2. **Claude AI (fallback)**: If regex finds 0 tasks but email looks task-like
   - Sends email to Claude with extraction prompt
   - Returns structured JSON (title, priority, due_date)
   - Requires `ANTHROPIC_API_KEY` in `.env`

3. **Deduplication**: By task title + sender hash

## Files

```
backend/
├── pyproject.toml              # Dependencies
├── .env.example                # Config template
└── app/
    ├── __init__.py
    ├── main.py                 # FastAPI app, routes, mock data
    ├── schemas.py              # Pydantic models
    └── services/
        ├── __init__.py
        └── task_parser.py      # Extraction logic (regex + Claude)
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `ANTHROPIC_API_KEY` - For Claude task extraction fallback (optional)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - For Gmail OAuth (if using direct API, future)

## Testing

```bash
# Check if backend is running
curl http://localhost:8000/health

# Fetch tasks
curl http://localhost:8000/api/tasks | jq .
```

## Next Steps

- [ ] Wire real Gmail via MCP or OAuth
- [ ] Update dashboard artifact to call real backend API
- [ ] Implement task persistence (if needed)
- [ ] Deploy backend (serverless or VM)
