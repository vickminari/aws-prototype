"""Rotas de cadastro; autenticação e cookies serão implementados na issue #9."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyExistsError, UsernameAlreadyExistsError
from app.dependencies import get_db
from app.schemas.error import ErrorRead
from app.schemas.user import UserCreate, UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


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
        422: {"description": "Dados de entrada inválidos; valores enviados não são retornados"},
    },
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    return UserRead.model_validate(auth_service.register(db, payload))
