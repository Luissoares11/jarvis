from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.memory.store import _conn
from app.utils import _now, TIMEZONE
from app.actions.timers import _push_notification


def check_event_reminders():
    now = _now()
    with _conn() as con:
        rows = con.execute(
            "SELECT er.id, er.offset_minutes, e.title, e.start_time "
            "FROM event_reminders er JOIN events e ON er.event_id = e.id"
        ).fetchall()

        for row in rows:
            event_dt = datetime.fromisoformat(row["start_time"])
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=ZoneInfo(TIMEZONE))

            trigger_at = event_dt - timedelta(minutes=row["offset_minutes"])

            if now >= trigger_at:
                _push_notification(f"📅 Reminder: '{row['title']}' is coming up.")
                con.execute("DELETE FROM event_reminders WHERE id = ?", (row["id"],))