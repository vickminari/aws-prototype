from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseUnavailableError
from app.dependencies import get_db
from app.schemas.error import error_response
from app.schemas.health import HealthLiveRead, HealthRead
from app.services import health_service

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthRead,
    summary="Verifica se a API e o banco estão no ar",
    description="Usado pelo healthcheck do Docker e pelo deploy. Não exige autenticação.",
    responses={
        200: {"description": "API e banco funcionando"},
        503: error_response("Banco de dados indisponível", DatabaseUnavailableError),
    },
)
def health(db: Session = Depends(get_db)) -> HealthRead:
    health_service.check_database(db)
    return HealthRead(status="ok", db="ok")


@router.get(
    "/health/live",
    response_model=HealthLiveRead,
    summary="Verifica se o processo da API responde (sem consultar o banco)",
    description=(
        "Health check do target group do ALB (ADR-027). Não toca no banco: uma oscilação "
        "do RDS não pode fazer o Auto Scaling trocar todas as instâncias. "
        "Não exige autenticação."
    ),
    responses={200: {"description": "API no ar"}},
)
def health_live() -> HealthLiveRead:
    return HealthLiveRead(status="ok")
