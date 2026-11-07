from fastapi import Depends
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_db, get_storage
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


def test_get_db_yields_session_and_closes_it_at_the_end(monkeypatch):
    closed = []

    class FakeSession:
        def close(self):
            closed.append(True)

    monkeypatch.setattr("app.dependencies.SessionLocal", FakeSession)
    dependency = get_db()

    session = next(dependency)
    assert isinstance(session, FakeSession)
    assert closed == []

    dependency.close()
    assert closed == [True]


def test_auth_user_fixture_is_returned_by_get_current_user(app, client, auth_user):
    @app.get("/me-test")
    def me(user=Depends(get_current_user)):
        return {"id": str(user.id), "username": user.username}

    response = client.get("/me-test")

    assert response.status_code == 200
    assert response.json() == {"id": str(auth_user.id), "username": auth_user.username}
