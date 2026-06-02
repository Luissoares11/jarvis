import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime

load_dotenv()

from app.core import process_input
from app.memory.store import init_db
from app.memory.context import make_context

JARVIS_TOKEN = os.getenv("JARVIS_API_TOKEN", "changeme")
security = HTTPBearer()

# ── session store ─────────────────────────────────────────────
# maps session_id → context dict
_sessions: dict[str, dict] = {}

def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = make_context()
    return _sessions[session_id]


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != JARVIS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.credentials


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

os.makedirs("data/plots", exist_ok=True)
app.mount("/plots", StaticFiles(directory="data/plots"), name="plots")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Jarvis is running"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, token: str = Depends(verify_token)):
    try:
        session_ctx = get_session(request.session_id)
        response = process_input(request.message, ctx=session_ctx)
        return ChatResponse(response=response, session_id=request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/notifications")
def get_notifications(token: str = Depends(verify_token)):
    from app.memory.store import _conn
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
    
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/timers")
def get_timers(token: str = Depends(verify_token)):
    from app.actions import _timer_threads
    from app.actions import _now
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
                "remaining_seconds": int(remaining)
            })
    return {"timers": result}