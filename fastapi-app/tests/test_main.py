from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json, os

app = FastAPI()

# 메시지 상수
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

class PatchTodo(BaseModel):
    completed: bool

# 전체 조회
@app.get("/todos", response_model=list[TodoItem])
def get_todos():
    return load_todos()

# 생성
@app.post("/todos", response_model=TodoItem)
def create_todo(todo: TodoItem):
    todos = load_todos()
    todos.append(todo.dict())
    save_todos(todos)
    return todo

# 단건 조회
@app.get("/todos/{todo_id}", response_model=TodoItem)
def read_todo(todo_id: int):
    todo = find_todo_by_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)
    return todo

# 수정
@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, updated: TodoItem):
    todos = load_todos()
    for i, t in enumerate(todos):
        if t["id"] == todo_id:
            todos[i] = updated.dict()
            save_todos(todos)
            return updated
    raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

# 삭제 (idempotent)
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    todos = [t for t in todos if t["id"] != todo_id]
    save_todos(todos)
    return {"message": DELETED_MSG}

# 완료 상태 변경
@app.patch("/todos/{todo_id}", response_model=TodoItem)
def patch_todo(todo_id: int, patch: PatchTodo):
    todo = find_todo_by_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)
    todos = load_todos()
    for t in todos:
        if t["id"] == todo_id:
            t["completed"] = patch.completed
            save_todos(todos)
            return t
    # (실제로 여기까지 오지 않음)
    raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

# HTML 서빙
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
