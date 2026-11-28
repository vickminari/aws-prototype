from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.core.database import Base

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
# Última migração da sprint 1 (users e revoked_tokens)
SPRINT1_REVISION = "702cac72104f"


def test_alembic_upgrade_head_creates_schema_equal_to_models(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migrations.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        command.upgrade(Config(str(ALEMBIC_INI)), "head")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()

    assert {
        "users",
        "revoked_tokens",
        "media_objects",
        "image_metadata",
        "video_metadata",
        "audio_metadata",
        "media_variants",
        "tags",
        "media_tags",
    } <= tables
    assert diff == []


def test_alembic_downgrade_to_sprint1_and_upgrade_again(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migrations.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(ALEMBIC_INI))

    try:
        command.upgrade(config, "head")
        command.downgrade(config, SPRINT1_REVISION)
        engine = create_engine(database_url)
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables_after_downgrade = set(inspector.get_table_names())
            user_columns = {column["name"] for column in inspector.get_columns("users")}
        engine.dispose()
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()

    assert "media_objects" not in tables_after_downgrade
    assert "storage_used_bytes" not in user_columns
