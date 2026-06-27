from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from server.auth import verify_token
from server.sessions import get_session
from app.core import process_input

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, token: str = Depends(verify_token)):
    try:
        session_ctx = get_session(request.session_id)
        response = process_input(request.message, ctx=session_ctx)
        return ChatResponse(response=response, session_id=request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))