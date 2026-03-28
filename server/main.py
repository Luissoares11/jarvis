from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from app.core import process_input
from app.memory.store import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Jarvis is running"}


@app.post("/chat")
def chat(input: str = Query(...)):
    return {"response": process_input(input)}