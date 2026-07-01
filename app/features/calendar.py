import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.memory.store import _conn
from app.utils import _now, _parse_datetime, TIMEZONE


# ── event types ───────────────────────────────────────────────

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


# ── calendar ──────────────────────────────────────────────────

def add_event(
    title: str,
    date_str: str,
    time_str: str = "09:00",
    event_type: str = "other",
    notes: str = "",
    reminder_offsets: list[int] | None = None,
) -> str:
    try:
        dt = _parse_datetime(date_str, time_str)
        dt_end = dt + timedelta(hours=1)
        type_label = EVENT_TYPES.get(event_type.lower(), "📅 Event")
        event_id = str(uuid.uuid4())

        with _conn() as con:
            con.execute(
                "INSERT INTO events (id, title, type, start_time, end_time, notes, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    event_id,
                    title,
                    event_type.lower(),
                    dt.isoformat(),
                    dt_end.isoformat(),
                    notes,
                )
            )

        if reminder_offsets:
            for offset in reminder_offsets:
                add_event_reminder(event_id, offset)

        return f"Added {type_label} '{title}' on {dt.strftime('%d %b at %H:%M')}."
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
    new_type: str = None,
) -> str:
    try:
        with _conn() as con:
            row = con.execute(
                "SELECT id, title, type, start_time, end_time, notes FROM events WHERE title LIKE ?",
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
            final_type  = new_type.lower() if new_type else row["type"]

            con.execute(
                "UPDATE events SET title = ?, type = ?, start_time = ?, end_time = ?, notes = ? WHERE id = ?",
                (final_title, final_type, new_dt.isoformat(), new_dt_end.isoformat(), final_notes, row["id"])
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
            "SELECT title, type, start_time, notes FROM events ORDER BY start_time"
        ).fetchall()

    if all_events:
        pass
    elif include_past:
        filtered = []
        for row in rows:
            dt = datetime.fromisoformat(row["start_time"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(TIMEZONE))
            if dt < now:
                filtered.append(row)
        rows = sorted(filtered, key=lambda r: r["start_time"], reverse=True)[:20]
    else:
        filtered = []
        for row in rows:
            dt = datetime.fromisoformat(row["start_time"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(TIMEZONE))
            if now <= dt <= until:
                filtered.append(row)
        rows = filtered

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
        type_label = EVENT_TYPES.get(row["type"], "📅 Event")
        lines.append(f"  - {dt.strftime('%d %b %Y %H:%M')} — {type_label}: {row['title']}")
        if row["notes"]:
            lines.append(f"    {row['notes']}")
    return "\n".join(lines)

#-------------------- events reminders --------------------

def add_event_reminder(event_id: str, offset_minutes: int) -> dict:
    if not (0 < offset_minutes <= 525600):
        raise ValueError("offset_minutes must be between 1 and 525600 (1 year).")

    reminder_id = str(uuid.uuid4())
    with _conn() as con:
        con.execute(
            "INSERT INTO event_reminders (id, event_id, offset_minutes, created_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (reminder_id, event_id, offset_minutes)
        )
    return {"id": reminder_id, "event_id": event_id, "offset_minutes": offset_minutes}


def list_event_reminders(event_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, event_id, offset_minutes, created_at FROM event_reminders WHERE event_id = ?",
            (event_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_event_reminder(reminder_id: str) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM event_reminders WHERE id = ?", (reminder_id,))
        return cur.rowcount > 0