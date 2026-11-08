from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidPasswordError,
    UsernameAlreadyExistsError,
    WrongPasswordError,
)
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import PasswordChange, UserProfileRead, UserUpdate


def to_read(user: User) -> UserProfileRead:
    """Converte um usuário em sua representação pública."""
    return UserProfileRead(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        profile_image_url=None,
        description=user.description,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def update_profile(db: Session, user: User, payload: UserUpdate) -> User:
    """Atualiza somente os campos enviados no perfil do usuário."""
    updates = payload.model_dump(exclude_unset=True)

    if "username" in updates:
        updates["username"] = updates["username"].lower()
        if db.scalar(select(User).where(User.username == updates["username"], User.id != user.id)):
            raise UsernameAlreadyExistsError()

    if "email" in updates:
        updates["email"] = updates["email"].lower()
        if db.scalar(select(User).where(User.email == updates["email"], User.id != user.id)):
            raise EmailAlreadyExistsError()

    for field, value in updates.items():
        setattr(user, field, value)

    if updates:
        user.updated_at = utcnow()
        db.commit()
        db.refresh(user)
    return user


def change_password(db: Session, user: User, payload: PasswordChange) -> None:
    """Troca a senha após validar a senha atual e a nova senha."""
    if not verify_password(payload.current_password, user.hashed_password):
        raise WrongPasswordError()
    if len(payload.new_password) < 8 or verify_password(payload.new_password, user.hashed_password):
        raise InvalidPasswordError()

    user.hashed_password = hash_password(payload.new_password)
    user.updated_at = utcnow()
    db.commit()
