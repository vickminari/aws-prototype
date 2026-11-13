"""Rotas públicas de cadastro, inicialização CSRF e login por cookie."""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.controllers.auth_session import establish_login
from app.controllers.csrf_http import issue_csrf_token
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidCsrfTokenError,
    UsernameAlreadyExistsError,
)
from app.dependencies import get_db, require_csrf
from app.schemas.auth import CsrfRead, LoginResponse
from app.schemas.error import ErrorRead, ValidationErrorRead, error_response
from app.schemas.user import UserCreate, UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(require_csrf)],
    summary="Autentica por username ou email e estabelece a sessão HttpOnly",
    description=(
        "Requer pré-sessão/cookie CSRF e X-CSRF-Token de /api/auth/csrf, além de origem confiável. "
        "Recebe formulário username/password, define cookies, descarta a pré-sessão e renova CSRF. "
        "Após o login, consulte /api/auth/csrf para obter o novo token público. Não retorna JWT."
    ),
    responses={
        401: error_response("Credenciais inválidas ou usuário inativo", InvalidCredentialsError),
        403: error_response("Falha de origem ou proteção CSRF", InvalidCsrfTokenError),
        422: {"model": ValidationErrorRead, "description": "Formulário inválido"},
    },
)
def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = auth_service.authenticate(db, form.username, form.password)
    establish_login(response, user.id, settings)
    return LoginResponse()


@router.get(
    "/csrf",
    response_model=CsrfRead,
    summary="Inicializa a pré-sessão e fornece o token CSRF",
    description="Retorna token para X-CSRF-Token e cookies HttpOnly, sem realizar login.",
)
def csrf(
    request: Request, response: Response, settings: Settings = Depends(get_settings)
) -> CsrfRead:
    return CsrfRead(csrf_token=issue_csrf_token(request, response, settings))


@router.post(
    "/register",
    status_code=201,
    response_model=UserRead,
    summary="Cadastra um usuário",
    description=(
        "Cria um usuário com email e username normalizados em minúsculas. "
        "Não realiza login nem emite cookie. Nunca retorna senha ou hash."
    ),
    responses={
        201: {"description": "Usuário cadastrado"},
        409: {
            "model": ErrorRead,
            "description": "Email ou username já cadastrado",
            "content": {
                "application/json": {
                    "examples": {
                        "email": {
                            "value": {
                                "detail": EmailAlreadyExistsError.message,
                                "code": EmailAlreadyExistsError.code,
                            }
                        },
                        "username": {
                            "value": {
                                "detail": UsernameAlreadyExistsError.message,
                                "code": UsernameAlreadyExistsError.code,
                            }
                        },
                    }
                }
            },
        },
        422: {
            "model": ValidationErrorRead,
            "description": "Dados de entrada inválidos; valores enviados não são retornados",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "password"],
                                "msg": "A senha deve conter ao menos uma letra e um número",
                                "type": "value_error",
                            }
                        ]
                    }
                }
            },
        },
    },
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    return UserRead.model_validate(auth_service.register(db, payload))
