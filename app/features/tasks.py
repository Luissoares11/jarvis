from app.memory.store import _conn, find_board_by_name, add_todo_to_board


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