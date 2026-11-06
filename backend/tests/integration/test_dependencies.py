from fastapi import Depends
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_storage
from app.main import create_app


def test_route_with_get_current_user_stub_returns_401():
    app = create_app()

    @app.get("/protected")
    def protected(user=Depends(get_current_user)):
        return {"ok": True}

    response = TestClient(app).get("/protected", headers={"Authorization": "Bearer qualquer"})

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"
    assert response.headers["www-authenticate"] == "Bearer"


def test_get_current_user_override_returns_fixture_user():
    app = create_app()

    @app.get("/protected")
    def protected(user=Depends(get_current_user)):
        return user

    app.dependency_overrides[get_current_user] = lambda: {"username": "fixture"}

    response = TestClient(app).get("/protected")

    assert response.status_code == 200
    assert response.json() == {"username": "fixture"}


def test_get_storage_override_returns_fake_storage():
    app = create_app()

    @app.get("/storage")
    def storage(storage=Depends(get_storage)):
        return {"backend": storage}

    app.dependency_overrides[get_storage] = lambda: "fake"

    response = TestClient(app).get("/storage")

    assert response.json() == {"backend": "fake"}
