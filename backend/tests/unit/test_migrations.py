from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.core.database import Base

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


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

    assert {"users", "revoked_tokens"} <= tables
    assert diff == []
