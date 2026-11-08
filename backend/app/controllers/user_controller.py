from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidTokenError
from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.error import error_response
from app.schemas.user import PasswordChange, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Retorna o usuário logado",
    responses={401: error_response("Não autenticado", InvalidTokenError)},
)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return user_service.to_read(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Atualiza o perfil do usuário logado",
    responses={401: error_response("Não autenticado", InvalidTokenError)},
)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return user_service.to_read(user_service.update_profile(db, current_user, payload))


@router.put(
    "/me/password",
    status_code=204,
    summary="Troca a senha do usuário logado",
    responses={401: error_response("Não autenticado", InvalidTokenError)},
)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    user_service.change_password(db, current_user, payload)
    return Response(status_code=204)
