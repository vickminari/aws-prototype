from http.cookies import SimpleCookie
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_db, require_csrf
from app.main import create_app
from app.services import auth_service

ORIGIN = "https://app.example.com"
PASSWORD = "Senha-de-teste-123"
LOGIN_URL = "/api/auth/login"
CSRF_URL = "/api/auth/csrf"


@pytest.fixture(params=["test", "prod"])
def login_settings(request):
    return Settings(
        _env_file=None,
        environment=request.param,
        jwt_secret="jwt-exclusivo-dos-testes-0000000000000000",
        jwt_expire_minutes=30,
        csrf_secret="csrf-exclusivo-dos-testes-00000000000000",
        csrf_trusted_origins=[ORIGIN],
    )


@pytest.fixture
def login_app(db_session, login_settings):
    app = create_app(login_settings)
    app.dependency_overrides[get_db] = lambda: db_session
    app.state.csrf_writes = 0

    @app.post("/login-write-test", dependencies=[Depends(require_csrf)])
    def write():
        # Isola o vínculo CSRF; autenticação das rotas será testada na etapa 5.
        app.state.csrf_writes += 1
        return {"executed": True}

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def login_client(login_app):
    with TestClient(login_app, base_url=ORIGIN) as client:
        yield client


@pytest.fixture
def login_user(user_factory):
    return user_factory(username="maria.silva", email="maria@example.com", password=PASSWORD)


def csrf_headers(client):
    response = client.get(CSRF_URL)
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def cookie_prefix(settings):
    return "__Host-" if settings.environment == "prod" else ""


@pytest.mark.parametrize("identifier", ["maria.silva", "maria@example.com", "MARIA@EXAMPLE.COM"])
def test_login_with_valid_form_sets_cookie_without_exposing_jwt(
    login_client, login_settings, login_user, identifier
):
    response = login_client.post(
        LOGIN_URL,
        data={"username": identifier, "password": PASSWORD},
        headers=csrf_headers(login_client),
    )

    assert response.status_code == 200
    assert response.json() == {"detail": "Login realizado"}
    assert response.headers["cache-control"] == "no-store"
    prefix = cookie_prefix(login_settings)
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    cookie = cookies[prefix + "access_token"]
    assert cookie["httponly"] is True
    assert bool(cookie["secure"]) is (login_settings.environment == "prod")
    assert cookie["samesite"].lower() == "lax"
    assert cookie["path"] == "/"
    assert cookie["domain"] == ""
    assert int(cookie["max-age"]) == 30 * 60
    claims = jwt.decode(cookie.value, login_settings.jwt_secret, algorithms=["HS256"])
    assert UUID(claims["sub"]) == login_user.id
    assert str(UUID(claims["jti"])) == claims["jti"]
    assert claims["exp"] - claims["iat"] == 30 * 60
    assert cookie.value not in response.text
    assert PASSWORD not in response.text
    assert login_user.hashed_password not in response.text
    assert prefix + "csrf_session" not in login_client.cookies


@pytest.mark.parametrize(
    "identifier, password, active",
    [
        ("maria.silva", "Senha-incorreta-123", True),
        ("nao.existe", PASSWORD, True),
        ("maria.silva", PASSWORD, False),
    ],
)
def test_login_with_invalid_credentials_returns_same_401_without_auth_cookie(
    login_client, login_settings, login_user, db_session, identifier, password, active
):
    login_user.is_active = active
    db_session.commit()

    response = login_client.post(
        LOGIN_URL,
        data={"username": identifier, "password": password},
        headers=csrf_headers(login_client),
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Usuário ou senha inválidos",
        "code": "INVALID_CREDENTIALS",
    }
    assert cookie_prefix(login_settings) + "access_token" not in login_client.cookies
    assert password not in response.text


@pytest.mark.parametrize("defect", ["no_csrf", "wrong_csrf", "untrusted_origin"])
def test_login_rejects_csrf_before_checking_credentials(login_client, monkeypatch, defect):
    def must_not_authenticate(*args, **kwargs):
        pytest.fail("A autenticação não deve executar após falha CSRF")

    monkeypatch.setattr(auth_service, "authenticate", must_not_authenticate)
    headers = csrf_headers(login_client)
    if defect == "no_csrf":
        del headers["X-CSRF-Token"]
    elif defect == "wrong_csrf":
        headers["X-CSRF-Token"] = "forjado"
    else:
        headers["Origin"] = "https://evil.example.com"

    response = login_client.post(
        LOGIN_URL, data={"username": "maria.silva", "password": PASSWORD}, headers=headers
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"


def test_login_without_password_returns_422_without_echoing_form(login_client):
    response = login_client.post(
        LOGIN_URL, data={"username": "maria.silva"}, headers=csrf_headers(login_client)
    )

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "password"] for error in response.json()["detail"])


def test_login_rotates_csrf_and_rejects_restored_pre_session(
    login_client, login_settings, login_user
):
    old_headers = csrf_headers(login_client)
    prefix = cookie_prefix(login_settings)
    old_session = login_client.cookies[prefix + "csrf_session"]
    response = login_client.post(
        LOGIN_URL, data={"username": login_user.username, "password": PASSWORD}, headers=old_headers
    )
    assert response.status_code == 200
    assert login_client.cookies[prefix + "csrf_token"] != old_headers["X-CSRF-Token"]

    new_headers = csrf_headers(login_client)
    assert prefix + "csrf_session" not in login_client.cookies
    assert new_headers["X-CSRF-Token"] != old_headers["X-CSRF-Token"]
    assert login_client.post("/login-write-test", headers=new_headers).status_code == 200

    # Restaura cookie, header e pré-sessão antigos: com JWT presente devem falhar.
    login_client.cookies.delete(prefix + "csrf_token")
    login_client.cookies.set(prefix + "csrf_token", old_headers["X-CSRF-Token"])
    login_client.cookies.set(prefix + "csrf_session", old_session)
    rejected = login_client.post("/login-write-test", headers=old_headers)
    assert rejected.status_code == 403
    assert rejected.json()["code"] == "CSRF_INVALID"
    assert login_client.app.state.csrf_writes == 1


def test_authenticated_csrf_is_bound_to_jti_not_only_user(login_client, login_settings, login_user):
    response = login_client.post(
        LOGIN_URL,
        data={"username": login_user.username, "password": PASSWORD},
        headers=csrf_headers(login_client),
    )
    assert response.status_code == 200
    headers = csrf_headers(login_client)
    name = cookie_prefix(login_settings) + "access_token"
    claims = jwt.decode(login_client.cookies[name], login_settings.jwt_secret, algorithms=["HS256"])
    claims["jti"] = str(uuid4())
    other_token = jwt.encode(claims, login_settings.jwt_secret, algorithm="HS256")
    login_client.cookies.delete(name)
    login_client.cookies.set(name, other_token)

    response = login_client.post("/login-write-test", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert login_client.app.state.csrf_writes == 0


@pytest.mark.parametrize("defect", ["malformed", "wrong_secret", "expired"])
def test_invalid_jwt_cannot_fall_back_to_pre_session_but_bootstrap_allows_new_login(
    login_client, login_settings, login_user, defect
):
    headers = csrf_headers(login_client)
    claims = {
        "sub": str(login_user.id),
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
            else login_settings.jwt_secret
        )
        invalid = jwt.encode(claims, secret, algorithm="HS256")
    name = cookie_prefix(login_settings) + "access_token"
    login_client.cookies.set(name, invalid, domain="app.example.com", path="/")

    rejected = login_client.post("/login-write-test", headers=headers)
    assert rejected.status_code == 403
    assert rejected.json()["code"] == "CSRF_INVALID"
    assert login_client.app.state.csrf_writes == 0

    # Apenas o bootstrap descarta a credencial inválida para permitir novo login.
    refreshed_headers = csrf_headers(login_client)
    assert name not in login_client.cookies
    response = login_client.post(
        LOGIN_URL,
        data={"username": login_user.username, "password": PASSWORD},
        headers=refreshed_headers,
    )
    assert response.status_code == 200


def test_login_openapi_describes_form_and_public_response(login_client):
    document = login_client.get("/api/openapi.json").json()
    operation = document["paths"][LOGIN_URL]["post"]

    assert "application/x-www-form-urlencoded" in operation["requestBody"]["content"]
    assert not operation.get("security")
    assert {"200", "401", "403", "422"} <= set(operation["responses"])
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LoginResponse"
    }
    assert set(document["components"]["schemas"]["LoginResponse"]["properties"]) == {"detail"}
