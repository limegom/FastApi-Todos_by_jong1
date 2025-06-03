# main.py

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
import json
import logging
import time
from multiprocessing import Queue
from os import getenv
from fastapi import Request
from pathlib import Path
from threading import Lock
from prometheus_fastapi_instrumentator import Instrumentator
from logging_loki import LokiQueueHandler


NOT_FOUND_DETAIL = "To-Do 아이템을 찾을 수 없습니다"
TODO_FILE = Path("todo.json")
FILE_LOCK = Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Prometheus 메트릭스 엔드포인트 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

instrumentator = Instrumentator()
instrumentator.instrument(app)
instrumentator.expose(app)

loki_logs_handler = LokiQueueHandler(
    Queue(-1),
    url=getenv("LOKI_ENDPOINT"),
    tags={"application": "fastapi"},
    version="1",
)

# Custom access logger (ignore Uvicorn's default logging)
custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)

# Add Loki handler (assuming `loki_logs_handler` is correctly configured)
custom_logger.addHandler(loki_logs_handler)

async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time  # Compute response time

    log_message = (
        f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" {response.status_code} {duration:.3f}s'
    )

    # **Only log if duration exists**
    if duration:
        custom_logger.info(log_message)

    return response

app.middleware("http")(log_requests)

class TodoItem(BaseModel):
    id: int
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    completed: bool = False
    created_at: Optional[str] = None
    due_date: Optional[str] = None      # YYYY-MM-DD 포맷
    days_left: Optional[int] = None     # D-day 용 계산 필드

def load_todos() -> List[dict]:
    try:
        data = TODO_FILE.read_text(encoding="utf-8")
        return json.loads(data)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        logger.error("JSON 디코딩 실패: %s", e)
        raise HTTPException(status_code=500, detail="To-Do 파일 읽기 실패")

def save_todos(todos: List[dict]) -> None:
    try:
        with FILE_LOCK:
            TODO_FILE.write_text(
                json.dumps(todos, indent=4, ensure_ascii=False), encoding="utf-8"
            )
    except OSError as e:
        logger.error("파일 쓰기 실패: %s", e)
        raise HTTPException(status_code=500, detail="To-Do 파일 저장 실패")

def compute_days_left(due: Optional[str]) -> Optional[int]:
    if not due:
        return None
    try:
        d = date.fromisoformat(due)
        return (d - datetime.utcnow().date()).days
    except ValueError:
        return None


@app.get("/todos", response_model=List[TodoItem])
def get_todos():
    todos = load_todos()
    # 각 항목에 days_left 계산값 추가
    for t in todos:
        t["days_left"] = compute_days_left(t.get("due_date"))
    return sorted(todos, key=lambda t: t.get("completed", False))

@app.post("/todos", response_model=TodoItem)
def create_todo(item: TodoItem):
    todos = load_todos()
    if any(t["id"] == item.id for t in todos):
        raise HTTPException(status_code=400, detail="이미 존재하는 ID입니다")
    if not item.created_at:
        item.created_at = datetime.utcnow().isoformat()
    todos.append(item.model_dump())
    save_todos(todos)
    return item

@app.get("/todos/search", response_model=List[TodoItem])
def search_todos(query: str = Query(..., min_length=1)):
    todos = load_todos()
    q = query.lower()
    return [t for t in todos
            if q in t["title"].lower()
            or (t.get("description") and q in t["description"].lower())]

@app.get("/todos/{todo_id}", response_model=TodoItem)
def get_todo_by_id(todo_id: int):
    for t in load_todos():
         if t["id"] == todo_id:
            t["days_left"] = compute_days_left(t.get("due_date"))
            return t
    raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)

@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, item: TodoItem):
    todos = load_todos()
    for idx, t in enumerate(todos):
        if t["id"] == todo_id:
            updated = item.model_dump()
            updated["id"] = todo_id
            updated["created_at"] = t["created_at"]
            updated["days_left"] = compute_days_left(updated.get("due_date"))
            todos[idx] = updated
            save_todos(todos)
            return updated
    raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)

@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    remaining = [t for t in todos if t["id"] != todo_id]
    if len(remaining) == len(todos):
        raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)
    save_todos(remaining)
    return {"message": "To-Do 아이템이 삭제되었습니다"}

@app.delete("/todos/completed", response_model=dict)
def delete_completed_todos():
    todos = load_todos()
    remaining = [t for t in todos if not t.get("completed", False)]
    deleted_count = len(todos) - len(remaining)
    save_todos(remaining)
    return {"message": f"완료된 To-Do 아이템 {deleted_count}개를 삭제했다"}

@app.get("/", response_class=HTMLResponse)
def read_root():
    template = Path("templates") / "index.html"
    try:
        content = template.read_text(encoding="utf-8")
    except OSError as e:
        logger.error("템플릿 로드 실패: %s", e)
        raise HTTPException(status_code=500, detail="템플릿 로드 실패")
    return HTMLResponse(content)

@app.patch("/todos/{todo_id}/complete", response_model=TodoItem, status_code=status.HTTP_200_OK)
def complete_todo(todo_id: int):
    todos = load_todos()
    for idx, t in enumerate(todos):
        if t["id"] == todo_id:
            todos[idx]["completed"] = not t.get("completed", False)
            save_todos(todos)
            return todos[idx]
    raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)

# 반복 To-Do 저장 파일
REPEAT_FILE = Path("repeating_todos.json")

class RepeatingTodo(BaseModel):
    id: int
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    repeat_type: str = Field(..., pattern="^(daily|weekly)$")  # ✅ 수정됨
    repeat_days: Optional[List[int]] = []  # 0=Sun ~ 6=Sat

def load_repeating() -> List[dict]:
    try:
        return json.loads(REPEAT_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        logger.error("반복 항목 JSON 디코딩 실패: %s", e)
        raise HTTPException(status_code=500, detail="반복 항목 로딩 실패")

def save_repeating(items: List[dict]) -> None:
    try:
        with FILE_LOCK:
            REPEAT_FILE.write_text(
                json.dumps(items, indent=4, ensure_ascii=False), encoding="utf-8"
            )
    except OSError as e:
        logger.error("반복 항목 저장 실패: %s", e)
        raise HTTPException(status_code=500, detail="반복 항목 저장 실패")
@app.get("/repeating", response_model=List[RepeatingTodo])
def get_repeating_todos():
    return load_repeating()

@app.post("/repeating", response_model=RepeatingTodo)
def create_repeating_todo(item: RepeatingTodo):
    items = load_repeating()
    if any(x["id"] == item.id for x in items):
        raise HTTPException(status_code=400, detail="이미 존재하는 ID입니다")
    items.append(item.model_dump())
    save_repeating(items)
    return item

@app.delete("/repeating/{item_id}", response_model=dict)
def delete_repeating_todo(item_id: int):
    items = load_repeating()
    remaining = [x for x in items if x["id"] != item_id]
    if len(items) == len(remaining):
        raise HTTPException(status_code=404, detail="반복 항목을 찾을 수 없습니다")
    save_repeating(remaining)
    return {"message": "반복 항목이 삭제되었습니다"}
