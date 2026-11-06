from fastapi import APIRouter

from app.schemas.health import HealthRead

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthRead,
    summary="Verifica se a API está no ar",
    description="Usado pelo healthcheck do Docker e pelo deploy. Não exige autenticação.",
    responses={200: {"description": "API funcionando"}},
)
def health() -> HealthRead:
    return HealthRead(status="ok")
