import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from app.memory.store import init_db, _ensure_todo_columns
from server.routers import chat, weather, tasks, calendar, timers, notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _ensure_todo_columns()
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

app.include_router(chat.router)
app.include_router(weather.router)
app.include_router(tasks.router)
app.include_router(calendar.router)
app.include_router(timers.router)
app.include_router(notifications.router)


@app.get("/")
def root():
    return {"message": "Jarvis is running"}


@app.get("/health")
def health():
    return {"status": "ok"}