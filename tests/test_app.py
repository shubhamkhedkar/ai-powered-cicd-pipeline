import pytest

from app.main import ITEMS, app


@pytest.fixture
def client():
    ITEMS.clear()
    return app.test_client()


def test_health(client):
    assert client.get("/health").json == {"status": "ok"}


def test_create_and_get(client):
    r = client.post("/items", json={"name": "a"})
    assert r.status_code == 201
    assert client.get("/items/1").json["name"] == "a"
    assert len(client.get("/items").json) == 1


def test_validation_and_404(client):
    assert client.post("/items", json={}).status_code == 400
    assert client.get("/items/99").status_code == 404
