from fastapi import APIRouter, Depends

from server.auth import verify_token
from app.memory.store import _conn

router = APIRouter()


@router.get("/notifications")
def get_notifications(token: str = Depends(verify_token)):
    with _conn() as con:
        rows = con.execute(
            "SELECT id, message, created_at FROM notifications WHERE read = 0 ORDER BY created_at"
        ).fetchall()
        if rows:
            ids = [r["id"] for r in rows]
            con.execute(
                f"UPDATE notifications SET read = 1 WHERE id IN ({','.join('?'*len(ids))})",
                ids
            )
        con.commit()
    return {"notifications": [{"id": r["id"], "message": r["message"]} for r in rows]}