from fastapi import FastAPI, Query
from app.core import process_input

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Jarvis is running"}


@app.post("/chat")
def chat(input: str = Query(...)):
    return {"response": process_input(input)}