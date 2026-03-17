from fastapi import FastAPI
from app.core import process_input

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Jarvis is running"}

@app.post("/chat")
def chat(input: str):
    response = process_input(input)
    return {"response": response}