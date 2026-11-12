"""Helpers HTTP do cookie de acesso; não geram nem validam o JWT."""

from fastapi import Response

from app.core.config import Settings


def auth_cookie_name(settings: Settings) -> str:
    """Seleciona o nome; o prefixo __Host- exige HTTPS em produção."""
    return "__Host-access_token" if settings.environment == "prod" else "access_token"


def set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    """Define o cookie HttpOnly com validade igual à configuração do JWT."""
    response.set_cookie(
        key=auth_cookie_name(settings),
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
        secure=settings.environment == "prod",
        httponly=True,
        samesite="lax",
    )


def clear_auth_cookie(response: Response, settings: Settings) -> None:
    """Expira o cookie no mesmo escopo e com os mesmos atributos da criação."""
    response.delete_cookie(
        key=auth_cookie_name(settings),
        path="/",
        secure=settings.environment == "prod",
        httponly=True,
        samesite="lax",
    )
