from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidImageError,
    InvalidPasswordError,
    UsernameAlreadyExistsError,
    WrongPasswordError,
)
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import PasswordChange, UserProfileRead, UserUpdate
from app.services.storage.base import StorageService, read_image


def to_read(user: User, storage: StorageService | None = None) -> UserProfileRead:
    """Converte um usuário em sua representação pública."""
    return UserProfileRead(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        profile_image_url=storage.get_url(user.profile_image_key)
        if storage and user.profile_image_key
        else None,
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


def update_avatar(db: Session, user: User, file: UploadFile, storage: StorageService) -> User:
    """Validates, stores and associates a new profile image."""
    try:
        _, extension = read_image(file)
    except ValueError as exc:
        raise InvalidImageError() from exc

    old_key = user.profile_image_key
    key = f"avatars/{user.id}/{uuid4()}.{extension}"
    storage.upload(key, file)
    if old_key:
        storage.delete(old_key)
    user.profile_image_key = key
    user.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return user


def delete_avatar(db: Session, user: User, storage: StorageService) -> User:
    """Removes the current profile image, if one exists."""
    if user.profile_image_key:
        storage.delete(user.profile_image_key)
        user.profile_image_key = None
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
