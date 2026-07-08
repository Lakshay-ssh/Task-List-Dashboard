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

### 4. Wire Real Gmail (Future)

#### Option A: MCP Connector (Recommended)
1. Authorize `plugin:small-business:gmail` via Claude Code MCP settings
2. Update `backend/app/main.py` to call Gmail MCP tools instead of mock data
3. Backend will fetch real emails and extract tasks

#### Option B: Direct Gmail API
1. Create OAuth 2.0 credentials in Google Cloud Console
2. Add credentials to `backend/.env`
3. Implement OAuth flow in `backend/app/services/gmail_client.py`
4. Call Gmail API directly from backend

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
