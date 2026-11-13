from http.cookies import SimpleCookie

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app import dependencies
from app.core.config import Settings, get_settings
from app.main import create_app

CSRF_URL = "/api/auth/csrf"
ORIGIN = "http://testserver"


@pytest.fixture
def csrf_app(db_session):
    settings = Settings(
        _env_file=None,
        environment="test",
        csrf_secret="csrf-exclusivo-dos-testes-00000000000000",
        csrf_trusted_origins=[ORIGIN],
    )
    app = create_app(settings)
    app.state.csrf_writes = 0
    app.dependency_overrides[dependencies.get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def csrf_client(csrf_app):
    with TestClient(csrf_app, base_url=ORIGIN) as client:
        yield client


@pytest.fixture
def protected_client(csrf_app, csrf_client):
    # Rota exclusiva dos testes: CSRF não exige antecipar login nem perfil.
    @csrf_app.post("/csrf-write", dependencies=[Depends(dependencies.require_csrf)])
    def write():
        csrf_app.state.csrf_writes += 1
        return {"executed": True}

    return csrf_client


def test_csrf_endpoint_initializes_pre_session_without_exposing_session_id(csrf_client):
    response = csrf_client.get(CSRF_URL)

    assert response.status_code == 200
    assert set(response.json()) == {"csrf_token"}
    assert response.json()["csrf_token"]
    assert response.headers["cache-control"] == "no-store"
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    for name in ("csrf_session", "csrf_token"):
        assert cookies[name]["httponly"] is True
        assert cookies[name]["samesite"].lower() == "lax"
        assert cookies[name]["path"] == "/"
        assert cookies[name]["domain"] == ""
        assert int(cookies[name]["max-age"]) > 0
    assert cookies["csrf_session"].value not in response.text
    assert cookies["csrf_token"].value == response.json()["csrf_token"]
    assert "access_token" not in csrf_client.cookies


def test_csrf_endpoint_preserves_pre_session_on_reload(csrf_client):
    first = csrf_client.get(CSRF_URL)
    assert first.status_code == 200
    session = csrf_client.cookies["csrf_session"]

    second = csrf_client.get(CSRF_URL)

    assert second.status_code == 200
    assert csrf_client.cookies["csrf_session"] == session


@pytest.mark.parametrize(
    "origin_headers",
    [{"Origin": ORIGIN}, {"Referer": ORIGIN + "/login?next=dashboard"}],
)
def test_csrf_accepts_token_and_trusted_origin_or_referer(protected_client, origin_headers):
    bootstrap = protected_client.get(CSRF_URL)
    assert bootstrap.status_code == 200

    response = protected_client.post(
        "/csrf-write",
        headers=origin_headers | {"X-CSRF-Token": bootstrap.json()["csrf_token"]},
    )

    assert response.status_code == 200
    assert response.json() == {"executed": True}


@pytest.mark.parametrize(
    "origin_headers",
    [
        {},
        {"Origin": "null"},
        {"Origin": "http://evil.example.com"},
        {"Origin": "http://testserver.evil.example.com"},
        {"Origin": "http://testserver:9999"},
        {"Origin": "http://evil.example.com", "Referer": ORIGIN + "/login"},
        {"Referer": "http://evil.example.com/"},
    ],
)
def test_csrf_rejects_untrusted_or_missing_origin(protected_client, origin_headers):
    bootstrap = protected_client.get(CSRF_URL)
    assert bootstrap.status_code == 200

    response = protected_client.post(
        "/csrf-write",
        headers=origin_headers | {"X-CSRF-Token": bootstrap.json()["csrf_token"]},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert protected_client.app.state.csrf_writes == 0


@pytest.mark.parametrize("defect", ["missing_header", "forged_token", "missing_cookie", "session"])
def test_csrf_rejects_invalid_double_submit(protected_client, defect):
    bootstrap = protected_client.get(CSRF_URL)
    assert bootstrap.status_code == 200
    headers = {"Origin": ORIGIN, "X-CSRF-Token": bootstrap.json()["csrf_token"]}
    if defect == "missing_header":
        del headers["X-CSRF-Token"]
    elif defect == "forged_token":
        # Igualdade cookie/header não basta: a assinatura também deve ser válida.
        protected_client.cookies.delete("csrf_token")
        protected_client.cookies.set("csrf_token", "forged")
        headers["X-CSRF-Token"] = "forged"
    elif defect == "missing_cookie":
        protected_client.cookies.delete("csrf_token")
    else:
        protected_client.cookies.delete("csrf_session")

    response = protected_client.post("/csrf-write", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert protected_client.app.state.csrf_writes == 0


def test_csrf_rejects_signed_token_from_another_pre_session(csrf_app, protected_client):
    bootstrap = protected_client.get(CSRF_URL)
    assert bootstrap.status_code == 200
    with TestClient(csrf_app, base_url=ORIGIN) as other_client:
        other_bootstrap = other_client.get(CSRF_URL)
        assert other_bootstrap.status_code == 200
        other_token = other_bootstrap.json()["csrf_token"]

    # Mesmo com assinatura válida e cookie/header iguais, a sessão não confere.
    protected_client.cookies.delete("csrf_token")
    protected_client.cookies.set("csrf_token", other_token)
    response = protected_client.post(
        "/csrf-write", headers={"Origin": ORIGIN, "X-CSRF-Token": other_token}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"
    assert protected_client.app.state.csrf_writes == 0
