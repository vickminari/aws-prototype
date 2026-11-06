from pydantic import BaseModel, ConfigDict


class ErrorRead(BaseModel):
    """Formato padrão de erro da API (ARQ §5.2). Use em `responses=` das rotas."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"detail": "Email já cadastrado", "code": "EMAIL_ALREADY_EXISTS"}]
        }
    )

    detail: str
    code: str
