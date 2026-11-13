"""Pré-sessão CSRF e validação de origem na camada HTTP."""

import hmac
from urllib.parse import urlsplit

from fastapi import Request, Response

from app.core.config import Settings
from app.core.csrf import (
    MAX_CSRF_TOKEN_LENGTH,
    create_csrf_token,
    verify_csrf_token,
)
from app.core.exceptions import InvalidCsrfTokenError

_PRE_SESSION_CONTEXT = "csrf-pre-session-cookie-v1"


def csrf_cookie_name(name: str, settings: Settings) -> str:
    """Usa cookies limitados ao host e HTTPS em produção."""
    return f"__Host-{name}" if settings.environment == "prod" else name


def _origin(value: str, *, referer: bool = False) -> tuple[str, str, int] | None:
    """Extrai a origem exata; só Referer permite caminho e query."""
    if not value or any(char.isspace() or ord(char) < 32 for char in value):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or (not referer and (parsed.path or parsed.query or "?" in value or "#" in value))
        ):
            return None
        port = parsed.port
        return (
            parsed.scheme,
            parsed.hostname,
            port if port is not None else (443 if parsed.scheme == "https" else 80),
        )
    except ValueError:
        return None


def _require_trusted_origin(request: Request, settings: Settings) -> None:
    """Origin presente prevalece sobre Referer; ausência/duplicação falha fechada."""
    origins = request.headers.getlist("origin")
    references = request.headers.getlist("referer")
    if origins:
        source = _origin(origins[0]) if len(origins) == 1 else None
    else:
        source = _origin(references[0], referer=True) if len(references) == 1 else None
    trusted = {_origin(origin) for origin in settings.csrf_trusted_origins}
    if source is None or source not in trusted:
        raise InvalidCsrfTokenError()


def issue_csrf_token(request: Request, response: Response, settings: Settings) -> str:
    """Inicia/reutiliza uma pré-sessão assinada e emite o token público CSRF."""
    session = request.cookies.get(csrf_cookie_name("csrf_session", settings), "")
    lifetime = settings.csrf_expire_minutes * 60
    if not verify_csrf_token(session, _PRE_SESSION_CONTEXT, settings.csrf_secret):
        session = create_csrf_token(_PRE_SESSION_CONTEXT, settings.csrf_secret, expires_in=lifetime)
    token = create_csrf_token(f"pre:{session}", settings.csrf_secret, expires_in=lifetime)
    for name, value in (("csrf_session", session), ("csrf_token", token)):
        response.set_cookie(
            key=csrf_cookie_name(name, settings),
            value=value,
            max_age=lifetime,
            path="/",
            secure=settings.environment == "prod",
            httponly=True,
            samesite="lax",
        )
    response.headers["Cache-Control"] = "no-store"
    return token


def validate_csrf_request(request: Request, settings: Settings) -> None:
    """Valida origem, double-submit e vínculo à pré-sessão antes de uma escrita.

    Raises:
        InvalidCsrfTokenError: se origem, cookies, header ou assinatura forem inválidos.
    """
    _require_trusted_origin(request, settings)
    headers = request.headers.getlist("x-csrf-token")
    header = headers[0] if len(headers) == 1 else ""
    cookie = request.cookies.get(csrf_cookie_name("csrf_token", settings), "")
    session = request.cookies.get(csrf_cookie_name("csrf_session", settings), "")
    if (
        not header
        or len(header) > MAX_CSRF_TOKEN_LENGTH
        or len(cookie) > MAX_CSRF_TOKEN_LENGTH
        or not hmac.compare_digest(header.encode(), cookie.encode())
        or not verify_csrf_token(session, _PRE_SESSION_CONTEXT, settings.csrf_secret)
        or not verify_csrf_token(header, f"pre:{session}", settings.csrf_secret)
    ):
        raise InvalidCsrfTokenError()
