from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_db
from app.main import create_app


def test_docs_returns_200_under_api_prefix():
    client = TestClient(create_app())

    assert client.get("/api/docs").status_code == 200
    openapi = client.get("/api/openapi.json")
    assert openapi.status_code == 200
    assert "/api/health" in openapi.json()["paths"]


def cors_client(db_session):
    """App com CORS configurado; usa o SQLite do teste porque /api/health consulta o banco."""
    app = create_app(Settings(_env_file=None, cors_origins="http://localhost:5173"))
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_cors_with_configured_origin_returns_allow_origin_header(db_session):
    client = cors_client(db_session)

    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_with_unknown_origin_returns_no_allow_origin_header(db_session):
    client = cors_client(db_session)

    response = client.get("/api/health", headers={"Origin": "http://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers
