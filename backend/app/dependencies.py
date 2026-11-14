"""Dependências injetadas nas rotas (`Depends`).

`get_current_user` autentica pelo cookie HttpOnly definido no login (issue #9). Testes
isolados podem substituí-lo com
`app.dependency_overrides[get_current_user] = lambda: usuario_de_fixture`.

`get_storage` cria o storage configurado (local ou S3, issue #11).

`get_db` é real (issue #5); nos testes a fixture `app` do `conftest.py` o substitui por
uma sessão SQLite em memória.
"""

from collections.abc import Iterator

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.controllers.auth_cookies import read_session_claims
from app.controllers.csrf_http import validate_csrf_request
from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.exceptions import InvalidTokenError
from app.models import User
from app.services import auth_service
from app.services.storage import StorageService, create_storage

# Só documenta o esquema no OpenAPI: o nome real depende do ambiente e é lido
# por read_session_claims. auto_error=False mantém o formato padrão de erro 401.
cookie_scheme = APIKeyCookie(
    name="access_token",
    scheme_name="CookieAuth",
    description=(
        "Cookie HttpOnly definido por POST /api/auth/login; em produção chama-se "
        "__Host-access_token. O navegador o envia automaticamente; não há Bearer."
    ),
    auto_error=False,
)


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


def get_current_user(
    request: Request,
    _documented_cookie: str | None = Security(cookie_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Autentica pelo cookie do ambiente: JWT válido, sessão não revogada e usuário ativo.

    Raises:
        InvalidTokenError: se o cookie faltar ou a sessão for inválida por qualquer motivo.
    """
    claims = read_session_claims(request, settings)
    if claims is None:
        raise InvalidTokenError()
    return auth_service.get_session_user(db, claims["sub"], claims["jti"])


def get_storage() -> StorageService:
    """Cria o backend de storage configurado para a aplicação."""
    from app.core.config import get_settings

    return create_storage(get_settings())
