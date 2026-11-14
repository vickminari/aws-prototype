from datetime import UTC, datetime

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import RevokedToken
from app.services import auth_service
from tests.integration.session_support import (
    LOGOUT_URL,
    ME_URL,
    SESSION_ORIGIN,
    cookie_name,
    csrf_headers,
    login,
    put_cookie,
    response_cookies,
)


def new_client(app):
    return TestClient(app, base_url=SESSION_ORIGIN)


def revoked_count(db_session):
    return db_session.scalar(select(func.count()).select_from(RevokedToken))


def restore(client, saved):
    for cookie, value in saved.items():
        put_cookie(client, cookie, value)


def test_logout_revokes_session_and_clears_cookies(
    session_client, session_settings, session_user, db_session
):
    headers = login(session_client, session_user)
    token = session_client.cookies[cookie_name(session_settings, "access_token")]
    claims = jwt.decode(token, session_settings.jwt_secret, algorithms=["HS256"])

    response = session_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    cleared = response_cookies(response)
    for cookie in ("access_token", "csrf_token"):
        morsel = cleared[cookie_name(session_settings, cookie)]
        assert int(morsel["max-age"]) == 0
        assert morsel["path"] == "/"
        assert morsel["httponly"] is True
        assert morsel["samesite"].lower() == "lax"
        assert bool(morsel["secure"]) is (session_settings.environment == "prod")
        assert cookie_name(session_settings, cookie) not in session_client.cookies
    saved = db_session.get(RevokedToken, claims["jti"])
    assert saved.user_id == session_user.id
    assert saved.expires_at == datetime.fromtimestamp(claims["exp"], UTC)
    assert session_client.get(ME_URL).status_code == 401


def test_copy_of_logged_out_jwt_is_rejected(session_client, session_settings, session_user):
    headers = login(session_client, session_user)
    token = session_client.cookies[cookie_name(session_settings, "access_token")]
    assert session_client.post(LOGOUT_URL, headers=headers).status_code == 204

    copy = new_client(session_client.app)
    restore(copy, {cookie_name(session_settings, "access_token"): token})

    response = copy.get(ME_URL)
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"


def test_new_login_after_logout_works(session_client, session_user):
    headers = login(session_client, session_user)
    assert session_client.post(LOGOUT_URL, headers=headers).status_code == 204

    login(session_client, session_user)

    assert session_client.get(ME_URL).status_code == 200


@pytest.mark.parametrize("defect", ["no_csrf", "wrong_csrf", "untrusted_origin"])
def test_logout_requires_csrf_and_keeps_session(
    session_client, session_user, db_session, monkeypatch, defect
):
    headers = login(session_client, session_user)

    def must_not_logout(*args, **kwargs):
        pytest.fail("O logout não deve executar após falha CSRF")

    monkeypatch.setattr(auth_service, "logout", must_not_logout)
    if defect == "no_csrf":
        del headers["X-CSRF-Token"]
    elif defect == "wrong_csrf":
        headers["X-CSRF-Token"] = "forjado"
    else:
        headers["Origin"] = "https://evil.example.com"

    response = session_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert revoked_count(db_session) == 0
    assert session_client.get(ME_URL).status_code == 200


def test_repeated_logout_with_copied_session_is_idempotent(
    session_client, session_settings, session_user, db_session
):
    """Outra aba ou cópia dos cookies repete o logout: 204, sem duplicar a revogação."""
    headers = login(session_client, session_user)
    saved = {
        cookie: session_client.cookies[cookie]
        for cookie in (
            cookie_name(session_settings, "access_token"),
            cookie_name(session_settings, "csrf_token"),
        )
    }
    assert session_client.post(LOGOUT_URL, headers=headers).status_code == 204

    copy = new_client(session_client.app)
    restore(copy, saved)
    response = copy.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert revoked_count(db_session) == 1


def test_repeated_logout_after_cookies_were_cleared_still_requires_csrf(
    session_client, session_user, db_session
):
    headers = login(session_client, session_user)
    assert session_client.post(LOGOUT_URL, headers=headers).status_code == 204

    response = session_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert revoked_count(db_session) == 1


def test_logout_with_pre_session_only_returns_204_without_revoking(
    session_client, session_settings, db_session
):
    headers = csrf_headers(session_client)

    response = session_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert revoked_count(db_session) == 0
    assert cookie_name(session_settings, "csrf_token") not in session_client.cookies
    assert cookie_name(session_settings, "csrf_session") not in session_client.cookies


def test_logout_of_one_session_keeps_other_session_of_same_user(session_client, session_user):
    headers = login(session_client, session_user)
    with new_client(session_client.app) as other:
        login(other, session_user)

        assert session_client.post(LOGOUT_URL, headers=headers).status_code == 204

        assert session_client.get(ME_URL).status_code == 401
        assert other.get(ME_URL).status_code == 200


def test_logout_openapi_describes_responses(session_client):
    operation = session_client.get("/api/openapi.json").json()["paths"][LOGOUT_URL]["post"]

    assert {"204", "403"} <= set(operation["responses"])
    assert "content" not in operation["responses"]["204"]


def test_logout_of_removed_user_clears_cookies_without_revoking(
    session_client, session_settings, session_user, db_session
):
    headers = login(session_client, session_user)
    db_session.delete(session_user)
    db_session.commit()

    response = session_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204
    assert revoked_count(db_session) == 0
    assert cookie_name(session_settings, "access_token") not in session_client.cookies
    assert cookie_name(session_settings, "csrf_token") not in session_client.cookies
