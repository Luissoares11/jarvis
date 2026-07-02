import os
import subprocess
import threading
from fastapi import APIRouter, HTTPException, Header

router = APIRouter()

DEPLOY_SECRET = os.getenv("DEPLOY_SECRET")


def _run_deploy():
    subprocess.run(
        ["bash", "-c", "cd ~/jarvis && git pull && docker compose build && docker compose up -d"],
        timeout=300,
    )


@router.post("/deploy")
def deploy(x_deploy_secret: str = Header(...)):
    if x_deploy_secret != DEPLOY_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    thread = threading.Thread(target=_run_deploy, daemon=True)
    thread.start()

    return {"ok": True, "message": "Deploy started."}