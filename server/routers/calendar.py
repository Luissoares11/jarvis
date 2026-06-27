from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends

from server.auth import verify_token
from app.memory.store import _conn
from app.utils import TIMEZONE

router = APIRouter()


@router.get("/events")
def get_events(token: str = Depends(verify_token)):
    now = datetime.now(ZoneInfo(TIMEZONE))
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, type, start_time, end_time, notes, recurrence "
            "FROM events ORDER BY start_time"
        ).fetchall()

    future = []
    for r in rows:
        dt = datetime.fromisoformat(r["start_time"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(TIMEZONE))
        if dt >= now:
            future.append(dict(r))

    return {"events": future}