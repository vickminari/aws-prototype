from datetime import UTC, datetime
from http.cookies import SimpleCookie

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.dependencies import get_db
from app.main import create_app
from app.models import RevokedToken
from app.services import auth_service

ORIGIN = "https://app.example.com"
PASSWORD = "Senha-de-teste-123"
LOGOUT_URL = "/api/auth/logout"
ME_URL = "/api/users/me"


@pytest.fixture(params=["test", "prod"])
def logout_settings(request):
    return Settings(
        _env_file=None,
        environment=request.param,
        jwt_secret="jwt-exclusivo-dos-testes-0000000000000000",
        jwt_expire_minutes=30,
        csrf_secret="csrf-exclusivo-dos-testes-00000000000000",
        csrf_trusted_origins=[ORIGIN],
    )


@pytest.fixture
def logout_app(db_session, logout_settings):
    app = create_app(logout_settings)
    app.dependency_overrides[get_db] = lambda: db_session
    yield app
    app.dependency_overrides.clear()


def new_client(app):
    return TestClient(app, base_url=ORIGIN)


@pytest.fixture
def logout_client(logout_app):
    with new_client(logout_app) as client:
        yield client


@pytest.fixture
def logout_user(user_factory):
    return user_factory(username="maria.silva", email="maria@example.com", password=PASSWORD)


def name(settings, cookie):
    return ("__Host-" if settings.environment == "prod" else "") + cookie


def csrf_headers(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def login(client, user):
    response = client.post(
        "/api/auth/login",
        data={"username": user.username, "password": PASSWORD},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    return csrf_headers(client)


def revoked_count(db_session):
    return db_session.scalar(select(func.count()).select_from(RevokedToken))


def set_cookies(response):
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    return cookies


def restore(client, settings, saved):
    for cookie, value in saved.items():
        client.cookies.set(cookie, value, domain="app.example.com", path="/")


def test_logout_revokes_session_and_clears_cookies(
    logout_client, logout_settings, logout_user, db_session
):
    headers = login(logout_client, logout_user)
    token = logout_client.cookies[name(logout_settings, "access_token")]
    claims = jwt.decode(token, logout_settings.jwt_secret, algorithms=["HS256"])

    response = logout_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    cleared = set_cookies(response)
    for cookie in ("access_token", "csrf_token"):
        morsel = cleared[name(logout_settings, cookie)]
        assert int(morsel["max-age"]) == 0
        assert morsel["path"] == "/"
        assert morsel["httponly"] is True
        assert morsel["samesite"].lower() == "lax"
        assert bool(morsel["secure"]) is (logout_settings.environment == "prod")
        assert name(logout_settings, cookie) not in logout_client.cookies
    saved = db_session.get(RevokedToken, claims["jti"])
    assert saved.user_id == logout_user.id
    assert saved.expires_at == datetime.fromtimestamp(claims["exp"], UTC)
    assert logout_client.get(ME_URL).status_code == 401


def test_copy_of_logged_out_jwt_is_rejected(logout_client, logout_settings, logout_user):
    headers = login(logout_client, logout_user)
    token = logout_client.cookies[name(logout_settings, "access_token")]
    assert logout_client.post(LOGOUT_URL, headers=headers).status_code == 204

    copy = new_client(logout_client.app)
    restore(copy, logout_settings, {name(logout_settings, "access_token"): token})

    response = copy.get(ME_URL)
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"


def test_new_login_after_logout_works(logout_client, logout_user):
    headers = login(logout_client, logout_user)
    assert logout_client.post(LOGOUT_URL, headers=headers).status_code == 204

    login(logout_client, logout_user)

    assert logout_client.get(ME_URL).status_code == 200


@pytest.mark.parametrize("defect", ["no_csrf", "wrong_csrf", "untrusted_origin"])
def test_logout_requires_csrf_and_keeps_session(
    logout_client, logout_user, db_session, monkeypatch, defect
):
    headers = login(logout_client, logout_user)

    def must_not_logout(*args, **kwargs):
        pytest.fail("O logout não deve executar após falha CSRF")

    monkeypatch.setattr(auth_service, "logout", must_not_logout)
    if defect == "no_csrf":
        del headers["X-CSRF-Token"]
    elif defect == "wrong_csrf":
        headers["X-CSRF-Token"] = "forjado"
    else:
        headers["Origin"] = "https://evil.example.com"

    response = logout_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert revoked_count(db_session) == 0
    assert logout_client.get(ME_URL).status_code == 200


def test_repeated_logout_with_copied_session_is_idempotent(
    logout_client, logout_settings, logout_user, db_session
):
    """Outra aba ou cópia dos cookies repete o logout: 204, sem duplicar a revogação."""
    headers = login(logout_client, logout_user)
    saved = {
        cookie: logout_client.cookies[cookie]
        for cookie in (name(logout_settings, "access_token"), name(logout_settings, "csrf_token"))
    }
    assert logout_client.post(LOGOUT_URL, headers=headers).status_code == 204

    copy = new_client(logout_client.app)
    restore(copy, logout_settings, saved)
    response = copy.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert revoked_count(db_session) == 1


def test_repeated_logout_after_cookies_were_cleared_still_requires_csrf(
    logout_client, logout_user, db_session
):
    headers = login(logout_client, logout_user)
    assert logout_client.post(LOGOUT_URL, headers=headers).status_code == 204

    response = logout_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert revoked_count(db_session) == 1


def test_logout_with_pre_session_only_returns_204_without_revoking(
    logout_client, logout_settings, db_session
):
    headers = csrf_headers(logout_client)

    response = logout_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert revoked_count(db_session) == 0
    assert name(logout_settings, "csrf_token") not in logout_client.cookies
    assert name(logout_settings, "csrf_session") not in logout_client.cookies


def test_logout_of_one_session_keeps_other_session_of_same_user(logout_client, logout_user):
    headers = login(logout_client, logout_user)
    with new_client(logout_client.app) as other:
        login(other, logout_user)

        assert logout_client.post(LOGOUT_URL, headers=headers).status_code == 204

        assert logout_client.get(ME_URL).status_code == 401
        assert other.get(ME_URL).status_code == 200


def test_logout_openapi_describes_responses(logout_client):
    operation = logout_client.get("/api/openapi.json").json()["paths"][LOGOUT_URL]["post"]

    assert {"204", "403"} <= set(operation["responses"])
    assert "content" not in operation["responses"]["204"]


def test_logout_of_removed_user_clears_cookies_without_revoking(
    logout_client, logout_settings, logout_user, db_session
):
    headers = login(logout_client, logout_user)
    db_session.delete(logout_user)
    db_session.commit()

    response = logout_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert revoked_count(db_session) == 0
    assert name(logout_settings, "access_token") not in logout_client.cookies
    assert name(logout_settings, "csrf_token") not in logout_client.cookies
