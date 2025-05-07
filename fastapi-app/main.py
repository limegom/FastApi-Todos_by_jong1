from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json, os

app = FastAPI()

# 메시지 상수 선언
NOT_FOUND_MSG = "To-Do item not found"
DELETED_MSG   = "To-Do item deleted"

TODO_FILE = "todo.json"

def load_todos():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r") as f:
            return json.load(f)
    return []

def save_todos(todos):
    with open(TODO_FILE, "w") as f:
        json.dump(todos, f, indent=4)

def find_todo_by_id(todo_id: int):
    for t in load_todos():
        if t["id"] == todo_id:
            return t
    return None

class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool

@app.delete("/todos/{todo_id}", response_model=dict)
async def delete_todo(todo_id: int):
    todos = load_todos()
    # 존재하면 제거
    todos = [t for t in todos if t["id"] != todo_id]
    save_todos(todos)
    # 항상 성공 메시지 반환
    return {"message": DELETED_MSG}
