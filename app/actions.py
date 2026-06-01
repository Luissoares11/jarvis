import threading
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .memory.store import _conn
import uuid

TIMEZONE = "Europe/Lisbon"


# ── helpers ───────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def _parse_datetime(date_str: str, time_str: str = None) -> datetime:
    """Parse flexible date/time strings into a datetime object."""
    date_str = date_str.strip().lower()
    time_str = time_str.strip().lower() if time_str else "09:00"

    now = _now()

    # relative dates
    if date_str in ("today",):
        date = now.date()
    elif date_str in ("tomorrow",):
        date = (now + timedelta(days=1)).date()
    elif date_str in ("next week",):
        date = (now + timedelta(weeks=1)).date()
    else:
        # try common formats
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %B %Y", "%d %b %Y"):
            try:
                date = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"I couldn't understand the date: {date_str}")

    # parse time
    for fmt in ("%H:%M", "%I:%M %p", "%I%p", "%H%M"):
        try:
            t = datetime.strptime(time_str, fmt).time()
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"I couldn't understand the time: {time_str}")

    return datetime.combine(date, t, tzinfo=ZoneInfo(TIMEZONE))


# ── todos ─────────────────────────────────────────────────────

def add_todo(task: str, priority: str = "normal") -> str:
    with _conn() as con:
        con.execute(
            "INSERT INTO todos (id, task, priority, done, created_at) "
            "VALUES (?, ?, ?, 0, datetime('now'))",
            (str(uuid.uuid4()), task, priority)
        )
    return f"Added to your list: '{task}'."


def list_todos(show_done: bool = False) -> str:
    with _conn() as con:
        if show_done:
            rows = con.execute(
                "SELECT id, task, priority, done FROM todos ORDER BY done, priority DESC, created_at"
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT id, task, priority, done FROM todos WHERE done = 0 "
                "ORDER BY priority DESC, created_at"
            ).fetchall()

    if not rows:
        return "Your to-do list is empty." if not show_done else "No tasks found."

    lines = ["Your tasks:"]
    for i, row in enumerate(rows, 1):
        status = "✓" if row["done"] else "○"
        priority_tag = f" [{row['priority']}]" if row["priority"] != "normal" else ""
        lines.append(f"  {i}. {status} {row['task']}{priority_tag}")
    return "\n".join(lines)


def complete_todo(task_ref: str) -> str:
    with _conn() as con:
        # try by position number
        if task_ref.isdigit():
            rows = con.execute(
                "SELECT id, task FROM todos WHERE done = 0 ORDER BY created_at"
            ).fetchall()
            idx = int(task_ref) - 1
            if 0 <= idx < len(rows):
                todo_id = rows[idx]["id"]
                task    = rows[idx]["task"]
                con.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,))
                return f"Marked as done: '{task}'."
            return "That task number doesn't exist."

        # try by name match
        row = con.execute(
            "SELECT id, task FROM todos WHERE task LIKE ? AND done = 0",
            (f"%{task_ref}%",)
        ).fetchone()
        if row:
            con.execute("UPDATE todos SET done = 1 WHERE id = ?", (row["id"],))
            return f"Marked as done: '{row['task']}'."

    return "I couldn't find that task."


def delete_todo(task_ref: str) -> str:
    with _conn() as con:
        if task_ref.isdigit():
            rows = con.execute(
                "SELECT id, task FROM todos WHERE done = 0 ORDER BY created_at"
            ).fetchall()
            idx = int(task_ref) - 1
            if 0 <= idx < len(rows):
                todo_id = rows[idx]["id"]
                task    = rows[idx]["task"]
                con.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
                return f"Removed: '{task}'."
            return "That task number doesn't exist."

        row = con.execute(
            "SELECT id, task FROM todos WHERE task LIKE ?",
            (f"%{task_ref}%",)
        ).fetchone()
        if row:
            con.execute("DELETE FROM todos WHERE id = ?", (row["id"],))
            return f"Removed: '{row['task']}'."

    return "I couldn't find that task."


# ── reminders ─────────────────────────────────────────────────

_reminder_threads: dict[str, threading.Timer] = {}


def _fire_reminder(reminder_id: str, message: str):
    print(f"\n⏰ Jarvis Reminder: {message}\n")
    with _conn() as con:
        con.execute(
            "UPDATE reminders SET fired = 1 WHERE id = ?",
            (reminder_id,)
        )
    _reminder_threads.pop(reminder_id, None)


def add_reminder(message: str, when_str: str, date_str: str = "today") -> str:
    try:
        dt = _parse_datetime(date_str, when_str)
        now = _now()

        if dt <= now:
            return "That time has already passed, sir."

        reminder_id = str(uuid.uuid4())
        with _conn() as con:
            con.execute(
                "INSERT INTO reminders (id, message, remind_at, fired, created_at) "
                "VALUES (?, ?, ?, 0, datetime('now'))",
                (reminder_id, message, dt.isoformat())
            )

        delay = (dt - now).total_seconds()
        timer = threading.Timer(delay, _fire_reminder, args=[reminder_id, message])
        timer.daemon = True
        timer.start()
        _reminder_threads[reminder_id] = timer

        return f"Reminder set: '{message}' at {dt.strftime('%H:%M on %d %b')}."
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't set that reminder: {e}"


def list_reminders() -> str:
    with _conn() as con:
        rows = con.execute(
            "SELECT message, remind_at FROM reminders WHERE fired = 0 "
            "ORDER BY remind_at"
        ).fetchall()

    if not rows:
        return "No pending reminders."

    lines = ["Pending reminders:"]
    for row in rows:
        dt = datetime.fromisoformat(row["remind_at"])
        lines.append(f"  - '{row['message']}' at {dt.strftime('%H:%M on %d %b')}")
    return "\n".join(lines)


def load_pending_reminders():
    """Call on startup to re-arm any reminders that survived a restart."""
    now = _now()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, message, remind_at FROM reminders WHERE fired = 0"
        ).fetchall()

    for row in rows:
        dt = datetime.fromisoformat(row["remind_at"])
        dt = dt.replace(tzinfo=ZoneInfo(TIMEZONE)) if dt.tzinfo is None else dt

        if dt <= now:
            # missed while offline — fire immediately
            _fire_reminder(row["id"], row["message"])
        else:
            delay = (dt - now).total_seconds()
            timer = threading.Timer(delay, _fire_reminder, args=[row["id"], row["message"]])
            timer.daemon = True
            timer.start()
            _reminder_threads[row["id"]] = timer


# ── timers ────────────────────────────────────────────────────

_timer_threads: dict[str, dict] = {}


def _fire_timer(timer_id: str, label: str):
    print(f"\n⏱️  Jarvis Timer: {label} — time's up!\n")
    _timer_threads.pop(timer_id, None)


def set_timer(duration_str: str, label: str = "Timer") -> str:
    try:
        duration_str = duration_str.strip().lower()
        seconds = 0

        import re
        h = re.search(r"(\d+)\s*h(?:our)?s?", duration_str)
        m = re.search(r"(\d+)\s*m(?:in(?:ute)?)?s?", duration_str)
        s = re.search(r"(\d+)\s*s(?:ec(?:ond)?)?s?", duration_str)

        if h: seconds += int(h.group(1)) * 3600
        if m: seconds += int(m.group(1)) * 60
        if s: seconds += int(s.group(1))

        if seconds == 0:
            # try plain number as minutes
            if duration_str.isdigit():
                seconds = int(duration_str) * 60
            else:
                return "I couldn't understand that duration."

        timer_id = str(uuid.uuid4())
        end_time = datetime.now() + timedelta(seconds=seconds)  
        timer = threading.Timer(seconds, _fire_timer, args=[timer_id, label])
        timer.daemon = True
        timer.start()
        _timer_threads[timer_id] = {"timer": timer, "label": label, "ends_at": end_time.isoformat()}  # updated


        mins = seconds // 60
        secs = seconds % 60
        duration_display = f"{mins}m {secs}s" if secs else f"{mins}m"
        if mins >= 60:
            duration_display = f"{mins//60}h {mins%60}m" if mins % 60 else f"{mins//60}h"

        return f"Timer set for {duration_display}: '{label}'."
    except Exception as e:
        return f"I couldn't set that timer: {e}"


# ── calendar ───────────────────────────────────────────

EVENT_TYPES = {
    "exam":        "🎓 Exam",
    "test":        "🎓 Test",
    "appointment": "🏥 Appointment",
    "anniversary": "🎂 Anniversary",
    "birthday":    "🎂 Birthday",
    "meeting":     "💼 Meeting",
    "deadline":    "⚠️ Deadline",
    "alarm":       "⏰ Alarm",
    "other":       "📅 Event",
}
def add_event(
    title: str,
    date_str: str,
    time_str: str = "09:00",
    event_type: str = "other",
    notes: str = "",
) -> str:
    try:
        dt = _parse_datetime(date_str, time_str)
        dt_end = dt + timedelta(hours=1)

        type_label = EVENT_TYPES.get(event_type.lower(), "📅 Event")
        full_title = f"{type_label}: {title}"

        with _conn() as con:
            con.execute(
                "INSERT INTO events (id, title, start_time, end_time, notes, created_at) "
                "VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (
                    str(uuid.uuid4()),
                    full_title,
                    dt.isoformat(),
                    dt_end.isoformat(),
                    notes,
                )
            )

        return (
            f"Added {type_label} '{title}' on "
            f"{dt.strftime('%d %b at %H:%M')}."
        )
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't add that event: {e}"
    
def delete_event(title: str) -> str:
    with _conn() as con:
        row = con.execute(
            "SELECT id, title FROM events WHERE title LIKE ?",
            (f"%{title}%",)
        ).fetchone()
        if row:
            con.execute("DELETE FROM events WHERE id = ?", (row["id"],))
            return f"Removed event '{row['title']}'."
    return "I couldn't find that event."

def edit_event(
    title: str,
    new_title: str = None,
    new_date_str: str = None,
    new_time_str: str = None,
    new_notes: str = None,
) -> str:
    try:
        with _conn() as con:
            row = con.execute(
                "SELECT id, title, start_time, end_time, notes FROM events WHERE title LIKE ?",
                (f"%{title}%",)
            ).fetchone()

            if not row:
                return "I couldn't find that event."

            current_dt = datetime.fromisoformat(row["start_time"])

            if new_date_str or new_time_str:
                date_str = new_date_str or current_dt.strftime("%d/%m/%Y")
                time_str = new_time_str or current_dt.strftime("%H:%M")
                new_dt = _parse_datetime(date_str, time_str)
                new_dt_end = new_dt + timedelta(hours=1)
            else:
                new_dt = current_dt
                new_dt_end = datetime.fromisoformat(row["end_time"])

            final_title = new_title if new_title else row["title"]
            final_notes = new_notes if new_notes is not None else row["notes"]

            con.execute(
                "UPDATE events SET title = ?, start_time = ?, end_time = ?, notes = ? WHERE id = ?",
                (final_title, new_dt.isoformat(), new_dt_end.isoformat(), final_notes, row["id"])
            )

        return f"Updated event '{final_title}'."
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't update that event: {e}"
        
def list_events(days_ahead: int = 30, include_past: bool = False, all_events: bool = False) -> str:
    now = _now()
    until = now + timedelta(days=days_ahead)

    with _conn() as con:
        rows = con.execute(
            "SELECT title, start_time, notes FROM events ORDER BY start_time"
        ).fetchall()

    if not all_events and not include_past:
        filtered = []
        for row in rows:
            dt = datetime.fromisoformat(row["start_time"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(TIMEZONE))
            if now <= dt <= until:
                filtered.append(row)
        rows = filtered
    elif include_past:
        filtered = []
        for row in rows:
            dt = datetime.fromisoformat(row["start_time"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(TIMEZONE))
            if dt < now:
                filtered.append(row)
        rows = sorted(filtered, key=lambda r: r["start_time"], reverse=True)[:20]

    if not rows:
        if include_past:
            return "No past events found."
        if all_events:
            return "No events found."
        return f"No events in the next {days_ahead} days."

    if all_events:
        lines = ["All events:"]
    elif include_past:
        lines = ["Past events:"]
    else:
        lines = [f"Events in the next {days_ahead} days:"]

    for row in rows:
        dt = datetime.fromisoformat(row["start_time"])
        lines.append(f"  - {dt.strftime('%d %b %Y %H:%M')} — {row['title']}")
        if row["notes"]:
            lines.append(f"    {row['notes']}")
    return "\n".join(lines)

def set_alarm(time_str: str, label: str = "Wake up") -> str:
    return add_reminder(label, time_str, "today")