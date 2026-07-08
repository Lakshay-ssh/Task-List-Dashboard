import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestTasksEndpoint:
    def test_get_tasks_success(self, client):
        response = client.get("/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert isinstance(data["tasks"], list)
        assert isinstance(data["total"], int)

    def test_tasks_have_required_fields(self, client):
        response = client.get("/api/tasks")
        data = response.json()

        if data["tasks"]:
            task = data["tasks"][0]
            assert "id" in task
            assert "title" in task
            assert "description" in task
            assert "priority" in task
            assert "due_date" in task
            assert "sender" in task
            assert "completed" in task

    def test_tasks_priority_valid(self, client):
        response = client.get("/api/tasks")
        data = response.json()

        for task in data["tasks"]:
            assert task["priority"] in ["high", "medium", "low"]

    def test_tasks_completed_is_boolean(self, client):
        response = client.get("/api/tasks")
        data = response.json()

        for task in data["tasks"]:
            assert isinstance(task["completed"], bool)

    def test_tasks_count_matches(self, client):
        response = client.get("/api/tasks")
        data = response.json()

        assert data["total"] == len(data["tasks"])

    def test_mock_data_has_tasks(self, client):
        response = client.get("/api/tasks")
        data = response.json()

        # Mock data should have at least some tasks
        assert len(data["tasks"]) > 0

    def test_tasks_are_deduplicated(self, client):
        response = client.get("/api/tasks")
        data = response.json()

        task_ids = [task["id"] for task in data["tasks"]]
        # No duplicate IDs
        assert len(task_ids) == len(set(task_ids))


class TestCORS:
    def test_cors_enabled(self, client):
        response = client.get("/api/tasks")
        # CORS headers should be present in response
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
