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
        csrf_secret="y" * 32,
        csrf_trusted_origins=["https://app.example.com"],
        storage_backend="s3",
        s3_bucket="proto1-avatars-teste",
    )

    assert settings.environment == "prod"


def test_settings_sprint2_defaults_follow_architecture(monkeypatch):
    for name in ("USER_QUOTA_BYTES", "MAX_UPLOAD_BYTES", "QUEUE_BACKEND", "RUN_MIGRATIONS"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.user_quota_bytes == 104_857_600
    assert settings.max_upload_bytes == 104_857_600
    assert settings.upload_url_expire_seconds == 900
    assert settings.pending_upload_ttl_minutes == 60
    assert settings.queue_backend == "memory"
    assert settings.sqs_queue_url is None
    assert settings.aws_endpoint_url is None
    assert settings.run_migrations is True
    assert (settings.db_pool_size, settings.db_max_overflow) == (3, 2)
    assert settings.video_max_duration_seconds == 600


def test_settings_reads_sprint2_values_from_env(monkeypatch):
    monkeypatch.setenv("RUN_MIGRATIONS", "0")
    monkeypatch.setenv("USER_QUOTA_BYTES", "1048576")
    monkeypatch.setenv("QUEUE_BACKEND", "sqs")
    monkeypatch.setenv("SQS_QUEUE_URL", "http://elasticmq:9324/000000000000/proto2-media-jobs")

    settings = Settings(_env_file=None)

    assert settings.run_migrations is False
    assert settings.user_quota_bytes == 1_048_576
    assert settings.queue_backend == "sqs"


def test_settings_sqs_queue_without_url_raises():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, queue_backend="sqs")


@pytest.mark.parametrize(
    "field",
    [
        "user_quota_bytes",
        "max_upload_bytes",
        "upload_url_expire_seconds",
        "pending_upload_ttl_minutes",
        "db_pool_size",
        "video_max_duration_seconds",
    ],
)
def test_settings_rejects_non_positive_sprint2_limits(field):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: 0})
