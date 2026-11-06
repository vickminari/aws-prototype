from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthRead(BaseModel):
    """Resposta do health check."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok"}]})

    status: Literal["ok"]
