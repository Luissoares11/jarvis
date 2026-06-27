from fastapi import APIRouter, Depends

from server.auth import verify_token
from app.memory.store import _conn

router = APIRouter()


@router.get("/events")
def get_events(token: str = Depends(verify_token)):
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, type, start_time, end_time, notes, recurrence "
            "FROM events ORDER BY start_time"
        ).fetchall()
    return {"events": [dict(r) for r in rows]}