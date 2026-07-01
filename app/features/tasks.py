from app.memory.store import _conn
import uuid

# ── tasks ─────────────────────────────────────────────────────

def add_task_to_board(board_name: str, task: str, priority: str = "normal", due_time: str | None = None) -> str:
    board = find_board_by_name(board_name)
    if not board:
        return f"I couldn't find a '{board_name}' board. Want me to create it?"
    add_todo_to_board(board["id"], task, priority, due_time)
    when = f" at {due_time}" if due_time else ""
    return f"Added '{task}'{when} to {board['title']}."


def list_tasks_on_board(board_name: str, show_done: bool = False) -> str:
    board = find_board_by_name(board_name)
    if not board:
        return f"I couldn't find a '{board_name}' board."

    with _conn() as con:
        if show_done:
            rows = con.execute(
                "SELECT task, priority, done, due_time FROM todos WHERE board_id = ? "
                "ORDER BY done, priority DESC, created_at",
                (board["id"],)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT task, priority, done, due_time FROM todos WHERE board_id = ? AND done = 0 "
                "ORDER BY priority DESC, created_at",
                (board["id"],)
            ).fetchall()

    if not rows:
        return f"No tasks on {board['title']}." if not show_done else f"No tasks found on {board['title']}."

    lines = [f"Tasks on {board['title']}:"]
    for i, row in enumerate(rows, 1):
        status = "✓" if row["done"] else "○"
        priority_tag = f" [{row['priority']}]" if row["priority"] != "normal" else ""
        time_tag = f" ({row['due_time']})" if row["due_time"] else ""
        lines.append(f"  {i}. {status} {row['task']}{time_tag}{priority_tag}")
    return "\n".join(lines)


def complete_task_on_board(board_name: str, task_ref: str) -> str:
    board = find_board_by_name(board_name)
    if not board:
        return f"I couldn't find a '{board_name}' board."

    with _conn() as con:
        row = con.execute(
            "SELECT id, task FROM todos WHERE board_id = ? AND task LIKE ? AND done = 0",
            (board["id"], f"%{task_ref}%")
        ).fetchone()
        if row:
            con.execute("UPDATE todos SET done = 1 WHERE id = ?", (row["id"],))
            return f"Marked as done on {board['title']}: '{row['task']}'."

    return f"I couldn't find '{task_ref}' on {board['title']}."


def delete_task_on_board(board_name: str, task_ref: str) -> str:
    board = find_board_by_name(board_name)
    if not board:
        return f"I couldn't find a '{board_name}' board."

    with _conn() as con:
        row = con.execute(
            "SELECT id, task FROM todos WHERE board_id = ? AND task LIKE ?",
            (board["id"], f"%{task_ref}%")
        ).fetchone()
        if row:
            con.execute("DELETE FROM todos WHERE id = ?", (row["id"],))
            return f"Removed from {board['title']}: '{row['task']}'."

    return f"I couldn't find '{task_ref}' on {board['title']}."

# ── boards ────────────────────────────────────────────────────

def add_board(title: str) -> dict:
    board_id = str(uuid.uuid4())
    with _conn() as con:
        con.execute(
            "INSERT INTO boards (id, title, created_at) VALUES (?, ?, datetime('now'))",
            (board_id, title)
        )
    return {"id": board_id, "title": title}


def list_boards() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, created_at FROM boards ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def find_board_by_name(name: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT id, title FROM boards WHERE title = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row:
            return dict(row)
        row = con.execute(
            "SELECT id, title FROM boards WHERE title LIKE ?", (f"%{name}%",)
        ).fetchone()
    return dict(row) if row else None


def delete_board(board_id: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM todos WHERE board_id = ?", (board_id,))
        con.execute("DELETE FROM boards WHERE id = ?", (board_id,))


# ── todos (boards-aware) ──────────────────────────────────────

def add_todo_to_board(board_id: str, task: str, priority: str = "normal", due_time: str | None = None) -> dict:
    todo_id = str(uuid.uuid4())
    with _conn() as con:
        con.execute(
            "INSERT INTO todos (id, task, priority, done, created_at, board_id, due_time) "
            "VALUES (?, ?, ?, 0, datetime('now'), ?, ?)",
            (todo_id, task, priority, board_id, due_time)
        )
    return {"id": todo_id, "task": task, "priority": priority, "done": False, "board_id": board_id, "due_time": due_time}


def list_todos_by_board(board_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, task, priority, done, created_at, due_time FROM todos "
            "WHERE board_id = ? AND done = 0 "
            "ORDER BY (due_time IS NULL), due_time, priority DESC, created_at",
            (board_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def set_todo_done(todo_id: str, done: bool) -> None:
    with _conn() as con:
        con.execute("UPDATE todos SET done = ? WHERE id = ?", (1 if done else 0, todo_id))


def delete_todo_by_id(todo_id: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM todos WHERE id = ?", (todo_id,))