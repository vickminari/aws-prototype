"""Estabelecimento da sessão HTTP após o service autenticar as credenciais."""

from uuid import UUID

from fastapi import Response

from app.controllers.auth_cookies import set_auth_cookie
from app.controllers.csrf_http import rotate_csrf_after_login
from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token


def establish_login(response: Response, user_id: UUID, settings: Settings) -> None:
    """Define JWT HttpOnly e renova CSRF, descartando a pré-sessão anterior."""
    token = create_access_token(user_id, settings=settings)
    claims = decode_access_token(token, settings=settings)
    set_auth_cookie(response, token, settings)
    rotate_csrf_after_login(response, claims["jti"], settings)
