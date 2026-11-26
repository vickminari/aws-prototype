from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime, utcnow


class User(Base):
    """Usuário cadastrado (ARQ §5.4).

    `username` e `email` são únicos e devem chegar aqui já em minúsculas (regra dos services).
    `hashed_password` nunca é retornado pela API.
    `storage_used_bytes` é a cota usada (sprint 2) e nunca fica negativa.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("storage_used_bytes >= 0", name="storage_used_bytes_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(120))
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Chave do objeto no storage (S3 ou disco), não a URL: a URL pré-assinada expira
    profile_image_key: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Soma dos originais enviados, inclusive reservas de uploads em andamento (ADR-022).
    # A imagem de perfil não conta. Alterado só pelo quota_service.
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
