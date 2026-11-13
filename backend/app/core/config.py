"""Configuração da aplicação lida de variáveis de ambiente (ARQ §5.8)."""

from functools import cached_property, lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.origins import Origin, parse_origin

# Valor só para desenvolvimento; em produção o segredo vem do Parameter Store.
DEV_JWT_SECRET = "dev-inseguro-troque-em-producao-0000000"
DEV_CSRF_SECRET = "dev-csrf-inseguro-troque-em-producao-0000000"
MIN_JWT_SECRET_LENGTH = 32
MIN_CSRF_SECRET_LENGTH = 32


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
    csrf_secret: str = Field(default=DEV_CSRF_SECRET, repr=False)
    csrf_expire_minutes: int = Field(default=60, gt=0)
    csrf_trusted_origins: Annotated[list[str], NoDecode] = []
    storage_backend: Literal["local", "s3"] = "local"
    s3_bucket: str | None = None
    aws_region: str = "us-east-2"
    # NoDecode: aceita "a,b" no .env em vez de exigir JSON
    cors_origins: Annotated[list[str], NoDecode] = []
    log_level: str = "INFO"

    @field_validator("cors_origins", "csrf_trusted_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Converte `"http://a, http://b"` em `["http://a", "http://b"]`."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("csrf_trusted_origins")
    @classmethod
    def _validate_csrf_origins(cls, origins: list[str]) -> list[str]:
        """Aceita apenas origens HTTP(S) explícitas, sem credenciais ou curingas."""
        normalized = [origin.removesuffix("/") for origin in origins]
        for origin in normalized:
            # Mesmo parser da validação das requisições, para não divergirem.
            if "*" in origin or parse_origin(origin) is None:
                raise ValueError("CSRF_TRUSTED_ORIGINS exige origens HTTP(S) explícitas")
        return normalized

    @cached_property
    def csrf_trusted_origin_keys(self) -> frozenset[Origin]:
        """Origens confiáveis já normalizadas em `(esquema, host, porta)`, calculadas uma vez."""
        return frozenset(filter(None, map(parse_origin, self.csrf_trusted_origins)))

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        """Impede subir a API com configuração insegura ou incompleta.

        Raises:
            ValueError: se em produção o `JWT_SECRET` for o padrão de dev ou curto demais,
                se CSRF estiver inseguro/incompleto, ou se `STORAGE_BACKEND=s3` sem `S3_BUCKET`.
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
        if len(self.csrf_secret) < MIN_CSRF_SECRET_LENGTH or self.csrf_secret == self.jwt_secret:
            raise ValueError(
                "CSRF_SECRET deve ter ao menos 32 caracteres e ser diferente de JWT_SECRET"
            )
        if self.environment == "prod":
            if self.csrf_secret == DEV_CSRF_SECRET:
                raise ValueError("CSRF_SECRET de produção não pode ser o padrão de desenvolvimento")
            if not self.csrf_trusted_origin_keys or any(
                scheme != "https" for scheme, _, _ in self.csrf_trusted_origin_keys
            ):
                raise ValueError("Produção exige CSRF_TRUSTED_ORIGINS explícitas com HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna a configuração carregada uma única vez por processo."""
    return Settings()
