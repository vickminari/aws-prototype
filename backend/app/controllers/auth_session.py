"""Início e fim da sessão HTTP; as regras de autenticação ficam no service."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.controllers.auth_cookies import clear_auth_cookie, read_session_claims, set_auth_cookie
from app.controllers.csrf_http import clear_csrf_cookies, rotate_csrf_after_login
from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token
from app.services import auth_service


def _revoke_current_session(request: Request, db: Session, settings: Settings) -> None:
    """Revoga o JWT do cookie, se houver; `require_csrf` já recusou um JWT inválido."""
    claims = read_session_claims(request, settings)
    if claims is not None:
        expires_at = datetime.fromtimestamp(claims["exp"], UTC)
        auth_service.logout(db, claims["sub"], claims["jti"], expires_at)


def establish_login(
    request: Request, response: Response, db: Session, user_id: UUID, settings: Settings
) -> None:
    """Define JWT HttpOnly e renova CSRF, descartando a pré-sessão anterior.

    Um login no navegador que já tinha sessão (novo login ou troca de conta) revoga a
    sessão anterior, para que cópias do cookie antigo deixem de valer.
    """
    _revoke_current_session(request, db, settings)
    token = create_access_token(user_id, settings=settings)
    claims = decode_access_token(token, settings=settings)
    set_auth_cookie(response, token, settings)
    rotate_csrf_after_login(response, claims["jti"], settings)


def end_session(request: Request, response: Response, db: Session, settings: Settings) -> None:
    """Revoga o JWT do cookie, se houver, e remove os cookies de sessão e CSRF.

    Deve rodar após `require_csrf`, que já recusa um JWT inválido presente no cookie.
    Sem JWT (somente pré-sessão) não há o que revogar; os cookies são limpos igualmente.
    """
    _revoke_current_session(request, db, settings)
    clear_auth_cookie(response, settings)
    clear_csrf_cookies(response, settings)
    response.headers["Cache-Control"] = "no-store"
