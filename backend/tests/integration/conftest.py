"""Fixtures dos testes de sessão HTTP, parametrizadas para `test` e `prod`.

- `session_settings`: configuração com segredos fictícios e origem HTTPS confiável.
- `session_app` / `session_client`: app e cliente nessa origem (cookies `__Host-` em prod).
- `session_user`: usuário `maria.silva` com a senha padrão.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_db
from app.main import create_app
from tests.integration.session_support import SESSION_ORIGIN


@pytest.fixture(params=["test", "prod"])
def session_settings(request):
    return Settings(
        _env_file=None,
        environment=request.param,
        jwt_secret="jwt-exclusivo-dos-testes-0000000000000000",
        jwt_expire_minutes=30,
        csrf_secret="csrf-exclusivo-dos-testes-00000000000000",
        csrf_trusted_origins=[SESSION_ORIGIN],
    )


@pytest.fixture
def session_app(db_session, session_settings):
    app = create_app(session_settings)
    app.dependency_overrides[get_db] = lambda: db_session
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def session_client(session_app):
    with TestClient(session_app, base_url=SESSION_ORIGIN) as client:
        yield client


@pytest.fixture
def session_user(user_factory):
    return user_factory(username="maria.silva", email="maria@example.com")
