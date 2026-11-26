from sqlalchemy import create_engine

from app.core.database import MIGRATION_LOCK_KEY, engine_options, migration_lock


class FakeConnection:
    """Conexão falsa do PostgreSQL que registra os comandos executados."""

    class dialect:  # noqa: N801  (imita o atributo `connection.dialect.name`)
        name = "postgresql"

    def __init__(self):
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params))

    def commit(self):
        self.statements.append(("COMMIT", None))


def test_engine_options_for_postgresql_set_pool_and_connect_timeout():
    options = engine_options(
        "postgresql+psycopg://app:app@db:5432/app", pool_size=3, max_overflow=2
    )

    assert options["pool_size"] == 3
    assert options["max_overflow"] == 2
    assert options["pool_pre_ping"] is True
    assert options["connect_args"] == {"connect_timeout": 5}


def test_engine_options_for_sqlite_skip_pool_settings():
    options = engine_options("sqlite+pysqlite:///:memory:", pool_size=3, max_overflow=2)

    assert "pool_size" not in options
    assert options["connect_args"] == {}


def test_migration_lock_on_postgresql_takes_and_releases_advisory_lock():
    connection = FakeConnection()

    with migration_lock(connection):
        connection.execute("-- migrações")

    sql = [statement for statement, _ in connection.statements]
    assert "pg_advisory_lock" in sql[0]
    assert sql[2] == "-- migrações"
    assert "pg_advisory_unlock" in sql[3]
    assert connection.statements[0][1] == {"key": MIGRATION_LOCK_KEY}


def test_migration_lock_releases_lock_even_on_error():
    connection = FakeConnection()

    try:
        with migration_lock(connection):
            raise RuntimeError("migração falhou")
    except RuntimeError:
        pass

    assert "pg_advisory_unlock" in connection.statements[-2][0]


def test_migration_lock_on_sqlite_does_nothing():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection, migration_lock(connection):
        assert not connection.in_transaction()
    engine.dispose()
