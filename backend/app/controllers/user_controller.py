from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidTokenError
from app.dependencies import get_current_user, get_db, get_storage
from app.models import User
from app.schemas.error import error_response
from app.schemas.user import PasswordChange, UserProfileRead, UserUpdate
from app.services import user_service
from app.services.storage import StorageService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserProfileRead,
    summary="Retorna o usuário logado",
    responses={401: error_response("Não autenticado", InvalidTokenError)},
)
def read_me(
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
) -> UserProfileRead:
    return user_service.to_read(current_user, storage)


@router.patch(
    "/me",
    response_model=UserProfileRead,
    summary="Atualiza o perfil do usuário logado",
    responses={401: error_response("Não autenticado", InvalidTokenError)},
)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
) -> UserProfileRead:
    return user_service.to_read(user_service.update_profile(db, current_user, payload), storage)


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


@router.post("/me/avatar", response_model=UserProfileRead, summary="Atualiza a imagem de perfil")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
) -> UserProfileRead:
    updated = user_service.update_avatar(db, current_user, file, storage)
    return user_service.to_read(updated, storage)


@router.delete("/me/avatar", response_model=UserProfileRead, summary="Remove a imagem de perfil")
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
) -> UserProfileRead:
    return user_service.to_read(user_service.delete_avatar(db, current_user, storage), storage)
