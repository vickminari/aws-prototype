from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime
from app.models.user import utcnow


class RevokedToken(Base):
    """`jti` de um JWT invalidado no logout (ARQ §5.4, ADR-002).

    `expires_at` guarda a expiração original do token: depois dela o registro pode ser
    apagado, porque o próprio JWT já é rejeitado por estar expirado.
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
