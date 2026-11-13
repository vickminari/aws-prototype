import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def isolated_auth_environment(monkeypatch):
    for name in ("CSRF_SECRET", "CSRF_TRUSTED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def production_config():
    # Valores exclusivamente de teste, não usar em deploy.
    return {
        "environment": "prod",
        "jwt_secret": "jwt-exclusivo-dos-testes-0000000000000000",
        "csrf_secret": "csrf-exclusivo-dos-testes-00000000000000",
        "csrf_trusted_origins": ["https://app.example.com"],
    }


def test_auth_settings_reads_csrf_secret_and_comma_separated_origins(monkeypatch):
    monkeypatch.setenv("CSRF_SECRET", "csrf-exclusivo-dos-testes-00000000000000")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "http://localhost:5173, http://127.0.0.1:5173")

    settings = Settings(_env_file=None)

    assert settings.csrf_secret == "csrf-exclusivo-dos-testes-00000000000000"
    assert settings.csrf_trusted_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_auth_settings_reads_configurable_csrf_lifetime(monkeypatch):
    monkeypatch.setenv("CSRF_EXPIRE_MINUTES", "120")

    assert Settings(_env_file=None).csrf_expire_minutes == 120


@pytest.mark.parametrize("minutes", [0, -1])
def test_auth_settings_rejects_non_positive_csrf_lifetime(minutes):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, csrf_expire_minutes=minutes)


def test_auth_settings_accepts_explicit_secure_production_config(production_config):
    settings = Settings(_env_file=None, **production_config)

    assert settings.csrf_trusted_origins == ["https://app.example.com"]
    assert settings.csrf_secret != settings.jwt_secret


@pytest.mark.parametrize("secret", ["", "curto", "jwt-exclusivo-dos-testes-0000000000000000"])
def test_auth_settings_rejects_weak_or_reused_csrf_secret_in_production(production_config, secret):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(production_config | {"csrf_secret": secret}))


def test_auth_settings_rejects_default_csrf_secret_in_production(production_config):
    del production_config["csrf_secret"]

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **production_config)


@pytest.mark.parametrize(
    "origins",
    [[], ["http://app.example.com"], ["*"], ["https://*.example.com"]],
)
def test_auth_settings_requires_explicit_https_origins_in_production(production_config, origins):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(production_config | {"csrf_trusted_origins": origins}))


@pytest.mark.parametrize(
    "origin",
    [
        "https://app.example.com/path",
        "https://user:pass@app.example.com",
        "https://app.example.com?q=1",
    ],
)
def test_auth_settings_rejects_urls_that_are_not_origins(production_config, origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(production_config | {"csrf_trusted_origins": [origin]}))


def test_dev_without_trusted_origins_accepts_local_frontend(monkeypatch):
    """`docker compose up` sem backend/.env sobe em dev; cadastro e login devem funcionar."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    settings = Settings(_env_file=None)

    assert settings.environment == "dev"
    assert settings.csrf_trusted_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_dev_keeps_explicit_trusted_origins(monkeypatch):
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "http://localhost:3000")

    settings = Settings(_env_file=None, environment="dev")

    assert settings.csrf_trusted_origins == ["http://localhost:3000"]


@pytest.mark.parametrize("environment", ["test", "prod"])
def test_local_origins_are_never_implicit_outside_dev(environment, production_config):
    if environment == "test":
        assert Settings(_env_file=None, environment="test").csrf_trusted_origins == []
        return
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(production_config | {"csrf_trusted_origins": []}))
