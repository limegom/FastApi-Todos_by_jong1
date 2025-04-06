import sys
import os

# ����: ���� �׽�Ʈ ������ �θ� ���͸�(fastapi-app)�� �ƴ�, fastapi-app ���� ��ü�� sys.path�� �߰�
# ����: main.py�� fastapi-app ���� ���� ��ġ�ϹǷ�, �ش� ������ �߰��ؾ� import�� ����� ������
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fastapi-app')))

import pytest
from fastapi.testclient import TestClient
from main import app, save_todos, load_todos, TodoItem  # main.py�� fastapi-app ���� ���� �����ϹǷ� ����

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # �׽�Ʈ �� �ʱ�ȭ
    save_todos([])
    yield
    # �׽�Ʈ �� ����
    save_todos([])

def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_get_todos_with_items():
    todo = TodoItem(id=1, title="Test", description="Test description", completed=False)
    save_todos([todo.dict()])
    response = client.get("/todos")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test"

def test_create_todo():
    todo = {"id": 1, "title": "Test", "description": "Test description", "completed": False}
    response = client.post("/todos", json=todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Test"

def test_create_todo_invalid():
    todo = {"id": 1, "title": "Test"}
    response = client.post("/todos", json=todo)
    assert response.status_code == 422

def test_update_todo():
    todo = TodoItem(id=1, title="Test", description="Test description", completed=False)
    save_todos([todo.dict()])
    updated_todo = {"id": 1, "title": "Updated", "description": "Updated description", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"

def test_update_todo_not_found():
    updated_todo = {"id": 1, "title": "Updated", "description": "Updated description", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 404

def test_delete_todo():
    todo = TodoItem(id=1, title="Test", description="Test description", completed=False)
    save_todos([todo.dict()])
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"

def test_delete_todo_not_found():
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"
