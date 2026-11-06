"""Configuração da aplicação lida de variáveis de ambiente (ARQ §5.8)."""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Valor só para desenvolvimento; em produção o segredo vem do Parameter Store.
DEV_JWT_SECRET = "dev-inseguro-troque-em-producao-0000000"
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Variáveis de ambiente da API.

    Cada campo corresponde a uma variável em maiúsculas (ex.: `jwt_secret` ← `JWT_SECRET`).
    Em desenvolvimento os valores vêm de `backend/.env` (ver `.env.example`).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_expire_minutes: int = Field(default=60, gt=0)
    storage_backend: Literal["local", "s3"] = "local"
    s3_bucket: str | None = None
    aws_region: str = "us-east-2"
    # NoDecode: aceita "a,b" no .env em vez de exigir JSON
    cors_origins: Annotated[list[str], NoDecode] = []
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Converte `"http://a, http://b"` em `["http://a", "http://b"]`."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        """Impede subir a API com configuração insegura ou incompleta.

        Raises:
            ValueError: se em produção o `JWT_SECRET` for o padrão de dev ou curto demais,
                ou se `STORAGE_BACKEND=s3` sem `S3_BUCKET`.
        """
        if self.environment == "prod" and (
            self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH
        ):
            raise ValueError(
                f"JWT_SECRET de produção deve ter ao menos {MIN_JWT_SECRET_LENGTH} caracteres "
                "e não pode ser o valor padrão de desenvolvimento"
            )
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("S3_BUCKET é obrigatório quando STORAGE_BACKEND=s3")
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna a configuração carregada uma única vez por processo."""
    return Settings()
