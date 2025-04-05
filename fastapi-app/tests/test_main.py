import pytest
from fastapi.testclient import TestClient
from main import app, save_todos, TodoItem

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # �� �׽�Ʈ ���ķ� todo.json �ʱ�ȭ
    save_todos([])
    yield
    save_todos([])

def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_get_todos_with_items():
    # ������ To-Do �׸� �߰� �� ��� ��ȸ
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
    # ���� �� ��� Ȯ��
    todos = client.get("/todos").json()
    assert any(todo["id"] == 1 for todo in todos)

def test_create_todo_invalid():
    # �ʼ� �ʵ�(description ��) ����
    invalid_todo = {"id": 1, "title": "Invalid Task"}
    response = client.post("/todos", json=invalid_todo)
    assert response.status_code == 422

def test_update_todo():
    # ���� �׸� �߰� �� ������Ʈ
    todo = TodoItem(id=1, title="Task", description="Description", completed=False)
    save_todos([todo.dict()])
    updated_todo = {"id": 1, "title": "Updated Task", "description": "Updated Description", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 200
    result = response.json()
    assert result["title"] == "Updated Task"
    # ���� ��ȸ�� ������Ʈ Ȯ��
    response_get = client.get("/todos/1")
    assert response_get.status_code == 200
    assert response_get.json()["title"] == "Updated Task"

def test_update_todo_not_found():
    updated_todo = {"id": 1, "title": "Nonexistent", "description": "Does not exist", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 404

def test_delete_todo():
    # �׸� �߰� �� ���� ����
    todo = TodoItem(id=1, title="Task", description="Description", completed=False)
    save_todos([todo.dict()])
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"
    # ���� �� ��� Ȯ��
    response_get = client.get("/todos")
    assert len(response_get.json()) == 0

def test_delete_todo_not_found():
    # �������� �ʴ� �׸� ���� ��û �ÿ��� ���� ����
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"

def test_patch_todo():
    # �Ϸ� ���� ����(PATCH) ����
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
    # ���� �׸� ��ȸ ����
    todo = TodoItem(id=1, title="Task", description="Description", completed=False)
    save_todos([todo.dict()])
    response = client.get("/todos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_get_todo_by_id_not_found():
    response = client.get("/todos/1")
    assert response.status_code == 404

def test_read_root():
    # HTML ���� ��������Ʈ ��Ʈ("/") ����
    response = client.get("/")
    assert response.status_code == 200
    # index.html�� Ư�� �ؽ�Ʈ ���� ���� Ȯ��
    assert "Active To-Dos" in response.text
