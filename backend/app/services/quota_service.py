"""Cota de armazenamento por usuário (ARQ §5.12, ADR-022).

Só o arquivo original conta; miniaturas, versões de vídeo e a imagem de perfil, não.
As funções não fazem commit: quem chama confirma a transação junto com o registro do
arquivo (#69) ou com a exclusão (#70), para a cota e os arquivos nunca divergirem.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import QuotaExceededError
from app.models import User

BYTES_PER_MB = 1024 * 1024


@dataclass(frozen=True)
class StorageUsage:
    """Uso atual da cota de um usuário, em bytes."""

    used_bytes: int
    quota_bytes: int


def format_megabytes(size_bytes: int) -> str:
    """Formata bytes em MB com até uma casa decimal e vírgula (ex.: `1,5`, `100`)."""
    return f"{size_bytes / BYTES_PER_MB:.1f}".removesuffix(".0").replace(".", ",")


def reserve(db: Session, user_id: UUID, size_bytes: int, *, quota_bytes: int) -> None:
    """Reserva `size_bytes` na cota do usuário, de forma atômica.

    Um único `UPDATE ... WHERE storage_used_bytes + n <= quota` soma e confere o limite
    no mesmo comando: dois uploads simultâneos não conseguem passar juntos da cota,
    tanto no PostgreSQL quanto no SQLite dos testes.

    Raises:
        ValueError: se `size_bytes` não for positivo (o schema já impede isso).
        QuotaExceededError: se o arquivo não couber, com o espaço livre na mensagem.
    """
    if size_bytes <= 0:
        raise ValueError("size_bytes deve ser positivo")
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.storage_used_bytes + size_bytes <= quota_bytes)
        .values(storage_used_bytes=User.storage_used_bytes + size_bytes)
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount == 0:
        raise QuotaExceededError(_quota_message(db, user_id, quota_bytes))


def release(db: Session, user_id: UUID, size_bytes: int) -> None:
    """Devolve `size_bytes` à cota (exclusão, falha de validação, upload abandonado).

    O valor nunca fica negativo: se a devolução passar do que está em uso, o uso vai a 0.
    Tamanhos não positivos são ignorados.
    """
    if size_bytes <= 0:
        return
    db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            storage_used_bytes=case(
                (User.storage_used_bytes > size_bytes, User.storage_used_bytes - size_bytes),
                else_=0,
            )
        )
        .execution_options(synchronize_session="fetch")
    )


def usage(db: Session, user_id: UUID, *, quota_bytes: int) -> StorageUsage:
    """Uso atual da cota, lido do banco (inclui reservas de uploads em andamento)."""
    used = db.scalar(select(User.storage_used_bytes).where(User.id == user_id)) or 0
    return StorageUsage(used_bytes=used, quota_bytes=quota_bytes)


def _quota_message(db: Session, user_id: UUID, quota_bytes: int) -> str:
    free = max(quota_bytes - usage(db, user_id, quota_bytes=quota_bytes).used_bytes, 0)
    adjective = "livre" if free < 2 * BYTES_PER_MB else "livres"
    return (
        f"Cota de {format_megabytes(quota_bytes)} MB excedida: "
        f"você tem {format_megabytes(free)} MB {adjective}"
    )
