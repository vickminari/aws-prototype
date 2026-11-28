"""MODEL: entidades SQLAlchemy (ARQ §5.4).

Todo modelo novo deve ser importado aqui: o Alembic (`alembic/env.py`) e os testes
enxergam as tabelas por meio de `Base.metadata` depois deste import.
"""

from app.models.media import (
    AudioMetadata,
    ImageMetadata,
    MediaObject,
    MediaVariant,
    Tag,
    VideoMetadata,
    media_tags,
)
from app.models.revoked_token import RevokedToken
from app.models.user import User

__all__ = [
    "AudioMetadata",
    "ImageMetadata",
    "MediaObject",
    "MediaVariant",
    "RevokedToken",
    "Tag",
    "User",
    "VideoMetadata",
    "media_tags",
]
