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

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import InvalidTokenError
from app.services.storage import StorageService, create_storage

# auto_error=False: a ausência de token também vira InvalidTokenError (formato padrão de erro)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


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


def get_storage() -> StorageService:
    """Cria o backend de storage configurado para a aplicação."""
    from app.core.config import get_settings

    return create_storage(get_settings())
