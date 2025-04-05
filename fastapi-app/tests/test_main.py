import pytest
from fastapi.testclient import TestClient
from main import app, save_todos, TodoItem

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # 각 테스트 전후로 todo.json 초기화
    save_todos([])
    yield
    save_todos([])

def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_get_todos_with_items():
    # 임의의 To-Do 항목 추가 후 목록 조회
    todo = TodoItem(id=1, title="Test", description="Test description", completed=False)
    save_todos([todo.dict()])
    response = client.get("/todos")
    assert response.status_code == 200
    todos = response.json()
    assert isinstance(todos, list)
    assert len(todos) == 1
    assert todos[0]["title"] == "Test"

def test_create_todo():
    new_todo = {"id": 1, "title": "New Task", "description": "New description", "completed": False}
    response = client.post("/todos", json=new_todo)
    assert response.status_code == 200
    result = response.json()
    assert result["title"] == "New Task"
    # 생성 후 목록 확인
    todos = client.get("/todos").json()
    assert any(todo["id"] == 1 for todo in todos)

def test_create_todo_invalid():
    # 필수 필드(description 등) 누락
    invalid_todo = {"id": 1, "title": "Invalid Task"}
    response = client.post("/todos", json=invalid_todo)
    assert response.status_code == 422

def test_update_todo():
    # 기존 항목 추가 후 업데이트
    todo = TodoItem(id=1, title="Task", description="Description", completed=False)
    save_todos([todo.dict()])
    updated_todo = {"id": 1, "title": "Updated Task", "description": "Updated Description", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 200
    result = response.json()
    assert result["title"] == "Updated Task"
    # 개별 조회로 업데이트 확인
    response_get = client.get("/todos/1")
    assert response_get.status_code == 200
    assert response_get.json()["title"] == "Updated Task"

def test_update_todo_not_found():
    updated_todo = {"id": 1, "title": "Nonexistent", "description": "Does not exist", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 404

def test_delete_todo():
    # 항목 추가 후 삭제 검증
    todo = TodoItem(id=1, title="Task", description="Description", completed=False)
    save_todos([todo.dict()])
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"
    # 삭제 후 목록 확인
    response_get = client.get("/todos")
    assert len(response_get.json()) == 0

def test_delete_todo_not_found():
    # 존재하지 않는 항목 삭제 요청 시에도 정상 응답
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"

def test_patch_todo():
    # 완료 상태 변경(PATCH) 검증
    todo = TodoItem(id=1, title="Task", description="Description", completed=False)
    save_todos([todo.dict()])
    patch_data = {"completed": True}
    response = client.patch("/todos/1", json=patch_data)
    assert response.status_code == 200
    assert response.json()["completed"] == True

def test_patch_todo_not_found():
    patch_data = {"completed": True}
    response = client.patch("/todos/1", json=patch_data)
    assert response.status_code == 404

def test_get_todo_by_id():
    # 개별 항목 조회 검증
    todo = TodoItem(id=1, title="Task", description="Description", completed=False)
    save_todos([todo.dict()])
    response = client.get("/todos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_get_todo_by_id_not_found():
    response = client.get("/todos/1")
    assert response.status_code == 404

def test_read_root():
    # HTML 서빙 엔드포인트 루트("/") 검증
    response = client.get("/")
    assert response.status_code == 200
    # index.html의 특정 텍스트 존재 여부 확인
    assert "Active To-Dos" in response.text
