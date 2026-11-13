"""Tokens CSRF HMAC vinculados à sessão, sem dependência da camada HTTP."""

import hashlib
import hmac
import re
import time
from secrets import token_urlsafe

CSRF_TTL_SECONDS = 3600
MAX_CSRF_TOKEN_LENGTH = 256
_TOKEN_PATTERN = re.compile(r"v1\.([0-9]{1,12})\.([A-Za-z0-9_-]{43})\.([a-f0-9]{64})")


def _signature(payload: str, session_id: str, secret: str) -> str:
    """Separa o contexto e delimita a sessão para evitar concatenações ambíguas."""
    session = session_id.encode()
    message = b"csrf:v1:" + len(session).to_bytes(4, "big") + session + payload.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def create_csrf_token(session_id: str, secret: str, *, expires_in: int = CSRF_TTL_SECONDS) -> str:
    """Emite token aleatório assinado sem revelar o identificador da sessão.

    Raises:
        ValueError: se a sessão, o segredo ou o tempo de validade forem inválidos.
    """
    if not session_id or len(session_id) > MAX_CSRF_TOKEN_LENGTH or not secret or expires_in <= 0:
        raise ValueError("Sessão, segredo e validade CSRF devem ser válidos")
    payload = f"v1.{int(time.time()) + expires_in}.{token_urlsafe(32)}"
    return f"{payload}.{_signature(payload, session_id, secret)}"


def csrf_token_remaining(token: str) -> int:
    """Segundos até a expiração declarada no token; 0 se malformado ou vencido.

    Não verifica a assinatura: use somente depois de `verify_csrf_token`.
    """
    match = _TOKEN_PATTERN.fullmatch(token) if isinstance(token, str) else None
    if match is None:
        return 0
    return max(0, int(match[1]) - int(time.time()))


def verify_csrf_token(token: str, session_id: str, secret: str) -> bool:
    """Rejeita assinatura, sessão, formato ou expiração inválidos sem lançar erro."""
    if (
        not isinstance(token, str)
        or not isinstance(session_id, str)
        or len(token) > MAX_CSRF_TOKEN_LENGTH
        or not session_id
        or len(session_id) > MAX_CSRF_TOKEN_LENGTH
        or not secret
    ):
        return False
    match = _TOKEN_PATTERN.fullmatch(token)
    if match is None or int(match[1]) <= time.time():
        return False
    payload, signature = token.rsplit(".", 1)
    return hmac.compare_digest(signature, _signature(payload, session_id, secret))
