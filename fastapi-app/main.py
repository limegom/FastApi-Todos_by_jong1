# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List
import json
import logging
from pathlib import Path
from threading import Lock
from prometheus_fastapi_instrumentator import Instrumentator

NOT_FOUND_DETAIL = "To-Do 아이템을 찾을 수 없습니다"

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Prometheus 메트릭스 엔드포인트 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 모델 정의
class TodoItem(BaseModel):
    id: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)
    completed: bool = Field(False)

class PatchTodo(BaseModel):
    completed: bool

# 파일 경로 및 동기화 잠금
TODO_FILE = Path("todo.json")
FILE_LOCK = Lock()

def load_todos() -> List[dict]:
    if TODO_FILE.exists():
        try:
            data = TODO_FILE.read_text(encoding="utf-8")
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error("JSON 디코딩 실패: %s", e)
            raise HTTPException(status_code=500, detail="To-Do 파일 읽기 실패")
    return []

def save_todos(todos: List[dict]) -> None:
    try:
        with FILE_LOCK:
            TODO_FILE.write_text(json.dumps(todos, indent=4), encoding="utf-8")
    except OSError as e:
        logger.error("파일 쓰기 실패: %s", e)
        raise HTTPException(status_code=500, detail="To-Do 파일 저장 실패")

@app.get("/todos", response_model=List[TodoItem])
def get_todos():
    return load_todos()

@app.post("/todos", response_model=TodoItem)
def create_todo(item: TodoItem):
    todos = load_todos()
    if any(t["id"] == item.id for t in todos):
        raise HTTPException(status_code=400, detail="이미 존재하는 ID입니다")
    todos.append(item.dict())
    save_todos(todos)
    return item

@app.get("/todos/{todo_id}", response_model=TodoItem)
def get_todo_by_id(todo_id: int):
    for t in load_todos():
        if t["id"] == todo_id:
            return t
    raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)

@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, updated: TodoItem):
    todos = load_todos()
    for idx, t in enumerate(todos):
        if t["id"] == todo_id:
            todos[idx] = updated.dict()
            save_todos(todos)
            return updated
    raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)

@app.patch("/todos/{todo_id}", response_model=TodoItem)
def patch_todo(todo_id: int, patch: PatchTodo):
    todos = load_todos()
    for idx, t in enumerate(todos):
        if t["id"] == todo_id:
            t["completed"] = patch.completed
            todos[idx] = t
            save_todos(todos)
            return t
    raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)

@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    filtered = [t for t in todos if t["id"] != todo_id]
    if len(filtered) == len(todos):
        raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)
    save_todos(filtered)
    return {"message": "To-Do 아이템이 삭제되었습니다"}

@app.get("/", response_class=HTMLResponse)
def read_root():
    template = Path("templates") / "index.html"
    try:
        content = template.read_text(encoding="utf-8")
    except OSError as e:
        logger.error("템플릿 로드 실패: %s", e)
        raise HTTPException(status_code=500, detail="템플릿 로드 실패")
    return HTMLResponse(content)
