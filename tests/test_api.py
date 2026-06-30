"""
Jarvis Backend — Integration Tests
===================================
Run from the repo root:  pytest tests/ -v
"""

import sys
import os
import pytest
import tempfile

os.environ["MEMORY_FILE"] = os.path.join(tempfile.gettempdir(), "jarvis_test_db.sqlite")

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
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM todos")
        con.execute("DELETE FROM boards")
        con.execute("DELETE FROM events")
        con.execute("DELETE FROM notifications")
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _insert_board(title: str = "Test Board"):
    import uuid
    board_id = str(uuid.uuid4())
    with _conn() as con:
        con.execute(
            "INSERT INTO boards (id, title, created_at) VALUES (?, ?, datetime('now'))",
            (board_id, title)
        )
    return board_id


def _insert_task(board_id: str, task: str, priority: str = "normal", due_time: str = None):
    import uuid
    with _conn() as con:
        con.execute(
            "INSERT INTO todos (id, task, priority, done, created_at, board_id, due_time) "
            "VALUES (?, ?, ?, 0, datetime('now'), ?, ?)",
            (str(uuid.uuid4()), task, priority, board_id, due_time)
        )


def _insert_event(title: str, start: str = None):
    import uuid
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    if start is None:
        dt = datetime.now(ZoneInfo("Europe/Lisbon")) + timedelta(days=3)
        start = dt.isoformat()
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
        """/boards without a token should return 401."""
        r = client.get("/boards")
        assert r.status_code == 401

    def test_wrong_token_is_rejected(self, client):
        """/boards with a bad token should return 401."""
        r = client.get("/boards", headers={"Authorization": "Bearer wrongtoken"})
        assert r.status_code == 401

    def test_correct_token_is_accepted(self, client):
        """A correct token should get through."""
        r = client.get("/boards", headers=AUTH)
        assert r.status_code == 200


# ── /boards ───────────────────────────────────────────────────

class TestBoards:
    def test_empty_when_no_boards(self, client):
        r = client.get("/boards", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"boards": []}

    def test_create_board(self, client):
        r = client.post("/boards", json={"title": "Jarvis UI"}, headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Jarvis UI"
        assert "id" in data

    def test_created_board_appears_in_list(self, client):
        client.post("/boards", json={"title": "Certificates"}, headers=AUTH)
        data = client.get("/boards", headers=AUTH).json()
        assert len(data["boards"]) == 1
        assert data["boards"][0]["title"] == "Certificates"

    def test_multiple_boards(self, client):
        client.post("/boards", json={"title": "Day to Day"}, headers=AUTH)
        client.post("/boards", json={"title": "Jarvis"}, headers=AUTH)
        client.post("/boards", json={"title": "Jarvis UI"}, headers=AUTH)
        data = client.get("/boards", headers=AUTH).json()
        assert len(data["boards"]) == 3

    def test_delete_board(self, client):
        board_id = _insert_board("Temp Board")
        r = client.delete(f"/boards/{board_id}", headers=AUTH)
        assert r.status_code == 200
        data = client.get("/boards", headers=AUTH).json()
        assert data["boards"] == []

    def test_deleting_board_deletes_its_tasks(self, client):
        board_id = _insert_board("Temp Board")
        _insert_task(board_id, "Some task")
        client.delete(f"/boards/{board_id}", headers=AUTH)
        with _conn() as con:
            rows = con.execute("SELECT * FROM todos WHERE board_id = ?", (board_id,)).fetchall()
        assert rows == []


# ── /boards/{id}/tasks ────────────────────────────────────────

class TestBoardTasks:
    def test_empty_when_no_tasks(self, client):
        board_id = _insert_board()
        r = client.get(f"/boards/{board_id}/tasks", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"tasks": []}

    def test_returns_inserted_task(self, client):
        board_id = _insert_board()
        _insert_task(board_id, "Buy milk")
        r = client.get(f"/boards/{board_id}/tasks", headers=AUTH)
        data = r.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task"] == "Buy milk"

    def test_response_has_expected_fields(self, client):
        board_id = _insert_board()
        _insert_task(board_id, "Write tests")
        task = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()["tasks"][0]
        for field in ("id", "task", "priority", "done", "created_at", "due_time"):
            assert field in task, f"Missing field: {field}"

    def test_done_tasks_are_excluded(self, client):
        board_id = _insert_board()
        import uuid
        with _conn() as con:
            con.execute(
                "INSERT INTO todos (id, task, priority, done, created_at, board_id) "
                "VALUES (?, 'Done task', 'normal', 1, datetime('now'), ?)",
                (str(uuid.uuid4()), board_id)
            )
        r = client.get(f"/boards/{board_id}/tasks", headers=AUTH)
        assert r.json() == {"tasks": []}

    def test_multiple_tasks(self, client):
        board_id = _insert_board()
        _insert_task(board_id, "Task A")
        _insert_task(board_id, "Task B")
        _insert_task(board_id, "Task C")
        data = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()
        assert len(data["tasks"]) == 3

    def test_tasks_are_scoped_to_their_board(self, client):
        """A task on board A should never show up when fetching board B."""
        board_a = _insert_board("Board A")
        board_b = _insert_board("Board B")
        _insert_task(board_a, "Only on A")
        data = client.get(f"/boards/{board_b}/tasks", headers=AUTH).json()
        assert data["tasks"] == []

    def test_create_task_via_post(self, client):
        board_id = _insert_board()
        r = client.post("/tasks", json={"board_id": board_id, "task": "New task"}, headers=AUTH)
        assert r.status_code == 200
        data = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()
        assert len(data["tasks"]) == 1

    def test_create_task_with_due_time(self, client):
        board_id = _insert_board()
        client.post(
            "/tasks",
            json={"board_id": board_id, "task": "Timed task", "due_time": "14:30"},
            headers=AUTH
        )
        task = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()["tasks"][0]
        assert task["due_time"] == "14:30"

    def test_create_task_without_due_time(self, client):
        board_id = _insert_board()
        client.post("/tasks", json={"board_id": board_id, "task": "No time task"}, headers=AUTH)
        task = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()["tasks"][0]
        assert task["due_time"] is None

    def test_mark_task_done(self, client):
        board_id = _insert_board()
        _insert_task(board_id, "Finish me")
        task_id = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()["tasks"][0]["id"]
        r = client.patch(f"/tasks/{task_id}", params={"done": True}, headers=AUTH)
        assert r.status_code == 200
        data = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()
        assert data["tasks"] == []  # done tasks excluded from default list

    def test_delete_task(self, client):
        board_id = _insert_board()
        _insert_task(board_id, "Delete me")
        task_id = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()["tasks"][0]["id"]
        r = client.delete(f"/tasks/{task_id}", headers=AUTH)
        assert r.status_code == 200
        data = client.get(f"/boards/{board_id}/tasks", headers=AUTH).json()
        assert data["tasks"] == []


# ── /events ───────────────────────────────────────────────────

class TestEvents:
    def test_empty_when_no_events(self, client):
        r = client.get("/events", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"events": []}

    def test_returns_future_event(self, client):
        _insert_event("🎓 Exam: Maths")
        data = client.get("/events", headers=AUTH).json()
        assert len(data["events"]) == 1
        assert "Maths" in data["events"][0]["title"]

    def test_past_events_are_returned(self, client):
        _insert_event("Old concert", start="2000-01-01T20:00:00+01:00")
        r = client.get("/events", headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()["events"]) == 1

    def test_response_has_expected_fields(self, client):
        _insert_event("Meeting")
        event = client.get("/events", headers=AUTH).json()["events"][0]
        for field in ("id", "title", "start_time", "end_time", "notes"):
            assert field in event, f"Missing field: {field}"


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