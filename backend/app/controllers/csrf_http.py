"""Pré-sessão CSRF e validação de origem na camada HTTP."""

import hmac

from fastapi import Request, Response

from app.controllers.auth_cookies import (
    clear_auth_cookie,
    clear_session_cookie,
    read_session_claims,
    session_cookie_name,
    set_session_cookie,
)
from app.core.config import Settings
from app.core.csrf import (
    MAX_CSRF_TOKEN_LENGTH,
    create_csrf_token,
    csrf_token_remaining,
    verify_csrf_token,
)
from app.core.exceptions import InvalidCsrfTokenError, InvalidTokenError
from app.core.origins import parse_origin

_PRE_SESSION_CONTEXT = "csrf-pre-session-cookie-v1"


def _require_trusted_origin(request: Request, settings: Settings) -> None:
    """Origin presente prevalece sobre Referer; ausência/duplicação falha fechada."""
    origins = request.headers.getlist("origin")
    references = request.headers.getlist("referer")
    if origins:
        source = parse_origin(origins[0]) if len(origins) == 1 else None
    else:
        source = parse_origin(references[0], referer=True) if len(references) == 1 else None
    if source is None or source not in settings.csrf_trusted_origin_keys:
        raise InvalidCsrfTokenError()


def issue_csrf_token(request: Request, response: Response, settings: Settings) -> str:
    """Emite CSRF vinculado ao JWT válido ou inicia/reutiliza uma pré-sessão."""
    try:
        binding = _authenticated_binding(request, settings)
    except InvalidTokenError:
        # Permite obter uma pré-sessão para novo login após o JWT expirar.
        # Escritas com JWT inválido continuam falhando, sem fallback de sessão.
        clear_auth_cookie(response, settings)
        binding = None
    if binding is not None:
        return _issue_authenticated_csrf(response, binding, settings, request)
    session = request.cookies.get(session_cookie_name("csrf_session", settings), "")
    lifetime = settings.csrf_expire_minutes * 60
    if not _is_fresh(session, _PRE_SESSION_CONTEXT, settings):
        # Renova a pré-sessão na segunda metade da validade, em vez de prolongá-la: a
        # expiração assinada continua limitando cada pré-sessão.
        session = create_csrf_token(_PRE_SESSION_CONTEXT, settings.csrf_secret, expires_in=lifetime)
    token = _current_or_new_token(
        request, f"pre:{session}", settings, max_lifetime=csrf_token_remaining(session)
    )
    for name, value in (("csrf_session", session), ("csrf_token", token)):
        set_session_cookie(response, name, value, max_age=lifetime, settings=settings)
    response.headers["Cache-Control"] = "no-store"
    return token


def _authenticated_binding(request: Request, settings: Settings) -> str | None:
    """Obtém o jti somente depois de validar assinatura e expiração do JWT."""
    claims = read_session_claims(request, settings)
    return None if claims is None else f"auth:{claims['jti']}"


def clear_csrf_cookies(response: Response, settings: Settings) -> None:
    """Remove pré-sessão e token CSRF, encerrando o estado CSRF do navegador."""
    for name in ("csrf_session", "csrf_token"):
        clear_session_cookie(response, name, settings)


def _is_fresh(token: str, binding: str, settings: Settings) -> bool:
    """Válido para o vínculo e com ao menos metade da validade configurada pela frente."""
    return verify_csrf_token(token, binding, settings.csrf_secret) and (
        csrf_token_remaining(token) * 2 >= settings.csrf_expire_minutes * 60
    )


def _current_or_new_token(
    request: Request | None, binding: str, settings: Settings, *, max_lifetime: int | None = None
) -> str:
    """Reaproveita o token do cookie enquanto estiver fresco para o mesmo vínculo.

    Assim um GET de outra aba (ou uma navegação vinda de outro site) não invalida o token
    que uma aba já mantém em memória. Um token novo nunca vence depois do vínculo.
    """
    if request is not None:
        current = request.cookies.get(session_cookie_name("csrf_token", settings), "")
        if _is_fresh(current, binding, settings):
            return current
    lifetime = settings.csrf_expire_minutes * 60
    if max_lifetime is not None:
        lifetime = min(lifetime, max_lifetime)
    return create_csrf_token(binding, settings.csrf_secret, expires_in=lifetime)


def _issue_authenticated_csrf(
    response: Response, binding: str, settings: Settings, request: Request | None = None
) -> str:
    """Descarta a pré-sessão e entrega o token ligado à sessão autenticada.

    Sem `request` (rotação no login), sempre emite um token novo.
    """
    lifetime = settings.csrf_expire_minutes * 60
    token = _current_or_new_token(request, binding, settings)
    clear_session_cookie(response, "csrf_session", settings)
    set_session_cookie(response, "csrf_token", token, max_age=lifetime, settings=settings)
    response.headers["Cache-Control"] = "no-store"
    return token


def rotate_csrf_after_login(response: Response, jti: str, settings: Settings) -> None:
    """Renova o cookie CSRF após login; o frontend obtém o valor por GET /auth/csrf."""
    _issue_authenticated_csrf(response, f"auth:{jti}", settings)


def validate_csrf_request(request: Request, settings: Settings) -> None:
    """Valida origem, double-submit e vínculo à sessão antes de uma escrita.

    Raises:
        InvalidCsrfTokenError: se origem, cookies, header ou assinatura forem inválidos.
    """
    _require_trusted_origin(request, settings)
    headers = request.headers.getlist("x-csrf-token")
    header = headers[0] if len(headers) == 1 else ""
    cookie = request.cookies.get(session_cookie_name("csrf_token", settings), "")
    if (
        not header
        or len(header) > MAX_CSRF_TOKEN_LENGTH
        or len(cookie) > MAX_CSRF_TOKEN_LENGTH
        or not hmac.compare_digest(header.encode(), cookie.encode())
    ):
        raise InvalidCsrfTokenError()
    try:
        binding = _authenticated_binding(request, settings)
    except InvalidTokenError as exc:
        raise InvalidCsrfTokenError() from exc
    if binding is None:
        session = request.cookies.get(session_cookie_name("csrf_session", settings), "")
        if not verify_csrf_token(session, _PRE_SESSION_CONTEXT, settings.csrf_secret):
            raise InvalidCsrfTokenError()
        binding = f"pre:{session}"
    if not verify_csrf_token(header, binding, settings.csrf_secret):
        raise InvalidCsrfTokenError()
