# test_main.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pytest
from fastapi.testclient import TestClient

import main  # main.py에 정의된 app, TODO_FILE, NOT_FOUND_MSG 사용

client = TestClient(main.app)

@pytest.fixture(autouse=True)
def isolate_todo_file(tmp_path, monkeypatch):
    # 테스트용 JSON 파일 경로 설정
    test_file = tmp_path / "todo_test.json"
    monkeypatch.setattr(main, "TODO_FILE", str(test_file))
    return test_file

def read_file(path):
    with open(path, "r") as f:
        return json.load(f)

def test_get_empty_list():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_create_and_read_todo():
    payload = {
        "id": 1,
        "title": "Test Task",
        "description": "테스트 설명",
        "completed": False
    }
    # 생성
    resp = client.post("/todos", json=payload)
    assert resp.status_code == 200
    assert resp.json() == payload

    # 파일에 저장되었는지 확인
    file_data = read_file(str(isolate_todo_file))
    assert file_data == [payload]

    # 단일 조회
    resp2 = client.get("/todos/1")
    assert resp2.status_code == 200
    assert resp2.json() == payload

def test_read_not_found():
    resp = client.get("/todos/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == main.NOT_FOUND_MSG

def test_update_todo():
    # 먼저 생성
    client.post("/todos", json={"id":2, "title":"Old","description":"Desc","completed":False})
    update_payload = {"id":2, "title":"New Title","description":"Desc","completed":True}
    resp = client.put("/todos/2", json=update_payload)
    assert resp.status_code == 200
    assert resp.json() == update_payload

    # 파일 반영 확인
    file_data = read_file(str(isolate_todo_file))
    assert file_data[0]["title"] == "New Title"
    assert file_data[0]["completed"] is True

def test_delete_todo():
    # 생성 후 삭제
    client.post("/todos", json={"id":3, "title":"Del","description":"","completed":False})
    resp = client.delete("/todos/3")
    assert resp.status_code == 200
    assert resp.json() == {"message": "To-Do item deleted"}

    # 파일에서 제거 확인
    file_data = read_file(str(isolate_todo_file))
    assert all(item["id"] != 3 for item in file_data)

def test_patch_todo():
    # 생성 후 patch
    client.post("/todos", json={"id":4, "title":"Patch","description":"","completed":False})
    resp = client.patch("/todos/4", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["completed"] is True

    # 파일 반영 확인
    file_data = read_file(str(isolate_todo_file))
    assert file_data[0]["completed"] is True
