from fastapi import FastAPI, HTTPException
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

@app.get("/todos")
async def get_todos():
    return load_todos()

@app.post("/todos")
async def create_todo(item: TodoItem):
    todos = load_todos()
    todos.append(item.dict())
    save_todos(todos)
    return item

@app.get("/todos/{todo_id}")
async def read_todo(todo_id: int):
    todo = find_todo_by_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)
    return todo

@app.put("/todos/{todo_id}")
async def update_todo(todo_id: int, item: TodoItem):
    todos = load_todos()
    for i, t in enumerate(todos):
        if t["id"] == todo_id:
            todos[i] = item.dict()
            save_todos(todos)
            return item
    raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

@app.patch("/todos/{todo_id}")
async def patch_todo(todo_id: int, patch_data: dict):
    todos = load_todos()
    for t in todos:
        if t["id"] == todo_id:
            t.update(patch_data)
            save_todos(todos)
            return t
    raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

@app.delete("/todos/{todo_id}", response_model=dict)
async def delete_todo(todo_id: int):
    todos = load_todos()
    todos = [t for t in todos if t["id"] != todo_id]
    save_todos(todos)
    return {"message": DELETED_MSG}
