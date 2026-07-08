import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
from app.schemas import Task, TasksResponse
from app.services.task_parser import extract_tasks_hybrid
from app.services import gmail_client

# Frontend directory (sibling of backend/)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
# Synced Gmail snapshot (real tasks pulled read-only)
GMAIL_CACHE = Path(__file__).resolve().parent / "data" / "gmail_tasks.json"

app = FastAPI(title="Gmail Tasks API", version="0.1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mock Gmail data (replace with real Gmail API calls later)
MOCK_EMAILS = [
    {
        "id": "email_1",
        "sender": "design@team.com",
        "subject": "TODO: Review design mockups",
        "body": "Hi, we have new dashboard UI mockups ready for feedback. Please review by tomorrow. Thanks!",
        "date": datetime.now() - timedelta(days=1),
    },
    {
        "id": "email_2",
        "sender": "docs@team.com",
        "subject": "TASK: Update API documentation",
        "body": "We need to update the API docs with examples for the new endpoints. This is medium priority and should be done by next week.",
        "date": datetime.now() - timedelta(days=2),
    },
    {
        "id": "email_3",
        "sender": "engineering@team.com",
        "subject": "URGENT: Fix critical bug in auth",
        "body": "[ACTION] Session token expiry handling not working correctly in production. This needs immediate attention. Due: 2026-07-08",
        "date": datetime.now(),
    },
    {
        "id": "email_4",
        "sender": "product@team.com",
        "subject": "TODO: Prepare Q3 roadmap",
        "body": "Need to compile all feature requests and create timelines for Q3. Please have this ready by 2026-07-15.",
        "date": datetime.now() - timedelta(days=3),
    },
    {
        "id": "email_5",
        "sender": "manager@team.com",
        "subject": "Schedule team meeting",
        "body": "Let's plan the sprint retrospective. Can you set up the meeting for next week?",
        "date": datetime.now() - timedelta(days=5),
    },
    {
        "id": "email_6",
        "sender": "devops@team.com",
        "subject": "URGENT: Database performance audit needed",
        "body": "We're seeing slow queries in production. Please analyze and optimize. Due: 2026-07-10. High priority.",
        "date": datetime.now(),
    },
    {
        "id": "email_7",
        "sender": "qa@team.com",
        "subject": "TODO: Write unit tests for payment module",
        "body": "[TASK] Cover all new payment module functions with comprehensive unit tests. Needed by 2026-07-16.",
        "date": datetime.now() - timedelta(days=4),
    },
    {
        "id": "email_8",
        "sender": "sales@team.com",
        "subject": "Client feedback review needed",
        "body": "Low priority: Summarize and categorize feature requests from recent client calls. Due: 2026-07-25",
        "date": datetime.now() - timedelta(days=6),
    },
]


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


def _tasks_from_cache() -> list[Task] | None:
    """Load the synced real-Gmail snapshot, if present."""
    if not GMAIL_CACHE.exists():
        return None
    data = json.loads(GMAIL_CACHE.read_text())
    return [Task(**t) for t in data.get("tasks", [])]


def _tasks_from_mock() -> list[Task]:
    """Extract tasks from the built-in sample emails."""
    all_tasks = []
    for email in MOCK_EMAILS:
        all_tasks.extend(extract_tasks_hybrid(
            email_subject=email["subject"],
            email_body=email["body"],
            sender=email["sender"],
            email_date=email["date"],
            email_id=email["id"],
        ))
    seen = set()
    deduped = []
    for task in all_tasks:
        if task.id not in seen:
            seen.add(task.id)
            deduped.append(task)
    return deduped


@app.get("/api/tasks", response_model=TasksResponse)
def get_tasks():
    """
    Return pending tasks. Source precedence:
      1. Live Gmail (read-only) when OAuth is configured (credentials/token present)
      2. Synced Gmail snapshot (backend/app/data/gmail_tasks.json) — real tasks
      3. Built-in mock emails (demo fallback)
    """
    tasks: list[Task] | None = None

    if gmail_client.is_configured():
        try:
            tasks = gmail_client.fetch_tasks()
        except Exception as e:
            print(f"Live Gmail fetch failed, falling back to cache/mock: {e}")

    if not tasks:
        tasks = _tasks_from_cache()

    if not tasks:
        tasks = _tasks_from_mock()

    return TasksResponse(tasks=tasks, total=len(tasks))


@app.get("/")
def serve_dashboard():
    """Serve the dashboard frontend at the root URL."""
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Dashboard frontend not found. See README."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
