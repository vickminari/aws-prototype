"""Proteção CSRF por padrão em todas as rotas de escrita da aplicação."""

import pytest
from sqlalchemy import func, select

from app.models import RevokedToken, User

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
KNOWN_WRITES = {
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("PATCH", "/api/users/me"),
    ("PUT", "/api/users/me/password"),
    ("POST", "/api/users/me/avatar"),
    ("DELETE", "/api/users/me/avatar"),
}


def write_routes(app):
    """Lista as escritas pelo OpenAPI; `app.routes` não expõe routers incluídos nesta versão."""
    return sorted(
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() not in SAFE_METHODS
    )


def database_state(db_session, user):
    db_session.expire_all()
    current = db_session.get(User, user.id)
    return (
        db_session.scalar(select(func.count()).select_from(User)),
        db_session.scalar(select(func.count()).select_from(RevokedToken)),
        current.full_name,
        current.hashed_password,
        current.profile_image_key,
    )


def test_known_write_routes_are_inspected(app):
    assert set(write_routes(app)) >= KNOWN_WRITES


@pytest.mark.parametrize("defect", ["no_token", "wrong_token", "untrusted_origin"])
def test_every_write_route_rejects_invalid_csrf_without_side_effects(
    app, logged_client, logged_user, db_session, defect
):
    before = database_state(db_session, logged_user)
    if defect == "no_token":
        logged_client.headers.pop("X-CSRF-Token")
    elif defect == "wrong_token":
        logged_client.headers["X-CSRF-Token"] = "forjado"
    else:
        logged_client.headers["Origin"] = "https://evil.example.com"

    for method, path in write_routes(app):
        assert "{" not in path, f"Inclua valores de exemplo para {path}"
        response = logged_client.request(method, path)

        assert response.status_code == 403, (method, path)
        assert response.json()["code"] == "CSRF_INVALID", (method, path)

    assert database_state(db_session, logged_user) == before
    assert logged_client.get("/api/users/me").status_code == 200


def test_register_without_pre_session_is_rejected(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Maria Silva",
            "username": "maria",
            "email": "maria@example.com",
            "password": "Senha-forte-123",
        },
        headers={"Origin": "http://testserver"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert db_session.scalar(select(func.count()).select_from(User)) == 0


def test_logged_client_updates_profile_and_password(logged_client, logged_user):
    profile = logged_client.patch("/api/users/me", json={"full_name": "Nome pela sessão"})
    password = logged_client.put(
        "/api/users/me/password",
        json={"current_password": "Senha-de-teste-123", "new_password": "Outra-senha-456"},
    )

    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Nome pela sessão"
    assert password.status_code == 204


def test_write_with_valid_csrf_but_without_session_returns_401(csrf_client):
    response = csrf_client.patch("/api/users/me", json={"full_name": "Sem sessão"})

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"
    assert "bearer" not in response.headers["www-authenticate"].lower()


def test_openapi_documents_csrf_failure_on_every_write(app, client):
    paths = client.get("/api/openapi.json").json()["paths"]

    for method, path in write_routes(app):
        responses = paths[path][method.lower()]["responses"]
        assert "403" in responses, (method, path)
