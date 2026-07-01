from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.auth import verify_token
from app.memory.store import _conn
from app.features.calendar import add_event_reminder, list_event_reminders, delete_event_reminder

router = APIRouter()


@router.get("/events")
def get_events(token: str = Depends(verify_token)):
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, type, start_time, end_time, notes, recurrence "
            "FROM events ORDER BY start_time"
        ).fetchall()
    return {"events": [dict(r) for r in rows]}

class ReminderCreate(BaseModel):
    offset_minutes: int


@router.get("/events/{event_id}/reminders")
def get_event_reminders(event_id: str, token: str = Depends(verify_token)):
    return {"reminders": list_event_reminders(event_id)}


@router.post("/events/{event_id}/reminders")
def create_event_reminder(event_id: str, body: ReminderCreate, token: str = Depends(verify_token)):
    try:
        return add_event_reminder(event_id, body.offset_minutes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/events/{event_id}/reminders/{reminder_id}")
def remove_event_reminder(event_id: str, reminder_id: str, token: str = Depends(verify_token)):
    deleted = delete_event_reminder(reminder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"ok": True}