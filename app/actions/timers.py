import re
import uuid
import threading
from datetime import timedelta

from app.memory.store import _conn
from app.utils import _now, _parse_datetime

# ── notifications helper ─────────────────────────────────────

def _push_notification(message: str):
    with _conn() as con:
        con.execute(
            "INSERT INTO notifications (id, message, read, created_at) "
            "VALUES (?, ?, 0, datetime('now'))",
            (str(uuid.uuid4()), message)
        )

# ── reminders ─────────────────────────────────────────────────

_reminder_threads: dict[str, threading.Timer] = {}


def _fire_reminder(reminder_id: str, message: str):
    print(f"\n⏰ Jarvis Reminder: {message}\n")
    with _conn() as con:
        con.execute("UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,))
    _reminder_threads.pop(reminder_id, None)
    _push_notification(f"⏰ Reminder: {message}")


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
    from datetime import datetime
    with _conn() as con:
        rows = con.execute(
            "SELECT message, remind_at FROM reminders WHERE fired = 0 ORDER BY remind_at"
        ).fetchall()

    if not rows:
        return "No pending reminders."

    lines = ["Pending reminders:"]
    for row in rows:
        from datetime import datetime
        dt = datetime.fromisoformat(row["remind_at"])
        lines.append(f"  - '{row['message']}' at {dt.strftime('%H:%M on %d %b')}")
    return "\n".join(lines)


def load_pending_reminders():
    """Re-arm any reminders that survived a restart."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.utils import TIMEZONE

    now = _now()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, message, remind_at FROM reminders WHERE fired = 0"
        ).fetchall()

    for row in rows:
        dt = datetime.fromisoformat(row["remind_at"])
        dt = dt.replace(tzinfo=ZoneInfo(TIMEZONE)) if dt.tzinfo is None else dt

        if dt <= now:
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
    _push_notification(f"⏱️ Timer done: {label}")
    


def set_timer(duration_str: str, label: str = "Timer") -> str:
    try:
        duration_str = duration_str.strip().lower()
        seconds = 0

        h = re.search(r"(\d+)\s*h(?:our)?s?", duration_str)
        m = re.search(r"(\d+)\s*m(?:in(?:ute)?)?s?", duration_str)
        s = re.search(r"(\d+)\s*s(?:ec(?:ond)?)?s?", duration_str)

        if h: seconds += int(h.group(1)) * 3600
        if m: seconds += int(m.group(1)) * 60
        if s: seconds += int(s.group(1))

        if seconds == 0:
            if duration_str.isdigit():
                seconds = int(duration_str) * 60
            else:
                return "I couldn't understand that duration."

        timer_id = str(uuid.uuid4())
        end_time = _now() + timedelta(seconds=seconds)
        timer = threading.Timer(seconds, _fire_timer, args=[timer_id, label])
        timer.daemon = True
        timer.start()
        _timer_threads[timer_id] = {
            "timer": timer,
            "label": label,
            "ends_at": end_time.isoformat(),
        }

        mins = seconds // 60
        secs = seconds % 60
        duration_display = f"{mins}m {secs}s" if secs else f"{mins}m"
        if mins >= 60:
            duration_display = f"{mins//60}h {mins%60}m" if mins % 60 else f"{mins//60}h"

        return f"Timer set for {duration_display}: '{label}'."
    except Exception as e:
        return f"I couldn't set that timer: {e}"


def set_alarm(time_str: str, label: str = "Wake up") -> str:
    return add_reminder(label, time_str, "today")