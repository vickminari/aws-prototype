"""Contratos públicos de cadastro e leitura de usuários (issue #8)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

# Regras compartilhadas por cadastro e perfil. Username nunca contém "@", e o email sempre
# contém: o login decide a coluna pelo "@", então um não pode se passar pelo outro.
Username = Annotated[str, Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_.]+$")]
Email = Annotated[EmailStr, Field(max_length=254)]


class UserCreate(BaseModel):
    """Dados de cadastro; a normalização de email/username cabe ao service."""

    model_config = ConfigDict(
        hide_input_in_errors=True,
        json_schema_extra={
            "examples": [
                {
                    "full_name": "Maria Silva",
                    "username": "maria.silva",
                    "email": "maria@example.com",
                    "password": "Senha123",
                    "description": "Descrição do perfil",
                }
            ]
        },
    )

    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ]
    # Aceita maiúsculas na entrada para o service normalizar antes de checar unicidade.
    username: Username
    email: Email
    password: str = Field(
        min_length=8,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )
    description: str | None = Field(default=None, max_length=500)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        """Exige uma letra e um número sem alterar a senha recebida."""
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("A senha deve conter ao menos uma letra e um número")
        return value


class UserRead(BaseModel):
    """Dados públicos do usuário, sem senha, hash ou chave interna de imagem."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "12345678-1234-4234-8234-123456789abc",
                    "full_name": "Maria Silva",
                    "username": "maria.silva",
                    "email": "maria@example.com",
                    "description": None,
                    "profile_image_url": None,
                    "created_at": "2026-11-07T12:00:00Z",
                }
            ]
        },
    )

    id: UUID
    full_name: str
    username: str
    email: EmailStr
    description: str | None = None
    profile_image_url: str | None = None
    created_at: datetime


class UserProfileRead(UserRead):
    """Dados públicos adicionais do perfil autenticado."""

    is_active: bool
    updated_at: datetime


class UserUpdate(BaseModel):
    """Campos aceitos na atualização parcial do perfil."""

    full_name: str | None = None
    username: Username | None = None
    email: Email | None = None
    description: str | None = None

    @field_validator("username", "email")
    @classmethod
    def _reject_explicit_null(cls, value: str | None) -> str | None:
        """Campo omitido mantém o valor; `null` explícito apagaria um campo obrigatório."""
        if value is None:
            raise ValueError("O campo não pode ser nulo")
        return value


class PasswordChange(BaseModel):
    """Dados necessários para trocar a senha do usuário."""

    current_password: str
    new_password: str = Field(min_length=8)
