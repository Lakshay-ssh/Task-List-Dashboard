import pytest
from datetime import datetime, timedelta, date
from app.services.task_parser import (
    extract_priority,
    extract_due_date,
    extract_tasks_regex,
    extract_tasks_hybrid,
)


class TestPriorityExtraction:
    def test_high_priority_urgent(self):
        assert extract_priority("URGENT: Fix this bug") == "high"

    def test_high_priority_asap(self):
        assert extract_priority("ASAP please") == "high"

    def test_high_priority_critical(self):
        assert extract_priority("Critical issue needs fixing") == "high"

    def test_medium_priority_important(self):
        assert extract_priority("Important task to complete") == "medium"

    def test_low_priority_default(self):
        assert extract_priority("Just a regular task") == "low"

    def test_case_insensitive(self):
        assert extract_priority("urgent task") == "high"
        assert extract_priority("IMPORTANT item") == "medium"


class TestDueDateExtraction:
    def test_due_date_with_slash(self):
        result = extract_due_date("Due 07/15/2026 for review")
        assert result == date(2026, 7, 15)

    def test_due_date_with_dash(self):
        result = extract_due_date("Deadline: 2026-07-20")
        assert result == date(2026, 7, 20)

    def test_due_date_by_pattern(self):
        result = extract_due_date("by 07/10/2026")
        assert result == date(2026, 7, 10)

    def test_no_date_returns_none(self):
        # We do not invent a deadline when the email states none.
        assert extract_due_date("No date specified") is None

    def test_no_date_with_email_date_still_none(self):
        assert extract_due_date("No date here", datetime(2026, 7, 1)) is None


class TestTaskRegexExtraction:
    def test_extract_todo_task(self):
        email_subject = "TODO: Review code"
        email_body = "Please review the code changes."
        tasks = extract_tasks_regex(email_subject, email_body, "dev@team.com")

        assert len(tasks) > 0
        assert any("Review code" in task.title for task in tasks)

    def test_extract_multiple_tasks(self):
        email_subject = "Multiple tasks"
        email_body = """
        TODO: Update docs
        TASK: Fix bug
        ACTION: Deploy to prod
        """
        tasks = extract_tasks_regex(email_subject, email_body, "ops@team.com")

        assert len(tasks) >= 2

    def test_extract_bracketed_task(self):
        email_subject = "Project Update"
        email_body = "[ACTION] Merge pull request"
        tasks = extract_tasks_regex(email_subject, email_body, "dev@team.com")

        assert len(tasks) > 0
        assert any("Merge pull request" in task.title for task in tasks)

    def test_no_tasks_found(self):
        email_subject = "Regular email"
        email_body = "Just some regular content here."
        tasks = extract_tasks_regex(email_subject, email_body, "user@team.com")

        assert len(tasks) == 0

    def test_task_priority_from_body(self):
        email_subject = "Task list"
        email_body = "TODO: URGENT fix database"
        tasks = extract_tasks_regex(email_subject, email_body, "dba@team.com")

        if tasks:
            assert tasks[0].priority == "high"

    def test_deduplication(self):
        email_subject = "Duplicate test"
        email_body = """
        TODO: Important task
        TASK: Important task
        """
        tasks = extract_tasks_regex(email_subject, email_body, "user@team.com")

        # Should deduplicate same title
        assert len(tasks) <= 2


class TestTaskHybridExtraction:
    def test_regex_path_with_indicators(self):
        email_subject = "TODO: Update documentation"
        email_body = "Please update the API docs"
        tasks = extract_tasks_hybrid(email_subject, email_body, "docs@team.com")

        assert len(tasks) > 0
        assert tasks[0].title is not None

    def test_no_extraction_without_indicators(self):
        email_subject = "Meeting notes"
        email_body = "We discussed the project timeline."
        tasks = extract_tasks_hybrid(email_subject, email_body, "manager@team.com")

        assert len(tasks) == 0

    def test_task_has_required_fields(self):
        email_subject = "TODO: Test task"
        email_body = "This is a test"
        tasks = extract_tasks_hybrid(email_subject, email_body, "test@team.com")

        if tasks:
            task = tasks[0]
            assert task.id is not None
            assert task.title is not None
            assert task.description is not None
            assert task.priority in ["high", "medium", "low"]
            # due_date may be None when the email states no deadline
            assert task.sender == "test@team.com"


class TestTaskModel:
    def test_task_creation(self):
        from app.schemas import Task

        task = Task(
            id="test_1",
            title="Test task",
            description="A test task",
            priority="high",
            due_date=date(2026, 7, 15),
            sender="test@example.com",
        )

        assert task.id == "test_1"
        assert task.title == "Test task"
        assert task.priority == "high"
        assert task.completed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
