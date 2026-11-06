from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def security_settings(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "segredo-exclusivo-dos-testes-000000000000")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "15")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_hash_password_uses_argon2id_and_random_salt():
    password = "Senha-de-teste-123!"
    first = hash_password(password)
    second = hash_password(password)

    assert first.startswith("$argon2id$")
    assert first != password
    assert first != second


@pytest.mark.parametrize("password, expected", [("Senha-123!", True), ("errada", False)])
def test_verify_password_checks_password(password, expected):
    hashed_password = hash_password("Senha-123!")

    assert verify_password(password, hashed_password) is expected


def test_create_access_token_contains_required_claims(security_settings):
    before = int(datetime.now(UTC).timestamp())
    token = create_access_token(42)
    after = int(datetime.now(UTC).timestamp())
    claims = jwt.decode(token, security_settings.jwt_secret, algorithms=["HS256"])

    assert claims["sub"] == "42"
    assert str(UUID(claims["jti"])) == claims["jti"]
    assert before <= claims["iat"] <= after
    assert claims["exp"] - claims["iat"] == security_settings.jwt_expire_minutes * 60
    assert decode_access_token(token) == claims


def test_create_access_token_assigns_unique_jti():
    first = decode_access_token(create_access_token(42))
    second = decode_access_token(create_access_token(42))

    assert first["jti"] != second["jti"]


def test_decode_access_token_rejects_expired_token(security_settings):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "42",
            "jti": "test-id",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        security_settings.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_decode_access_token_rejects_wrong_secret(monkeypatch):
    token = create_access_token(42)
    monkeypatch.setenv("JWT_SECRET", "outro-segredo-de-testes-000000000000000")
    get_settings.cache_clear()

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_decode_access_token_rejects_tampered_payload(security_settings):
    token = create_access_token(42)
    header, _, signature = token.split(".")
    forged_payload = jwt.encode(
        {"sub": "999", "jti": "forged", "iat": 0, "exp": 9999999999},
        security_settings.jwt_secret,
        algorithm="HS256",
    ).split(".")[1]

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header}.{forged_payload}.{signature}")


@pytest.mark.parametrize("token", ["", "nao-e-jwt", "a.b.c"])
def test_decode_access_token_rejects_malformed_token(token):
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("missing_claim", ["sub", "jti", "iat", "exp"])
def test_decode_access_token_rejects_missing_claim(missing_claim, security_settings):
    claims = decode_access_token(create_access_token(42))
    del claims[missing_claim]
    token = jwt.encode(claims, security_settings.jwt_secret, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("algorithm", ["HS384", "none"])
def test_decode_access_token_rejects_unexpected_algorithm(algorithm, security_settings):
    claims = decode_access_token(create_access_token(42))
    key = security_settings.jwt_secret if algorithm != "none" else ""
    token = jwt.encode(claims, key, algorithm=algorithm)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
