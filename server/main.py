import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

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
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)