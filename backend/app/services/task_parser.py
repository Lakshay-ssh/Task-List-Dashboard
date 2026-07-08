import re
import hashlib
from datetime import datetime
from typing import Optional
from app.schemas import Task


def extract_priority(text: str) -> str:
    """Extract priority from email text using keyword matching."""
    text_lower = text.lower()

    high_keywords = r'\b(urgent|asap|critical|immediately|high.priority|must.do|emergency)\b'
    medium_keywords = r'\b(important|medium.priority|soon|please.do)\b'

    if re.search(high_keywords, text_lower):
        return 'high'
    elif re.search(medium_keywords, text_lower):
        return 'medium'
    else:
        return 'low'


def extract_due_date(text: str, email_date: Optional[datetime] = None):
    """Extract a due date from email text. Returns a date, or None if the email
    specifies no deadline (we do not invent one)."""
    text_lower = text.lower()

    # Pattern: "due [date format]" or "deadline:" - supports both MM/DD and YYYY-MM-DD
    date_patterns = [
        r'due\s+(\d{4}-\d{1,2}-\d{1,2})',  # ISO format
        r'deadline[:\s]+(\d{4}-\d{1,2}-\d{1,2})',  # ISO format
        r'by\s+(\d{4}-\d{1,2}-\d{1,2})',  # ISO format
        r'due\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY
        r'deadline[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY
        r'by\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text_lower)
        if match:
            date_str = match.group(1)
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue

    # No deadline found — leave it unset rather than fabricating one.
    return None


def extract_tasks_regex(email_subject: str, email_body: str, sender: str, email_date: Optional[datetime] = None, email_id: Optional[str] = None) -> list[Task]:
    """Extract tasks from email using regex patterns (fast path)."""
    combined_text = f"{email_subject}\n{email_body}"
    tasks = []

    # Task indicators: TODO, TASK, [ACTION], etc.
    task_patterns = [
        r'(?:^|\n)\s*(?:TODO|TASK|ACTION|BUG|FEATURE|FIX)[:\s]+([^\n]+)',
        r'(?:^|\n)\s*\[([A-Z\s]+)\]\s*:?\s+([^\n]+)',
        r'(?:^|\n)\s*-\s+\[?\s*(?:TODO|TASK|ACTION)\s*\]?\s+([^\n]+)',
    ]

    task_set = set()  # Deduplicate by title

    for pattern in task_patterns:
        matches = re.finditer(pattern, combined_text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            title = match.group(1) if match.lastindex == 1 else match.group(2) if match.lastindex == 2 else None
            if title:
                title = title.strip()[:100]  # Limit length
                if title and title not in task_set:
                    task_set.add(title)
                    priority = extract_priority(combined_text)
                    due_date = extract_due_date(combined_text, email_date)

                    task_id = f"{sender}_{hashlib.md5(title.encode()).hexdigest()[:8]}"
                    tasks.append(Task(
                        id=task_id,
                        title=title,
                        description=email_subject[:200] if email_subject else title,
                        priority=priority,
                        due_date=due_date,
                        sender=sender,
                        email_id=email_id,
                    ))

    return tasks


def extract_tasks_claude(email_subject: str, email_body: str, sender: str, email_date: Optional[datetime] = None, email_id: Optional[str] = None) -> list[Task]:
    """
    Extract tasks from email using Claude AI (fallback when regex finds nothing).
    Only call this if regex extraction returned 0 tasks but email looks task-like.
    """
    try:
        from anthropic import Anthropic

        client = Anthropic()

        prompt = f"""Extract actionable tasks from this email. Return JSON array of tasks.

Email from: {sender}
Subject: {email_subject}
Body: {email_body}

Return ONLY valid JSON in this format (no markdown, no explanation):
[
  {{"title": "Task title", "priority": "high|medium|low", "due_date": "YYYY-MM-DD"}}
]

If no clear tasks, return empty array [].
Prioritize: high=urgent/asap/critical, medium=important, low=default.
Due dates: extract from text only. If the email states no deadline, set "due_date" to null (do not invent one)."""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Parse JSON
        import json
        task_dicts = json.loads(response_text)

        tasks = []
        for task_dict in task_dicts:
            raw_due = task_dict.get('due_date')
            due_date = None
            if raw_due:
                try:
                    due_date = datetime.strptime(raw_due, '%Y-%m-%d').date()
                except ValueError:
                    due_date = None

            priority = task_dict.get('priority', 'low').lower()
            if priority not in ['high', 'medium', 'low']:
                priority = 'low'

            task_id = f"{sender}_{hashlib.md5(task_dict.get('title', '').encode()).hexdigest()[:8]}"
            tasks.append(Task(
                id=task_id,
                title=task_dict.get('title', '')[:100],
                description=email_subject[:200] if email_subject else task_dict.get('title', ''),
                priority=priority,
                due_date=due_date,
                sender=sender,
                email_id=email_id,
            ))

        return tasks
    except Exception as e:
        print(f"Claude extraction failed: {e}")
        return []


def extract_tasks_hybrid(email_subject: str, email_body: str, sender: str, email_date: Optional[datetime] = None, email_id: Optional[str] = None) -> list[Task]:
    """
    Hybrid extraction: regex first (fast), Claude fallback if regex found nothing.
    """
    # Fast path: regex extraction
    tasks = extract_tasks_regex(email_subject, email_body, sender, email_date, email_id)

    if tasks:
        return tasks

    # Fallback: check if email looks task-like
    combined_text = f"{email_subject}\n{email_body}".lower()
    task_keywords = ['task', 'todo', 'action', 'bug', 'feature', 'fix', 'urgent', 'asap', 'important']

    if any(keyword in combined_text for keyword in task_keywords):
        return extract_tasks_claude(email_subject, email_body, sender, email_date, email_id)

    return []
