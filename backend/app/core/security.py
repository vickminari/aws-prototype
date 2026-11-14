"""Hash de senha e tokens de acesso, sem dependências da camada HTTP."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidTokenError

_password_hash = PasswordHash.recommended()
_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Gera um hash Argon2id com salt aleatório para armazenamento."""
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Confere a senha em texto contra o hash armazenado."""
    return _password_hash.verify(password, hashed_password)


def create_access_token(user_id: UUID, *, settings: Settings | None = None) -> str:
    """Assina um JWT com o UUID do usuário em sub, ID único e validade configurada."""
    settings = settings or get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        },
        settings.jwt_secret,
        algorithm=_JWT_ALGORITHM,
    )


def decode_access_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Valida assinatura, algoritmo, campos obrigatórios e validade do JWT.

    Raises:
        InvalidTokenError: se o token estiver expirado, adulterado ou malformado.

    A consulta de revogação do jti e a verificação do usuário ativo cabem à
    camada de autenticação (#9); esta função não consulta o banco.
    """
    try:
        claims = jwt.decode(
            token,
            (settings or get_settings()).jwt_secret,
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["sub", "jti", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError() from exc

    if not claims["sub"] or not claims["jti"]:
        raise InvalidTokenError()
    return claims
