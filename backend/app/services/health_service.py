"""Verificações de saúde da aplicação usadas por `GET /api/health`."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)


def check_database(db: Session) -> None:
    """Confirma que o banco responde executando `SELECT 1`.

    Raises:
        DatabaseUnavailableError: se a consulta falhar (banco fora do ar, credenciais
            erradas, rede bloqueada etc.).
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Só o tipo do erro: a mensagem do driver pode trazer host e usuário do banco
        logger.warning("Health check: banco indisponível (%s)", type(exc).__name__)
        raise DatabaseUnavailableError() from exc
