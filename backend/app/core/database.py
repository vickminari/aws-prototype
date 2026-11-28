"""Conexão com o banco: engine, fábrica de sessões e base declarativa dos modelos (ARQ §5.4)."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Connection,
    DateTime,
    Dialect,
    MetaData,
    TypeDecorator,
    create_engine,
    make_url,
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

# Nomes previsíveis para constraints e índices: o Alembic consegue alterá-los/removê-los
# depois sem depender dos nomes gerados por cada banco.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Momento atual em UTC (ARQ §5.9: datas sempre em UTC no banco). Default das colunas."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """`DateTime(timezone=True)` que sempre devolve datas com fuso UTC.

    O PostgreSQL guarda o fuso, mas o SQLite dos testes devolve datas "ingênuas" (sem fuso),
    e comparar as duas (ex.: `expires_at < datetime.now(UTC)`) lança `TypeError`.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    """Classe-mãe de todos os modelos SQLAlchemy."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


CONNECT_TIMEOUT_SECONDS = 5
# Chave fixa do pg_advisory_lock das migrações; qualquer inteiro de 64 bits serve,
# desde que todas as instâncias usem o mesmo (ADR-027)
MIGRATION_LOCK_KEY = 2026_11_26_64


def engine_options(database_url: str, *, pool_size: int, max_overflow: int) -> dict[str, Any]:
    """Opções do `create_engine` para a URL informada.

    No PostgreSQL:
    - `connect_timeout` limita a espera por conexão: com o RDS inacessível (SG, rede),
      o health check responde 503 em segundos em vez de travar a requisição;
    - o pool fica pequeno (`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`, padrão 3 + 2): com várias
      instâncias no ASG, a soma precisa caber nas ~80 conexões do `db.t4g.micro`.

    O SQLite dos testes usa o pool padrão.
    """
    options: dict[str, Any] = {"pool_pre_ping": True, "connect_args": {}}
    if make_url(database_url).get_backend_name() == "postgresql":
        options["connect_args"] = {"connect_timeout": CONNECT_TIMEOUT_SECONDS}
        options["pool_size"] = pool_size
        options["max_overflow"] = max_overflow
    return options


@contextmanager
def migration_lock(connection: Connection) -> Iterator[None]:
    """Garante que só uma instância aplique migrações por vez (ADR-027).

    No PostgreSQL pega um `pg_advisory_lock` de sessão: se duas instâncias do ASG sobem
    juntas, a segunda espera a primeira terminar e depois não encontra nada pendente.
    O lock é liberado mesmo se a migração falhar. No SQLite (testes) não faz nada.
    """
    if connection.dialect.name != "postgresql":
        yield
        return
    connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY})
    # Encerra a transação aberta pelo SELECT; o lock de sessão continua valendo
    connection.commit()
    try:
        yield
    finally:
        connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY})
        connection.commit()


# A conexão só é aberta no primeiro uso; pool_pre_ping descarta conexões que o RDS encerrou.
_settings = get_settings()
engine = create_engine(
    _settings.database_url,
    **engine_options(
        _settings.database_url,
        pool_size=_settings.db_pool_size,
        max_overflow=_settings.db_max_overflow,
    ),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
