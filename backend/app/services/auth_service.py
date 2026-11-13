"""Regras de cadastro e autenticação, independentes da camada HTTP."""

from datetime import datetime
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    UsernameAlreadyExistsError,
)
from app.core.security import hash_password, verify_password
from app.models import RevokedToken, User
from app.schemas.user import UserCreate

# Calculado uma vez por processo para verificar uma senha mesmo sem usuário.
# Evita o retorno antecipado que eliminaria o custo do Argon2 nesse caminho.
_DUMMY_PASSWORD_HASH = hash_password(token_urlsafe(32))


def authenticate(db: Session, identifier: str, password: str) -> User:
    """Autentica por username ou email, sem alterar a senha ou o usuário.

    Raises:
        InvalidCredentialsError: se as credenciais forem inválidas ou o usuário
            estiver inativo, sempre com a mesma mensagem pública.
    """
    normalized_identifier = identifier.lower()
    user = db.scalar(
        select(User).where(
            (User.username == normalized_identifier) | (User.email == normalized_identifier)
        )
    )
    hashed_password = user.hashed_password if user is not None else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, hashed_password)
    if user is None or not password_matches or not user.is_active:
        raise InvalidCredentialsError()
    return user


def _parse_subject(subject: str) -> UUID:
    """Converte o `sub` no UUID canônico emitido no login.

    Raises:
        InvalidTokenError: se o valor não for um UUID canônico.
    """
    try:
        user_id = UUID(subject)
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidTokenError() from exc
    # Rejeita variações aceitas por UUID() (sem hífens, chaves, urn:) não emitidas por nós.
    if str(user_id) != subject:
        raise InvalidTokenError()
    return user_id


def get_session_user(db: Session, subject: str, jti: str) -> User:
    """Resolve o usuário de um JWT já validado, checando revogação e status.

    Args:
        subject: claim `sub`; deve ser o UUID canônico emitido no login.
        jti: identificador da sessão, consultado na lista de revogação.

    Raises:
        InvalidTokenError: se o `sub` for malformado, o `jti` estiver revogado
            ou o usuário não existir ou estiver inativo.
    """
    user_id = _parse_subject(subject)
    if db.get(RevokedToken, jti) is not None:
        raise InvalidTokenError()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError()
    return user


def logout(db: Session, subject: str, jti: str, expires_at: datetime) -> None:
    """Revoga a sessão `jti` até a expiração original do JWT; é idempotente.

    Um `jti` já revogado, inclusive por outro logout concorrente, não gera erro
    nem um segundo registro.

    Raises:
        InvalidTokenError: se o `sub` não for um UUID canônico.
        IntegrityError: se outra restrição do banco impedir a revogação.
    """
    user_id = _parse_subject(subject)
    if db.get(RevokedToken, jti) is not None:
        return
    db.add(RevokedToken(jti=jti, user_id=user_id, expires_at=expires_at))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Outro logout pode ter gravado o mesmo jti após a checagem acima.
        if db.get(RevokedToken, jti) is None:
            raise


def _ensure_unique_identity(db: Session, email: str, username: str) -> None:
    """Checa os identificadores normalizados, inclusive de usuários inativos."""
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EmailAlreadyExistsError()
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise UsernameAlreadyExistsError()


def register(db: Session, payload: UserCreate) -> User:
    """Normaliza os identificadores e persiste um usuário com senha em hash.

    Raises:
        EmailAlreadyExistsError: se o email já estiver cadastrado.
        UsernameAlreadyExistsError: se o username já estiver cadastrado.
        IntegrityError: se outra restrição do banco impedir o cadastro.
    """
    email = payload.email.lower()
    username = payload.username.lower()
    _ensure_unique_identity(db, email, username)

    user = User(
        full_name=payload.full_name,
        username=username,
        email=email,
        hashed_password=hash_password(payload.password),
        description=payload.description,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Outro cadastro pode ter gravado os identificadores após a consulta
        # inicial. Reconsulta após rollback sem depender de mensagens do driver.
        _ensure_unique_identity(db, email, username)
        raise

    db.refresh(user)
    return user
