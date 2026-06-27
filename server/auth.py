import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JARVIS_TOKEN = os.getenv("JARVIS_API_TOKEN", "changeme")
security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != JARVIS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.credentials