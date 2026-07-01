from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from server.auth import verify_token
from app.features.tasks import list_boards, add_board, delete_board, list_todos_by_board, add_todo_to_board, set_todo_done, delete_todo_by_id

router = APIRouter()


class BoardCreate(BaseModel):
    title: str


class TodoCreate(BaseModel):
    board_id: str
    task: str
    priority: str = "normal"
    due_time: Optional[str] = None


@router.get("/boards")
def get_boards(token: str = Depends(verify_token)):
    return {"boards": list_boards()}


@router.post("/boards")
def create_board(body: BoardCreate, token: str = Depends(verify_token)):
    return add_board(body.title.strip())


@router.delete("/boards/{board_id}")
def remove_board(board_id: str, token: str = Depends(verify_token)):
    delete_board(board_id)
    return {"ok": True}


@router.get("/boards/{board_id}/tasks")
def get_board_tasks(board_id: str, token: str = Depends(verify_token)):
    return {"tasks": list_todos_by_board(board_id)}


@router.post("/tasks")
def create_task(body: TodoCreate, token: str = Depends(verify_token)):
    return add_todo_to_board(body.board_id, body.task.strip(), body.priority, body.due_time)


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, done: bool, token: str = Depends(verify_token)):
    set_todo_done(task_id, done)
    return {"ok": True}


@router.delete("/tasks/{task_id}")
def remove_task(task_id: str, token: str = Depends(verify_token)):
    delete_todo_by_id(task_id)
    return {"ok": True}