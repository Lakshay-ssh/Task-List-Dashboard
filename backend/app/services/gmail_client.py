"""
Live Gmail connection via the Gmail API (read-only).

This is the OPTIONAL live-refresh path. It is only used when OAuth credentials
are present; otherwise the app serves the synced cache (backend/app/data/
gmail_tasks.json) or mock data. See README "Connect Gmail (live refresh)".

Setup (one-time):
  1. Google Cloud Console -> enable Gmail API -> create OAuth client (Desktop).
  2. Download the client JSON as  backend/credentials.json
  3. First run opens a browser for consent; a read-only token is cached to
     backend/token.json. No email is ever modified or sent (readonly scope).
"""
from __future__ import annotations

import base64
from pathlib import Path
from datetime import datetime
from typing import Optional

from app.schemas import Task
from app.services.task_parser import extract_tasks_hybrid

# Read-only. Cannot send, modify, or delete anything.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

BACKEND_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_FILE = BACKEND_DIR / "credentials.json"
TOKEN_FILE = BACKEND_DIR / "token.json"


def is_configured() -> bool:
    """True if OAuth is set up enough to attempt a live fetch."""
    return CREDENTIALS_FILE.exists() or TOKEN_FILE.exists()


def _get_service():
    """Build an authenticated Gmail service, running OAuth consent if needed."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_plain_body(payload) -> str:
    """Pull the text/plain body out of a Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        body = _extract_plain_body(part)
        if body:
            return body
    return ""


def fetch_tasks(query: str = "in:inbox newer_than:30d", max_results: int = 25) -> list[Task]:
    """Fetch recent inbox messages and extract tasks. Read-only."""
    service = _get_service()
    listing = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    all_tasks: list[Task] = []
    for ref in listing.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=ref["id"], format="full"
        ).execute()

        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "")
        sender = headers.get("from", "")
        body = _extract_plain_body(msg.get("payload", {})) or msg.get("snippet", "")

        email_date: Optional[datetime] = None
        internal = msg.get("internalDate")
        if internal:
            email_date = datetime.fromtimestamp(int(internal) / 1000)

        all_tasks.extend(
            extract_tasks_hybrid(subject, body, sender, email_date, ref["id"])
        )

    # Deduplicate by task id
    seen: set[str] = set()
    deduped: list[Task] = []
    for task in all_tasks:
        if task.id not in seen:
            seen.add(task.id)
            deduped.append(task)
    return deduped
