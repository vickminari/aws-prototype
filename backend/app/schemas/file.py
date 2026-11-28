"""Contratos públicos dos arquivos de mídia e da cota (ARQ §5.5, sprint 2).

Usados pelo upload (#69), pela listagem, detalhe e edição (#70) e pelo frontend (#66).
URLs de miniatura, visualização, download e versões são pré-assinadas pelo service e
só aparecem depois da checagem de dono (ADR-029).
"""

from datetime import datetime
from typing import Annotated, Literal, get_args
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

MediaType = Literal["image", "audio", "video"]
MediaStatus = Literal["pending_upload", "queued", "processing", "ready", "failed"]
# Formatos da especificação (ARQ §5.11). O MIME gravado é sempre o detectado pelo conteúdo.
AcceptedContentType = Literal[
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/svg+xml",
    "image/webp",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/flac",
    "video/mp4",
    "video/x-msvideo",
    "video/quicktime",
    "video/webm",
]
ACCEPTED_CONTENT_TYPES: frozenset[str] = frozenset(get_args(AcceptedContentType))

MAX_TAGS = 10
MAX_TAG_LENGTH = 40

FileName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


def media_type_for(content_type: str) -> MediaType:
    """Tipo de mídia (`image`, `audio` ou `video`) de um MIME aceito."""
    return content_type.split("/", 1)[0]  # type: ignore[return-value]


class UploadInit(BaseModel):
    """Início de um upload: o arquivo ainda está no navegador.

    O limite por arquivo (`MAX_UPLOAD_BYTES`) e a cota são conferidos pelo service, que
    responde 422 `FILE_TOO_LARGE` ou 413 `QUOTA_EXCEEDED`.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"filename": "praia.jpg", "size_bytes": 2048576, "content_type": "image/jpeg"}
            ]
        }
    )

    filename: FileName
    size_bytes: int = Field(gt=0)
    content_type: AcceptedContentType


class UploadForm(BaseModel):
    """Formulário do POST pré-assinado: o navegador envia `fields` + o arquivo para `url`."""

    url: str
    fields: dict[str, str]


class UploadTicket(BaseModel):
    """Resposta da iniciação do upload. `expires_in` é a validade do formulário, em segundos."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "file_id": "0b7d5a8e-6c1f-4d0e-9a51-2f6f9f3c1a10",
                    "upload": {
                        "url": "https://proto2-media-exemplo.s3.amazonaws.com/",
                        "fields": {
                            "key": "users/<uid>/images/<file_id>/original.jpg",
                            "Content-Type": "image/jpeg",
                            "policy": "<base64>",
                        },
                    },
                    "expires_in": 900,
                }
            ]
        }
    )

    file_id: UUID
    upload: UploadForm
    expires_in: int


class ImageMetadataRead(BaseModel):
    """Propriedades de uma imagem; GPS só chega aqui para o dono (todas as rotas são do dono)."""

    model_config = ConfigDict(from_attributes=True)

    width: int | None = None
    height: int | None = None
    color_depth_bits: int | None = None
    dpi_x: float | None = None
    dpi_y: float | None = None
    format: str | None = None
    is_animated: bool = False
    exif: dict[str, object] | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    taken_at: datetime | None = None
    exposure_time: str | None = None
    f_number: float | None = None
    iso: int | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None


class VideoMetadataRead(BaseModel):
    """Propriedades de um vídeo (ffprobe)."""

    model_config = ConfigDict(from_attributes=True)

    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    bitrate: int | None = None
    container: str | None = None


class AudioMetadataRead(BaseModel):
    """Propriedades de um áudio (ffprobe)."""

    model_config = ConfigDict(from_attributes=True)

    duration_seconds: float | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    codec: str | None = None


class VariantRead(BaseModel):
    """Versão de reprodução de um vídeo, com URL pré-assinada."""

    model_config = ConfigDict(from_attributes=True)

    label: str
    width: int
    height: int
    size_bytes: int
    url: str
    is_original: bool


class FileSummary(BaseModel):
    """Item da listagem do drive."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "0b7d5a8e-6c1f-4d0e-9a51-2f6f9f3c1a10",
                    "name": "praia.jpg",
                    "media_type": "image",
                    "mime_type": "image/jpeg",
                    "size_bytes": 2048576,
                    "status": "ready",
                    "thumbnail_url": "https://proto2-media-exemplo.s3.amazonaws.com/...",
                    "duration_seconds": None,
                    "tags": ["praia", "férias"],
                    "created_at": "2026-11-27T14:00:00Z",
                }
            ]
        },
    )

    id: UUID
    name: str
    media_type: MediaType
    mime_type: str
    size_bytes: int
    status: MediaStatus
    thumbnail_url: str | None
    duration_seconds: float | None
    tags: list[str]
    created_at: datetime


class FileDetail(FileSummary):
    """Detalhe de um arquivo: só o bloco do próprio tipo vem preenchido (`image`, `video`
    ou `audio`). `default_variant` é a maior versão ≤ 1080p, ou `null`."""

    original_filename: str
    description: str | None
    genre: str | None
    error_code: str | None
    updated_at: datetime
    processed_at: datetime | None
    view_url: str | None
    download_url: str | None
    image: ImageMetadataRead | None = None
    video: VideoMetadataRead | None = None
    audio: AudioMetadataRead | None = None
    variants: list[VariantRead] = []
    default_variant: str | None = None


class FilePage(BaseModel):
    """Página da listagem (`page_size` de 1 a 50, padrão 24)."""

    items: list[FileSummary]
    total: int
    page: int
    page_size: int


class FileUpdate(BaseModel):
    """Edição parcial: só os campos enviados mudam. `tags` substitui a lista inteira;
    `genre` é ignorado em imagens (regra do service)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Pôr do sol", "description": "Praia de Atalaia", "tags": ["praia"]}
            ]
        }
    )

    name: FileName | None = None
    description: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS)
    genre: str | None = Field(default=None, max_length=50)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, tags: list[str] | None) -> list[str] | None:
        """Minúsculas, sem espaços nas pontas e sem repetição, mantendo a ordem."""
        if tags is None:
            return None
        normalized: list[str] = []
        for tag in tags:
            value = tag.strip().lower()
            if not 1 <= len(value) <= MAX_TAG_LENGTH:
                raise ValueError(f"Cada tag deve ter de 1 a {MAX_TAG_LENGTH} caracteres")
            if value not in normalized:
                normalized.append(value)
        return normalized


class StorageUsageRead(BaseModel):
    """Uso da cota do usuário logado, em bytes."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [{"used_bytes": 52428800, "quota_bytes": 104857600}]},
    )

    used_bytes: int
    quota_bytes: int
