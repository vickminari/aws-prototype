"""Conexão com o banco: engine, fábrica de sessões e base declarativa dos modelos (ARQ §5.4)."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Dialect, MetaData, TypeDecorator, create_engine, make_url
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


def _connect_args(database_url: str) -> dict[str, int]:
    """Limita a espera por conexão no PostgreSQL: com o RDS inacessível (SG, rede),
    o health check responde 503 em segundos em vez de travar a requisição."""
    if make_url(database_url).get_backend_name() == "postgresql":
        return {"connect_timeout": CONNECT_TIMEOUT_SECONDS}
    return {}


CONNECT_TIMEOUT_SECONDS = 5

# A conexão só é aberta no primeiro uso; pool_pre_ping descarta conexões que o RDS encerrou.
_database_url = get_settings().database_url
engine = create_engine(_database_url, pool_pre_ping=True, connect_args=_connect_args(_database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
