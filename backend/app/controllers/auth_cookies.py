"""Cookies da sessão HTTP (acesso e CSRF): nomes, atributos e leitura do JWT do cookie."""

from typing import Any

from fastapi import Request, Response

from app.core.config import Settings
from app.core.security import decode_access_token

ACCESS_COOKIE = "access_token"
_CLAIMS_STATE = "session_claims"


def session_cookie_name(base: str, settings: Settings) -> str:
    """Em produção usa o prefixo `__Host-`, que exige `Secure`, `Path=/` e nenhum `Domain`."""
    return f"__Host-{base}" if settings.environment == "prod" else base


def _attributes(settings: Settings) -> dict[str, Any]:
    """Atributos únicos para criar e remover: divergir faria o logout deixar cookie para trás."""
    return {
        "path": "/",
        "secure": settings.environment == "prod",
        "httponly": True,
        "samesite": "lax",
    }


def set_session_cookie(
    response: Response, base: str, value: str, *, max_age: int, settings: Settings
) -> None:
    response.set_cookie(
        key=session_cookie_name(base, settings),
        value=value,
        max_age=max_age,
        **_attributes(settings),
    )


def clear_session_cookie(response: Response, base: str, settings: Settings) -> None:
    """Expira o cookie no mesmo escopo e com os mesmos atributos da criação."""
    response.delete_cookie(key=session_cookie_name(base, settings), **_attributes(settings))


def auth_cookie_name(settings: Settings) -> str:
    return session_cookie_name(ACCESS_COOKIE, settings)


def read_auth_cookie(request: Request, settings: Settings) -> str | None:
    """Lê somente o cookie do ambiente; nomes de outro ambiente e Bearer são ignorados."""
    return request.cookies.get(auth_cookie_name(settings))


def read_session_claims(request: Request, settings: Settings) -> dict[str, Any] | None:
    """Claims do JWT do cookie, validados uma única vez por requisição.

    CSRF, autenticação e logout consultam o mesmo cookie; o resultado fica em
    `request.state`. Retorna `None` sem cookie. Não consulta revogação nem usuário.

    Raises:
        InvalidTokenError: se o JWT do cookie for inválido ou estiver expirado.
    """
    token = read_auth_cookie(request, settings)
    if token is None:
        return None
    cached = getattr(request.state, _CLAIMS_STATE, None)
    if cached is not None and cached[0] == token:
        return cached[1]
    claims = decode_access_token(token, settings=settings)
    setattr(request.state, _CLAIMS_STATE, (token, claims))
    return claims


def set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    """Define o cookie HttpOnly com validade igual à configuração do JWT."""
    set_session_cookie(
        response, ACCESS_COOKIE, token, max_age=settings.jwt_expire_minutes * 60, settings=settings
    )


def clear_auth_cookie(response: Response, settings: Settings) -> None:
    clear_session_cookie(response, ACCESS_COOKIE, settings)
