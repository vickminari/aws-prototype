from sqlalchemy.exc import OperationalError

from app.dependencies import get_db


class UnavailableSession:
    """Sessão falsa que simula o banco fora do ar em qualquer consulta."""

    def execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, ConnectionRefusedError("banco fora do ar"))


def test_health_returns_200_with_status_and_db_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_health_with_database_unavailable_returns_503(app, client):
    app.dependency_overrides[get_db] = lambda: UnavailableSession()

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Banco de dados indisponível",
        "code": "DATABASE_UNAVAILABLE",
    }
