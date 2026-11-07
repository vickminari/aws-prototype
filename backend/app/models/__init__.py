"""MODEL: entidades SQLAlchemy (ARQ §5.4).

Todo modelo novo deve ser importado aqui: o Alembic (`alembic/env.py`) e os testes
enxergam as tabelas por meio de `Base.metadata` depois deste import.
"""

from app.models.revoked_token import RevokedToken
from app.models.user import User

__all__ = ["RevokedToken", "User"]
