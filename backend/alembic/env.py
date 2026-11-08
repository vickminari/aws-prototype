"""Ambiente do Alembic: aplica as migrações no banco de DATABASE_URL.

Rodado por `alembic upgrade head` (no `entrypoint.sh` do container) e por
`alembic revision --autogenerate -m "..."` ao criar uma migração nova.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registra as tabelas em Base.metadata)
from app.core.config import get_settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    # Não desliga os loggers da aplicação quando roda dentro dos testes
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL das migrações sem conectar (`alembic upgrade head --sql`)."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Conecta no banco e aplica as migrações pendentes."""
    connectable = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # render_as_batch: permite ALTER TABLE também no SQLite (usado nos testes)
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
