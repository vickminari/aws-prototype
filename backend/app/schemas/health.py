from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthRead(BaseModel):
    """Resposta do health check. Com o banco fora do ar a rota responde 503 (`ErrorRead`)."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok", "db": "ok"}]})

    status: Literal["ok"]
    db: Literal["ok"]
