"""Arquivos de mídia do SGM e seus dados derivados (ARQ §5.4, sprint 2).

Só tipos genéricos do SQLAlchemy, para os testes continuarem em SQLite. As regras
(cota, status, quem pode ver o quê) ficam nos services; aqui só há entidades e constraints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow

MEDIA_TYPES = ("image", "audio", "video")
# pending_upload → queued → processing → ready | failed; imagem vai direto para ready/failed
MEDIA_STATUSES = ("pending_upload", "queued", "processing", "ready", "failed")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


# Associação N:N entre arquivos e tags; some junto com o arquivo ou com a tag
media_tags = Table(
    "media_tags",
    Base.metadata,
    Column("media_id", Uuid, ForeignKey("media_objects.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Uuid, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class MediaObject(Base):
    """Um arquivo enviado (imagem, áudio ou vídeo).

    `id` também é o `file_id` das rotas e das chaves do S3. Toda consulta dos services
    filtra por `owner_id` (ADR-029). `size_bytes` é o tamanho do original, o único que
    conta na cota (ADR-022).
    """

    __tablename__ = "media_objects"
    __table_args__ = (
        CheckConstraint(_in("media_type", MEDIA_TYPES), name="media_type"),
        CheckConstraint(_in("status", MEDIA_STATUSES), name="status"),
        # Listagem do drive (filtro por tipo, ordem por data) e limpeza de uploads abandonados
        Index("ix_media_objects_owner_type_created", "owner_id", "media_type", "created_at"),
        Index("ix_media_objects_owner_status", "owner_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    media_type: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    extension: Mapped[str] = mapped_column(String(10))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default="pending_upload")
    error_code: Mapped[str | None] = mapped_column(String(50))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(String(2000))
    genre: Mapped[str | None] = mapped_column(String(50))
    # Nome + descrição + tags em minúsculas e sem acento, mantido pelo service (#70)
    search_text: Mapped[str] = mapped_column(String(3000), default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # cascade + passive_deletes: o ORM apaga os filhos carregados e o banco (ON DELETE
    # CASCADE) garante o resto, inclusive em exclusões feitas por SQL direto
    image: Mapped["ImageMetadata | None"] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    video: Mapped["VideoMetadata | None"] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    audio: Mapped["AudioMetadata | None"] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    variants: Mapped[list["MediaVariant"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list["Tag"]] = relationship(secondary=media_tags)


class ImageMetadata(Base):
    """Propriedades de uma imagem (1:1 com `MediaObject`), extraídas com Pillow (#68)."""

    __tablename__ = "image_metadata"

    media_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("media_objects.id", ondelete="CASCADE"), primary_key=True
    )
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    # Pelo modo do Pillow (RGB → 24); nulo no SVG
    color_depth_bits: Mapped[int | None] = mapped_column(Integer)
    dpi_x: Mapped[float | None] = mapped_column(Float)
    dpi_y: Mapped[float | None] = mapped_column(Float)
    format: Mapped[str | None] = mapped_column(String(10))
    is_animated: Mapped[bool] = mapped_column(Boolean, default=False)
    # Tags EXIF legíveis, sem MakerNote nem valores binários
    exif: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    camera_make: Mapped[str | None] = mapped_column(String(100))
    camera_model: Mapped[str | None] = mapped_column(String(100))
    taken_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    exposure_time: Mapped[str | None] = mapped_column(String(20))
    f_number: Mapped[float | None] = mapped_column(Float)
    iso: Mapped[int | None] = mapped_column(Integer)
    # Em graus decimais; visíveis só para o dono
    gps_lat: Mapped[float | None] = mapped_column(Float)
    gps_lon: Mapped[float | None] = mapped_column(Float)


class VideoMetadata(Base):
    """Propriedades de um vídeo (1:1 com `MediaObject`), extraídas com ffprobe (#73)."""

    __tablename__ = "video_metadata"

    media_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("media_objects.id", ondelete="CASCADE"), primary_key=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Float)
    video_codec: Mapped[str | None] = mapped_column(String(30))
    audio_codec: Mapped[str | None] = mapped_column(String(30))
    bitrate: Mapped[int | None] = mapped_column(Integer)
    container: Mapped[str | None] = mapped_column(String(30))


class AudioMetadata(Base):
    """Propriedades de um áudio (1:1 com `MediaObject`), extraídas com ffprobe (#74)."""

    __tablename__ = "audio_metadata"

    media_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("media_objects.id", ondelete="CASCADE"), primary_key=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    bitrate: Mapped[int | None] = mapped_column(Integer)
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    channels: Mapped[int | None] = mapped_column(Integer)
    codec: Mapped[str | None] = mapped_column(String(30))


class MediaVariant(Base):
    """Versão de reprodução de um vídeo (1080p, 720p, 480p...).

    `UNIQUE(media_id, label)` deixa o worker repetir um job sem duplicar versões.
    `is_original` indica que a versão é o próprio arquivo enviado, sem cópia.
    """

    __tablename__ = "media_variants"
    __table_args__ = (UniqueConstraint("media_id", "label"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    media_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("media_objects.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(10))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    # Não conta na cota (ADR-022)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(512))
    is_original: Mapped[bool] = mapped_column(Boolean, default=False)


class Tag(Base):
    """Tag do vocabulário de um usuário; `name` chega em minúsculas (regra do service)."""

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(40))
