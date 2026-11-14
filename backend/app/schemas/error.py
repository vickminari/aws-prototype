from typing import Any

from pydantic import BaseModel

from app.core.exceptions import DomainError, InvalidCsrfTokenError, InvalidTokenError


class ErrorRead(BaseModel):
    """Formato padrão de erro da API (ARQ §5.2). Nas rotas, use `error_response`."""

    detail: str
    code: str


class ValidationIssue(BaseModel):
    """Erro por campo; omite os valores de entrada e o contexto interno."""

    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorRead(BaseModel):
    """Contrato público das respostas 422 de validação da requisição."""

    detail: list[ValidationIssue]


def error_response(
    description: str, error: type[DomainError] | None = None, *, detail: str = "", code: str = ""
) -> dict[str, Any]:
    """Monta uma entrada de `responses=` com o exemplo do erro que a rota realmente devolve.

    Sem isso o Swagger mostraria o mesmo exemplo genérico em todos os status de erro.

    Args:
        description: texto exibido ao lado do status no Swagger.
        error: exceção de domínio; o exemplo usa o `message` e o `code` dela.
        detail: mensagem do exemplo, para erros que não são `DomainError` (ex.: 500).
        code: código do exemplo, para erros que não são `DomainError`.

    Exemplo: `responses={409: error_response("Email já cadastrado", EmailAlreadyExistsError)}`.
    """
    if error is not None:
        detail, code = error.message, error.code
    return {
        "model": ErrorRead,
        "description": description,
        "content": {"application/json": {"example": {"detail": detail, "code": code}}},
    }


# Respostas repetidas nas rotas protegidas e em todas as escritas (CSRF global em create_app).
UNAUTHENTICATED_RESPONSE = error_response("Não autenticado", InvalidTokenError)
CSRF_FAILURE_RESPONSE = error_response(
    "Origem não confiável ou X-CSRF-Token ausente, inválido ou de outra sessão",
    InvalidCsrfTokenError,
)
