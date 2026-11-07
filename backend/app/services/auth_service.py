"""Regras de cadastro de usuários, independentes da camada HTTP."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyExistsError, UsernameAlreadyExistsError
from app.core.security import hash_password
from app.models import User
from app.schemas.user import UserCreate


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
