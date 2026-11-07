from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.error import ErrorRead
from app.schemas.health import HealthRead
from app.services import health_service

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthRead,
    summary="Verifica se a API e o banco estão no ar",
    description="Usado pelo healthcheck do Docker e pelo deploy. Não exige autenticação.",
    responses={
        200: {"description": "API e banco funcionando"},
        503: {"model": ErrorRead, "description": "Banco de dados indisponível"},
    },
)
def health(db: Session = Depends(get_db)) -> HealthRead:
    health_service.check_database(db)
    return HealthRead(status="ok", db="ok")
