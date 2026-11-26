"""cria tabelas de midia e cota do usuario

Sprint 2 (#64, ARQ §5.4): arquivos de mídia, metadados por tipo, versões de vídeo, tags
e a coluna users.storage_used_bytes. Só cria tabelas e adiciona uma coluna com default,
então a versão anterior da API continua funcionando durante o instance refresh
(expand/contract, ARQ §5.9).

Revision ID: 6a2396e933d3
Revises: 702cac72104f
Create Date: 2026-11-26 17:17:42.145230
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6a2396e933d3"
down_revision: str | Sequence[str] | None = "702cac72104f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_objects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=10), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("thumbnail_key", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("genre", sa.String(length=50), nullable=True),
        sa.Column("search_text", sa.String(length=3000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "media_type IN ('image', 'audio', 'video')", name=op.f("ck_media_objects_media_type")
        ),
        sa.CheckConstraint(
            "status IN ('pending_upload', 'queued', 'processing', 'ready', 'failed')",
            name=op.f("ck_media_objects_status"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_media_objects_owner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_objects")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_media_objects_storage_key")),
    )
    # Listagem do drive por tipo e data; limpeza de uploads abandonados por status
    op.create_index(
        "ix_media_objects_owner_type_created",
        "media_objects",
        ["owner_id", "media_type", "created_at"],
    )
    op.create_index("ix_media_objects_owner_status", "media_objects", ["owner_id", "status"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_tags_owner_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("owner_id", "name", name=op.f("uq_tags_owner_id")),
    )
    op.create_table(
        "audio_metadata",
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("bitrate", sa.Integer(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("channels", sa.Integer(), nullable=True),
        sa.Column("codec", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_objects.id"],
            name=op.f("fk_audio_metadata_media_id_media_objects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("media_id", name=op.f("pk_audio_metadata")),
    )
    op.create_table(
        "image_metadata",
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("color_depth_bits", sa.Integer(), nullable=True),
        sa.Column("dpi_x", sa.Float(), nullable=True),
        sa.Column("dpi_y", sa.Float(), nullable=True),
        sa.Column("format", sa.String(length=10), nullable=True),
        sa.Column("is_animated", sa.Boolean(), nullable=False),
        sa.Column("exif", sa.JSON(), nullable=True),
        sa.Column("camera_make", sa.String(length=100), nullable=True),
        sa.Column("camera_model", sa.String(length=100), nullable=True),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exposure_time", sa.String(length=20), nullable=True),
        sa.Column("f_number", sa.Float(), nullable=True),
        sa.Column("iso", sa.Integer(), nullable=True),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lon", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_objects.id"],
            name=op.f("fk_image_metadata_media_id_media_objects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("media_id", name=op.f("pk_image_metadata")),
    )
    op.create_table(
        "media_tags",
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_objects.id"],
            name=op.f("fk_media_tags_media_id_media_objects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name=op.f("fk_media_tags_tag_id_tags"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("media_id", "tag_id", name=op.f("pk_media_tags")),
    )
    op.create_table(
        "media_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=10), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("is_original", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_objects.id"],
            name=op.f("fk_media_variants_media_id_media_objects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_variants")),
        sa.UniqueConstraint("media_id", "label", name=op.f("uq_media_variants_media_id")),
    )
    op.create_table(
        "video_metadata",
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("video_codec", sa.String(length=30), nullable=True),
        sa.Column("audio_codec", sa.String(length=30), nullable=True),
        sa.Column("bitrate", sa.Integer(), nullable=True),
        sa.Column("container", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_objects.id"],
            name=op.f("fk_video_metadata_media_id_media_objects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("media_id", name=op.f("pk_video_metadata")),
    )
    # server_default 0: os usuários da sprint 1 começam sem nada usado na cota
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("storage_used_bytes", sa.BigInteger(), server_default="0", nullable=False)
        )
        batch_op.create_check_constraint(
            op.f("ck_users_storage_used_bytes_non_negative"), "storage_used_bytes >= 0"
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(op.f("ck_users_storage_used_bytes_non_negative"), type_="check")
        batch_op.drop_column("storage_used_bytes")

    op.drop_table("video_metadata")
    op.drop_table("media_variants")
    op.drop_table("media_tags")
    op.drop_table("image_metadata")
    op.drop_table("audio_metadata")
    op.drop_table("tags")
    op.drop_index("ix_media_objects_owner_status", table_name="media_objects")
    op.drop_index("ix_media_objects_owner_type_created", table_name="media_objects")
    op.drop_table("media_objects")
