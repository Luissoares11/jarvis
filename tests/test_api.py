"""
Jarvis Backend — Integration Tests
===================================
Run from the repo root:  pytest tests/ -v
"""

import sys
import os
import pytest

# make sure imports resolve from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from server.main import app
from app.memory.store import init_db, _conn

# ── token ─────────────────────────────────────────────────────

TOKEN = os.getenv("JARVIS_API_TOKEN", "changeme")
AUTH  = {"Authorization": f"Bearer {TOKEN}"}


# ── fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    """
    Runs before every test.
    Wipes the tables we touch so tests don't bleed into each other.
    autouse=True means every test gets this automatically.
    """
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM todos")
        con.execute("DELETE FROM reminders")
        con.execute("DELETE FROM events")
        con.execute("DELETE FROM notifications")
    yield  # test runs here
    # nothing to do after — next test gets a fresh clean_db call


@pytest.fixture
def client():
    """
    A TestClient wraps the FastAPI app and lets us make HTTP requests
    without actually starting a server. Fast and isolated.
    """
    with TestClient(app) as c:
        yield c


def _insert_task(task: str, priority: str = "normal"):
    """Helper — insert a todo row directly into the DB."""
    import uuid
    with _conn() as con:
        con.execute(
            "INSERT INTO todos (id, task, priority, done, created_at) "
            "VALUES (?, ?, ?, 0, datetime('now'))",
            (str(uuid.uuid4()), task, priority)
        )


def _insert_event(title: str, start: str = "2099-12-31T10:00:00"):
    """Helper — insert a future event so it appears in /events."""
    import uuid
    with _conn() as con:
        con.execute(
            "INSERT INTO events (id, title, start_time, end_time, notes, created_at) "
            "VALUES (?, ?, ?, ?, '', datetime('now'))",
            (str(uuid.uuid4()), title, start, start)
        )


# ── /health ───────────────────────────────────────────────────

class TestHealth:
    def test_returns_ok(self, client):
        """The health endpoint should always return 200 with status ok."""
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_no_auth_required(self, client):
        """Health should be public — no token needed."""
        r = client.get("/health")
        assert r.status_code == 200


# ── auth ──────────────────────────────────────────────────────

class TestAuth:
    def test_missing_token_is_rejected(self, client):
        """/tasks without a token should return 403."""
        r = client.get("/tasks")
        assert r.status_code == 403

    def test_wrong_token_is_rejected(self, client):
        """/tasks with a bad token should return 403."""
        r = client.get("/tasks", headers={"Authorization": "Bearer wrongtoken"})
        assert r.status_code == 403

    def test_correct_token_is_accepted(self, client):
        """A correct token should get through."""
        r = client.get("/tasks", headers=AUTH)
        assert r.status_code == 200


# ── /tasks ────────────────────────────────────────────────────

class TestTasks:
    def test_empty_when_no_tasks(self, client):
        """Fresh DB should return an empty list, not an error."""
        r = client.get("/tasks", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"tasks": []}

    def test_returns_inserted_task(self, client):
        """A task inserted into the DB should appear in the response."""
        _insert_task("Buy milk")
        r = client.get("/tasks", headers=AUTH)
        data = r.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task"] == "Buy milk"

    def test_response_has_expected_fields(self, client):
        """Each task object must have id, task, priority, done, created_at."""
        _insert_task("Write tests")
        task = client.get("/tasks", headers=AUTH).json()["tasks"][0]
        for field in ("id", "task", "priority", "done", "created_at"):
            assert field in task, f"Missing field: {field}"

    def test_done_tasks_are_excluded(self, client):
        """Completed tasks should not appear — endpoint only returns active ones."""
        import uuid
        with _conn() as con:
            con.execute(
                "INSERT INTO todos (id, task, priority, done, created_at) "
                "VALUES (?, 'Done task', 'normal', 1, datetime('now'))",
                (str(uuid.uuid4()),)
            )
        r = client.get("/tasks", headers=AUTH)
        assert r.json() == {"tasks": []}

    def test_multiple_tasks(self, client):
        """Multiple tasks should all be returned."""
        _insert_task("Task A")
        _insert_task("Task B")
        _insert_task("Task C")
        data = client.get("/tasks", headers=AUTH).json()
        assert len(data["tasks"]) == 3

    def test_missing_token_is_rejected(self, client):
        """/tasks without a token should return 401."""
        r = client.get("/tasks")
        assert r.status_code == 401

    def test_wrong_token_is_rejected(self, client):
        """/tasks with a bad token should return 401."""
        r = client.get("/tasks", headers={"Authorization": "Bearer wrongtoken"})
        assert r.status_code == 401

# ── /reminders ────────────────────────────────────────────────

class TestReminders:
    def test_empty_when_no_reminders(self, client):
        r = client.get("/reminders", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"reminders": []}

    def test_returns_inserted_reminder(self, client):
        import uuid
        with _conn() as con:
            con.execute(
                "INSERT INTO reminders (id, message, remind_at, fired, created_at) "
                "VALUES (?, 'Take meds', '2099-12-31T08:00:00', 0, datetime('now'))",
                (str(uuid.uuid4()),)
            )
        data = client.get("/reminders", headers=AUTH).json()
        assert len(data["reminders"]) == 1
        assert data["reminders"][0]["message"] == "Take meds"

    def test_fired_reminders_are_excluded(self, client):
        """Reminders that already fired should not appear."""
        import uuid
        with _conn() as con:
            con.execute(
                "INSERT INTO reminders (id, message, remind_at, fired, created_at) "
                "VALUES (?, 'Old reminder', '2020-01-01T08:00:00', 1, datetime('now'))",
                (str(uuid.uuid4()),)
            )
        r = client.get("/reminders", headers=AUTH)
        assert r.json() == {"reminders": []}

    def test_response_has_expected_fields(self, client):
        import uuid
        with _conn() as con:
            con.execute(
                "INSERT INTO reminders (id, message, remind_at, fired, created_at) "
                "VALUES (?, 'Test', '2099-01-01T09:00:00', 0, datetime('now'))",
                (str(uuid.uuid4()),)
            )
        reminder = client.get("/reminders", headers=AUTH).json()["reminders"][0]
        for field in ("id", "message", "remind_at"):
            assert field in reminder, f"Missing field: {field}"


# ── /events ───────────────────────────────────────────────────

class TestEvents:
    def test_empty_when_no_events(self, client):
        r = client.get("/events", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"events": []}

    def test_returns_future_event(self, client):
        _insert_event("🎓 Exam: Maths", start="2099-06-30T10:00:00+01:00")
        data = client.get("/events", headers=AUTH).json()
        assert len(data["events"]) == 1
        assert "Maths" in data["events"][0]["title"]

    def test_past_events_are_excluded(self, client):
        """Events in the past should not appear in the default response."""
        _insert_event("Old concert", start="2000-01-01T20:00:00")
        r = client.get("/events", headers=AUTH)
        assert r.json() == {"events": []}

    def test_response_has_expected_fields(self, client):
        _insert_event("Meeting", start="2099-07-01T14:00:00+01:00")
        event = client.get("/events", headers=AUTH).json()["events"][0]
        for field in ("id", "title", "start_time", "end_time", "notes"):
            assert field in event, f"Missing field: {field}"

    # _insert_event helper — add timezone to the start time
    def _insert_event(title: str, start: str = "2099-12-31T10:00:00+01:00"):
        import uuid
        with _conn() as con:
            con.execute(
                "INSERT INTO events (id, title, start_time, end_time, notes, created_at) "
                "VALUES (?, ?, ?, ?, '', datetime('now'))",
                (str(uuid.uuid4()), title, start, start)
        ) 

# ── /chat ─────────────────────────────────────────────────────

class TestChat:
    def test_greeting_returns_response(self, client):
        """A basic message should return a non-empty response string."""
        r = client.post("/chat", json={"message": "hello", "session_id": "test"}, headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert len(data["response"]) > 0

    def test_session_id_echoed_back(self, client):
        """The response should echo back the session_id we sent."""
        r = client.post("/chat", json={"message": "hi", "session_id": "my-session"}, headers=AUTH)
        assert r.json()["session_id"] == "my-session"

    def test_missing_message_is_rejected(self, client):
        """Sending no message field should return 422 (validation error)."""
        r = client.post("/chat", json={}, headers=AUTH)
        assert r.status_code == 422


# ── /timers ───────────────────────────────────────────────────

class TestTimers:
    def test_returns_empty_when_no_timers(self, client):
        r = client.get("/timers", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"timers": []}


# ── /notifications ────────────────────────────────────────────

class TestNotifications:
    def test_returns_empty_when_none(self, client):
        r = client.get("/notifications", headers=AUTH)
        assert r.status_code == 200
        assert "notifications" in r.json()

    def test_marks_as_read_after_fetch(self, client):
        """Fetching notifications should mark them as read — second fetch returns empty."""
        import uuid
        with _conn() as con:
            con.execute(
                "INSERT INTO notifications (id, message, read, created_at) "
                "VALUES (?, 'Hello', 0, datetime('now'))",
                (str(uuid.uuid4()),)
            )
        first  = client.get("/notifications", headers=AUTH).json()["notifications"]
        second = client.get("/notifications", headers=AUTH).json()["notifications"]
        assert len(first) == 1
        assert len(second) == 0