from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.exceptions import EmailAlreadyExistsError, UsernameAlreadyExistsError
from app.models import User
from app.schemas.user import UserRead, UserUpdate


def to_read(user: User) -> UserRead:
    """Converte um usuário em sua representação pública."""
    return UserRead(
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
