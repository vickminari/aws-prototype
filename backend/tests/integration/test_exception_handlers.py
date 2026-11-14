import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    DomainError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidImageError,
    InvalidTokenError,
    NotFoundError,
    UsernameAlreadyExistsError,
    WrongPasswordError,
)
from app.main import create_app


def _app_raising(exc: Exception) -> FastAPI:
    """Cria o app real com uma rota extra que só lança `exc`."""
    app = create_app()

    @app.get("/boom")
    def boom():
        raise exc

    return app


@pytest.mark.parametrize(
    ("exc_class", "status_code", "code"),
    [
        (EmailAlreadyExistsError, 409, "EMAIL_ALREADY_EXISTS"),
        (UsernameAlreadyExistsError, 409, "USERNAME_ALREADY_EXISTS"),
        (InvalidCredentialsError, 401, "INVALID_CREDENTIALS"),
        (InvalidTokenError, 401, "INVALID_TOKEN"),
        (WrongPasswordError, 400, "WRONG_PASSWORD"),
        (InvalidImageError, 422, "INVALID_IMAGE"),
        (NotFoundError, 404, "NOT_FOUND"),
    ],
)
def test_domain_error_returns_mapped_status_and_code(exc_class, status_code, code):
    client = TestClient(_app_raising(exc_class()))

    response = client.get("/boom")

    assert response.status_code == status_code
    assert response.json() == {"detail": exc_class.message, "code": code}


def test_domain_error_with_custom_message_returns_it_in_detail():
    client = TestClient(_app_raising(NotFoundError("Usuário não encontrado")))

    response = client.get("/boom")

    assert response.json() == {"detail": "Usuário não encontrado", "code": "NOT_FOUND"}


@pytest.mark.parametrize("exc_class", [InvalidCredentialsError, InvalidTokenError])
def test_authentication_error_announces_cookie_scheme_not_bearer(exc_class):
    """RFC 9110 exige um desafio no 401; anuncia o cookie, o único meio aceito."""
    client = TestClient(_app_raising(exc_class()))

    response = client.get("/boom")

    assert response.headers["www-authenticate"] == 'Cookie realm="api"'


def test_unmapped_domain_error_returns_400():
    class SomeRuleError(DomainError):
        code = "SOME_RULE"
        message = "Regra violada"

    client = TestClient(_app_raising(SomeRuleError()))

    response = client.get("/boom")

    assert response.status_code == 400
    assert response.json() == {"detail": "Regra violada", "code": "SOME_RULE"}


def test_unexpected_error_returns_500_without_leaking_message():
    app = _app_raising(RuntimeError("segredo interno"))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor", "code": "INTERNAL_ERROR"}
