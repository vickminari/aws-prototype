import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("minutes", [0, -1])
def test_settings_rejects_non_positive_token_lifetime(minutes):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_expire_minutes=minutes)


def test_settings_without_env_uses_dev_defaults(monkeypatch):
    for name in ("ENVIRONMENT", "STORAGE_BACKEND", "AWS_REGION", "JWT_EXPIRE_MINUTES"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.environment == "dev"
    assert settings.storage_backend == "local"
    assert settings.aws_region == "us-east-2"
    assert settings.jwt_expire_minutes == 60


def test_settings_reads_values_from_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("S3_BUCKET", "proto1-avatars-teste")

    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"
    assert settings.s3_bucket == "proto1-avatars-teste"


def test_cors_origins_with_comma_separated_string_returns_list(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, http://127.0.0.1:5173")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_origins_with_empty_string_returns_empty_list(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == []


def test_prod_with_default_jwt_secret_raises_validation_error():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="prod", storage_backend="s3", s3_bucket="b")


def test_prod_with_short_jwt_secret_raises_validation_error():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="prod",
            jwt_secret="curto",
            storage_backend="s3",
            s3_bucket="b",
        )


def test_s3_backend_without_bucket_raises_validation_error():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, storage_backend="s3", s3_bucket=None)


def test_prod_with_strong_jwt_secret_is_valid():
    settings = Settings(
        _env_file=None,
        environment="prod",
        jwt_secret="x" * 32,
        storage_backend="s3",
        s3_bucket="proto1-avatars-teste",
    )

    assert settings.environment == "prod"
