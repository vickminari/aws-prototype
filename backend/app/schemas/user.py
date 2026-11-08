from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserRead(BaseModel):
    """Dados públicos do usuário autenticado."""

    id: UUID
    full_name: str
    username: str
    email: str
    profile_image_url: str | None
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Campos aceitos na atualização parcial do perfil."""

    full_name: str | None = None
    username: str | None = None
    email: str | None = None
    description: str | None = None


class PasswordChange(BaseModel):
    """Dados necessários para trocar a senha do usuário."""

    current_password: str
    new_password: str = Field(min_length=8)
