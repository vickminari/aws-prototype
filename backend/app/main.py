"""Ponto de entrada da API: cria o app, registra routers e handlers de erro."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.controllers import auth_controller, health_controller, user_controller
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DatabaseUnavailableError,
    DomainError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidCsrfTokenError,
    InvalidImageError,
    InvalidPasswordError,
    InvalidTokenError,
    NotFoundError,
    UsernameAlreadyExistsError,
    WrongPasswordError,
)
from app.dependencies import get_storage
from app.schemas.error import ValidationErrorRead, ValidationIssue, error_response
from app.services.storage import create_storage

API_PREFIX = "/api"

# Exceção de domínio → status HTTP (ARQ §5.2). Subclasses herdam o status da classe-mãe;
# exceções fora do mapa viram 400.
DOMAIN_ERROR_STATUS: dict[type[DomainError], int] = {
    EmailAlreadyExistsError: 409,
    UsernameAlreadyExistsError: 409,
    InvalidCredentialsError: 401,
    InvalidCsrfTokenError: 403,
    InvalidTokenError: 401,
    WrongPasswordError: 400,
    InvalidPasswordError: 422,
    InvalidImageError: 422,
    NotFoundError: 404,
    DatabaseUnavailableError: 503,
}
DEFAULT_DOMAIN_ERROR_STATUS = 400
INTERNAL_ERROR_DETAIL = "Erro interno do servidor"
INTERNAL_ERROR_CODE = "INTERNAL_ERROR"

logger = logging.getLogger(__name__)


def _status_for(exc: DomainError) -> int:
    for cls in type(exc).__mro__:
        if cls in DOMAIN_ERROR_STATUS:
            return DOMAIN_ERROR_STATUS[cls]
    return DEFAULT_DOMAIN_ERROR_STATUS


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = _status_for(exc)
    # RFC 6750: respostas 401 indicam o esquema de autenticação esperado
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
        headers=headers,
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # A mensagem original vai só para o log: pode conter dados internos
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": INTERNAL_ERROR_DETAIL, "code": INTERNAL_ERROR_CODE},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Preserva os erros por campo sem devolver entradas ou contexto sensível.

    O handler padrão pode ecoar a senha em `input`, inclusive dentro do corpo
    inteiro quando um campo obrigatório está ausente.
    """
    return JSONResponse(
        status_code=422,
        content=ValidationErrorRead(
            detail=[ValidationIssue.model_validate(error) for error in exc.errors()]
        ).model_dump(mode="json"),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Monta a aplicação FastAPI.

    Args:
        settings: configuração a usar; se omitida, lê das variáveis de ambiente.
            Os testes passam um `Settings` próprio para variar CORS, ambiente etc.
    """
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    app = FastAPI(
        title="Protótipo 1 — API",
        description="Cadastro, login com JWT e perfil de usuário (TES/UFPI).",
        version="0.1.0",
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
        redoc_url=None,
        responses={
            500: error_response(
                "Erro inesperado no servidor",
                detail=INTERNAL_ERROR_DETAIL,
                code=INTERNAL_ERROR_CODE,
            )
        },
    )

    # Dependências HTTP usam a mesma configuração da instância da aplicação.
    app.dependency_overrides[get_settings] = lambda: settings

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    app.include_router(health_controller.router, prefix=API_PREFIX)
    app.include_router(auth_controller.router, prefix=API_PREFIX)
    app.include_router(user_controller.router, prefix=API_PREFIX)
    app.dependency_overrides[get_storage] = lambda: create_storage(settings)
    if settings.storage_backend == "local":
        media_root = Path(__file__).resolve().parents[1] / "media"
        media_root.mkdir(parents=True, exist_ok=True)
        app.mount(f"{API_PREFIX}/media", StaticFiles(directory=media_root), name="media")
    return app


app = create_app()
