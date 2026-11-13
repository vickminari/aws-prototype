from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends

from app.dependencies import require_csrf
from app.services import auth_service
from tests.integration.session_support import (
    LOGIN_URL,
    PASSWORD,
    cookie_name,
    csrf_headers,
    login,
    put_cookie,
    response_cookies,
)


@pytest.fixture
def session_app(session_app):
    """Acrescenta uma escrita mínima para observar o vínculo CSRF sem regras de perfil."""
    session_app.state.csrf_writes = 0

    @session_app.post("/login-write-test", dependencies=[Depends(require_csrf)])
    def write():
        session_app.state.csrf_writes += 1
        return {"executed": True}

    return session_app


def cookie_prefix(settings):
    return cookie_name(settings, "")


@pytest.mark.parametrize("identifier", ["maria.silva", "maria@example.com", "MARIA@EXAMPLE.COM"])
def test_login_with_valid_form_sets_cookie_without_exposing_jwt(
    session_client, session_settings, session_user, identifier
):
    response = session_client.post(
        LOGIN_URL,
        data={"username": identifier, "password": PASSWORD},
        headers=csrf_headers(session_client),
    )

    assert response.status_code == 200
    assert response.json() == {"detail": "Login realizado"}
    assert response.headers["cache-control"] == "no-store"
    prefix = cookie_prefix(session_settings)
    cookie = response_cookies(response)[prefix + "access_token"]
    assert cookie["httponly"] is True
    assert bool(cookie["secure"]) is (session_settings.environment == "prod")
    assert cookie["samesite"].lower() == "lax"
    assert cookie["path"] == "/"
    assert cookie["domain"] == ""
    assert int(cookie["max-age"]) == 30 * 60
    claims = jwt.decode(cookie.value, session_settings.jwt_secret, algorithms=["HS256"])
    assert UUID(claims["sub"]) == session_user.id
    assert str(UUID(claims["jti"])) == claims["jti"]
    assert claims["exp"] - claims["iat"] == 30 * 60
    assert cookie.value not in response.text
    assert PASSWORD not in response.text
    assert session_user.hashed_password not in response.text
    assert prefix + "csrf_session" not in session_client.cookies


@pytest.mark.parametrize(
    "identifier, password, active",
    [
        ("maria.silva", "Senha-incorreta-123", True),
        ("nao.existe", PASSWORD, True),
        ("maria.silva", PASSWORD, False),
    ],
)
def test_login_with_invalid_credentials_returns_same_401_without_auth_cookie(
    session_client, session_settings, session_user, db_session, identifier, password, active
):
    session_user.is_active = active
    db_session.commit()

    response = session_client.post(
        LOGIN_URL,
        data={"username": identifier, "password": password},
        headers=csrf_headers(session_client),
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Usuário ou senha inválidos",
        "code": "INVALID_CREDENTIALS",
    }
    assert cookie_prefix(session_settings) + "access_token" not in session_client.cookies
    assert password not in response.text


@pytest.mark.parametrize("defect", ["no_csrf", "wrong_csrf", "untrusted_origin"])
def test_login_rejects_csrf_before_checking_credentials(session_client, monkeypatch, defect):
    def must_not_authenticate(*args, **kwargs):
        pytest.fail("A autenticação não deve executar após falha CSRF")

    monkeypatch.setattr(auth_service, "authenticate", must_not_authenticate)
    headers = csrf_headers(session_client)
    if defect == "no_csrf":
        del headers["X-CSRF-Token"]
    elif defect == "wrong_csrf":
        headers["X-CSRF-Token"] = "forjado"
    else:
        headers["Origin"] = "https://evil.example.com"

    response = session_client.post(
        LOGIN_URL, data={"username": "maria.silva", "password": PASSWORD}, headers=headers
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"


def test_login_without_password_returns_422_without_echoing_form(session_client):
    response = session_client.post(
        LOGIN_URL, data={"username": "maria.silva"}, headers=csrf_headers(session_client)
    )

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "password"] for error in response.json()["detail"])


def test_login_rotates_csrf_and_rejects_restored_pre_session(
    session_client, session_settings, session_user
):
    old_headers = csrf_headers(session_client)
    prefix = cookie_prefix(session_settings)
    old_session = session_client.cookies[prefix + "csrf_session"]
    response = session_client.post(
        LOGIN_URL,
        data={"username": session_user.username, "password": PASSWORD},
        headers=old_headers,
    )
    assert response.status_code == 200
    assert session_client.cookies[prefix + "csrf_token"] != old_headers["X-CSRF-Token"]

    new_headers = csrf_headers(session_client)
    assert prefix + "csrf_session" not in session_client.cookies
    assert new_headers["X-CSRF-Token"] != old_headers["X-CSRF-Token"]
    assert session_client.post("/login-write-test", headers=new_headers).status_code == 200

    # Restaura cookie, header e pré-sessão antigos: com JWT presente devem falhar.
    session_client.cookies.delete(prefix + "csrf_token")
    session_client.cookies.set(prefix + "csrf_token", old_headers["X-CSRF-Token"])
    session_client.cookies.set(prefix + "csrf_session", old_session)
    rejected = session_client.post("/login-write-test", headers=old_headers)
    assert rejected.status_code == 403
    assert rejected.json()["code"] == "CSRF_INVALID"
    assert session_client.app.state.csrf_writes == 1


def test_authenticated_csrf_is_bound_to_jti_not_only_user(
    session_client, session_settings, session_user
):
    response = session_client.post(
        LOGIN_URL,
        data={"username": session_user.username, "password": PASSWORD},
        headers=csrf_headers(session_client),
    )
    assert response.status_code == 200
    headers = csrf_headers(session_client)
    name = cookie_prefix(session_settings) + "access_token"
    claims = jwt.decode(
        session_client.cookies[name], session_settings.jwt_secret, algorithms=["HS256"]
    )
    claims["jti"] = str(uuid4())
    other_token = jwt.encode(claims, session_settings.jwt_secret, algorithm="HS256")
    session_client.cookies.delete(name)
    session_client.cookies.set(name, other_token)

    response = session_client.post("/login-write-test", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert session_client.app.state.csrf_writes == 0


@pytest.mark.parametrize("defect", ["malformed", "wrong_secret", "expired"])
def test_invalid_jwt_cannot_fall_back_to_pre_session_but_bootstrap_allows_new_login(
    session_client, session_settings, session_user, defect
):
    headers = csrf_headers(session_client)
    claims = {
        "sub": str(session_user.id),
        "jti": str(uuid4()),
        "iat": 0,
        "exp": 1 if defect == "expired" else 9999999999,
    }
    if defect == "malformed":
        invalid = "nao-e-jwt"
    else:
        secret = (
            "outro-segredo-dos-testes-00000000000000"
            if defect == "wrong_secret"
            else session_settings.jwt_secret
        )
        invalid = jwt.encode(claims, secret, algorithm="HS256")
    name = cookie_prefix(session_settings) + "access_token"
    put_cookie(session_client, name, invalid)

    rejected = session_client.post("/login-write-test", headers=headers)
    assert rejected.status_code == 403
    assert rejected.json()["code"] == "CSRF_INVALID"
    assert session_client.app.state.csrf_writes == 0

    # Apenas o bootstrap descarta a credencial inválida para permitir novo login.
    refreshed_headers = csrf_headers(session_client)
    assert name not in session_client.cookies
    response = session_client.post(
        LOGIN_URL,
        data={"username": session_user.username, "password": PASSWORD},
        headers=refreshed_headers,
    )
    assert response.status_code == 200


def test_login_openapi_describes_form_and_public_response(session_client):
    document = session_client.get("/api/openapi.json").json()
    operation = document["paths"][LOGIN_URL]["post"]

    assert "application/x-www-form-urlencoded" in operation["requestBody"]["content"]
    assert not operation.get("security")
    assert {"200", "401", "403", "422"} <= set(operation["responses"])
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LoginResponse"
    }
    assert set(document["components"]["schemas"]["LoginResponse"]["properties"]) == {"detail"}


def test_authenticated_csrf_token_is_stable_across_tabs(session_client, session_user):
    tab_a = login(session_client, session_user)
    tab_b = csrf_headers(session_client)

    assert tab_b["X-CSRF-Token"] == tab_a["X-CSRF-Token"]
    assert session_client.post("/login-write-test", headers=tab_a).status_code == 200
    assert session_client.post("/login-write-test", headers=tab_b).status_code == 200
