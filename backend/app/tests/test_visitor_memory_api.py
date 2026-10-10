from fastapi.testclient import TestClient

from main import app


def test_clear_visitor_memory_endpoint_is_reachable():
    client = TestClient(app)
    response = client.delete("/api/chat/visitor-memory/unknown-visitor-xyz")
    assert response.status_code == 200
    assert response.json()["deleted"] == 0


def test_clear_visitor_memory_rejects_overlong_id():
    client = TestClient(app)
    response = client.delete("/api/chat/visitor-memory/" + "x" * 200)
    assert response.status_code == 200
    assert response.json()["deleted"] == 0
