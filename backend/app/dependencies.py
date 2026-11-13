"""Dependências injetadas nas rotas (`Depends`).

`get_current_user` e `get_storage` são **stubs** (ARQ §1.3): definem o contrato para
quem implementa perfil e avatar sem esperar o login. Nos testes, substitua-os com
`app.dependency_overrides[get_current_user] = lambda: usuario_de_fixture`.

- `get_current_user` real: issue #9 (login/logout).
- `get_storage` real: issue #11 (storage e avatar).

`get_db` é real (issue #5); nos testes a fixture `app` do `conftest.py` o substitui por
uma sessão SQLite em memória.
"""

from collections.abc import Iterator
from typing import NoReturn

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.controllers.csrf_http import validate_csrf_request
from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.exceptions import InvalidTokenError

# auto_error=False: a ausência de token também vira InvalidTokenError (formato padrão de erro)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def require_csrf(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Exige origem confiável e token CSRF válido em métodos de escrita."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        validate_csrf_request(request, settings)


def get_db() -> Iterator[Session]:
    """Abre uma sessão do banco por requisição e a fecha ao final, mesmo em caso de erro."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> NoReturn:
    """Stub: rejeita qualquer requisição com 401 até a issue #9 implementar o login.

    Raises:
        InvalidTokenError: sempre.
    """
    raise InvalidTokenError()


def get_storage() -> NoReturn:
    """Stub: o `StorageService` (local/S3) é implementado na issue #11.

    Raises:
        NotImplementedError: sempre; use `dependency_overrides` nos testes.
    """
    raise NotImplementedError("StorageService ainda não implementado (issue #11)")
