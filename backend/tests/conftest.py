"""Fixtures compartilhadas pelos testes (ARQ §6.3).

- `engine`: SQLite em memória, recriado a cada teste (isolamento total entre testes).
- `db_session`: `Session` ligada ao `engine`; faz rollback e fecha ao final.
- `app` / `client`: API com `get_db` substituído pela `db_session` do teste.
- `user_factory`: cria e persiste usuários com dados válidos e únicos.
- `auth_user`: usuário criado e devolvido por `get_current_user` (sem login real).
"""

from collections.abc import Callable, Iterator
from itertools import count

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.core.security import hash_password
from app.dependencies import get_current_user, get_db
from app.main import create_app
from app.models import User

DEFAULT_PASSWORD = "Senha-de-teste-123"


@pytest.fixture
def engine() -> Iterator[Engine]:
    # StaticPool: todas as conexões compartilham o mesmo banco em memória
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # O SQLite só respeita chaves estrangeiras com este PRAGMA (o PostgreSQL sempre respeita)
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    session = Session(engine, expire_on_commit=False)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def app(db_session: Session) -> Iterator[FastAPI]:
    app = create_app(Settings(_env_file=None, environment="test"))
    app.dependency_overrides[get_db] = lambda: db_session
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def user_factory(db_session: Session) -> Callable[..., User]:
    """Cria usuários persistidos; qualquer campo pode ser sobrescrito.

    Uso: `user_factory(username="maria", password="Outra-123")`. A senha padrão é
    `DEFAULT_PASSWORD` e é salva somente como hash.
    """
    sequence = count(1)

    def create(*, password: str = DEFAULT_PASSWORD, **fields) -> User:
        n = next(sequence)
        data = {
            "full_name": f"Usuário {n}",
            "username": f"usuario{n}",
            "email": f"usuario{n}@example.com",
            "hashed_password": hash_password(password),
        }
        user = User(**(data | fields))
        db_session.add(user)
        db_session.commit()
        return user

    return create


@pytest.fixture
def auth_user(app: FastAPI, user_factory: Callable[..., User]) -> User:
    """Usuário "logado": `get_current_user` passa a devolvê-lo em todas as rotas."""
    user = user_factory()
    app.dependency_overrides[get_current_user] = lambda: user
    return user
