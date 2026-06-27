from datetime import datetime
from fastapi import APIRouter, Depends

from server.auth import verify_token
from app.actions import _timer_threads, _now

router = APIRouter()


@router.get("/timers")
def get_timers(token: str = Depends(verify_token)):
    now = _now()
    result = []
    for timer_id, data in _timer_threads.items():
        ends_at = datetime.fromisoformat(data["ends_at"])
        remaining = (ends_at - now).total_seconds()
        if remaining > 0:
            result.append({
                "id": timer_id,
                "label": data["label"],
                "ends_at": data["ends_at"],
                "remaining_seconds": int(remaining),
            })
    return {"timers": result}