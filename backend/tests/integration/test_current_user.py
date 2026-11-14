from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.models import RevokedToken
from tests.integration.session_support import (
    ME_URL,
    SESSION_ORIGIN,
    cookie_name,
    login,
    put_cookie,
)

OTHER_SECRET = "outro-segredo-dos-testes-00000000000000"


def make_token(settings, *, secret=None, minutes=30, omit=(), **claims):
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    } | claims
    for claim in omit:
        payload.pop(claim)
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm="HS256")


def use_cookie(client, settings, value, *, name=None):
    put_cookie(client, name or cookie_name(settings), value)


def assert_unauthenticated(response, *, secret_value=None):
    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido ou expirado", "code": "INVALID_TOKEN"}
    if secret_value:
        assert secret_value not in response.text


def test_login_cookie_authenticates_protected_route(session_client, session_user):
    login(session_client, session_user)

    response = session_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["id"] == str(session_user.id)
    assert response.json()["username"] == session_user.username
    assert "hashed_password" not in response.json()


def test_valid_token_for_existing_user_authenticates(
    session_client, session_settings, session_user
):
    use_cookie(
        session_client, session_settings, make_token(session_settings, sub=str(session_user.id))
    )

    response = session_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["id"] == str(session_user.id)


def test_protected_route_without_cookie_returns_401(session_client):
    assert_unauthenticated(session_client.get(ME_URL))


@pytest.mark.parametrize("defect", ["malformed", "wrong_secret", "expired", "no_jti", "no_exp"])
def test_invalid_jwt_cookie_returns_401(session_client, session_settings, session_user, defect):
    claims = {"sub": str(session_user.id)}
    token = {
        "malformed": lambda: "nao-e-jwt",
        "wrong_secret": lambda: make_token(session_settings, secret=OTHER_SECRET, **claims),
        "expired": lambda: make_token(session_settings, minutes=-1, **claims),
        "no_jti": lambda: make_token(session_settings, omit=("jti",), **claims),
        "no_exp": lambda: make_token(session_settings, omit=("exp",), **claims),
    }[defect]()
    use_cookie(session_client, session_settings, token)

    assert_unauthenticated(session_client.get(ME_URL), secret_value=token)


@pytest.mark.parametrize("sub", ["nao-e-uuid", "123", "00000000-0000-0000-0000", " "])
def test_malformed_sub_returns_401_without_internal_error(session_client, session_settings, sub):
    use_cookie(session_client, session_settings, make_token(session_settings, sub=sub))

    assert_unauthenticated(session_client.get(ME_URL))


def test_token_for_unknown_user_returns_401(session_client, session_settings):
    use_cookie(session_client, session_settings, make_token(session_settings, sub=str(uuid4())))

    assert_unauthenticated(session_client.get(ME_URL))


def test_user_deactivated_after_login_is_rejected(session_client, session_user, db_session):
    login(session_client, session_user)
    assert session_client.get(ME_URL).status_code == 200

    session_user.is_active = False
    db_session.commit()

    assert_unauthenticated(session_client.get(ME_URL))


def test_revoked_jti_is_rejected_even_from_a_copied_cookie(
    session_client, session_settings, session_user, db_session
):
    login(session_client, session_user)
    assert session_client.get(ME_URL).status_code == 200
    token = session_client.cookies[cookie_name(session_settings)]
    claims = jwt.decode(token, session_settings.jwt_secret, algorithms=["HS256"])

    db_session.add(
        RevokedToken(
            jti=claims["jti"],
            user_id=session_user.id,
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
        )
    )
    db_session.commit()

    assert_unauthenticated(session_client.get(ME_URL))
    copy = TestClient(session_client.app, base_url=SESSION_ORIGIN)
    use_cookie(copy, session_settings, token)
    assert_unauthenticated(copy.get(ME_URL))


def test_revoking_one_session_keeps_other_sessions_valid(
    session_client, session_settings, session_user, db_session
):
    revoked = make_token(session_settings, sub=str(session_user.id))
    active = make_token(session_settings, sub=str(session_user.id))
    claims = jwt.decode(revoked, session_settings.jwt_secret, algorithms=["HS256"])
    db_session.add(
        RevokedToken(
            jti=claims["jti"],
            user_id=session_user.id,
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
        )
    )
    db_session.commit()

    use_cookie(session_client, session_settings, revoked)
    assert_unauthenticated(session_client.get(ME_URL))
    use_cookie(session_client, session_settings, active)
    assert session_client.get(ME_URL).status_code == 200


def test_bearer_header_alone_does_not_authenticate(session_client, session_settings, session_user):
    token = make_token(session_settings, sub=str(session_user.id))

    response = session_client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert_unauthenticated(response, secret_value=token)


def test_cookie_with_name_of_other_environment_is_ignored(
    session_client, session_settings, session_user
):
    other_name = "access_token" if session_settings.environment == "prod" else "__Host-access_token"
    token = make_token(session_settings, sub=str(session_user.id))
    use_cookie(session_client, session_settings, token, name=other_name)

    assert_unauthenticated(session_client.get(ME_URL))


@pytest.mark.parametrize("variant", ["hex", "upper", "braces", "urn"])
def test_non_canonical_uuid_sub_is_rejected(
    session_client, session_settings, session_user, variant
):
    canonical = str(session_user.id)
    sub = {
        "hex": session_user.id.hex,
        "upper": canonical.upper(),
        "braces": f"{{{canonical}}}",
        "urn": f"urn:uuid:{canonical}",
    }[variant]
    use_cookie(session_client, session_settings, make_token(session_settings, sub=sub))

    assert_unauthenticated(session_client.get(ME_URL))


def test_openapi_documents_cookie_auth_instead_of_bearer(session_client):
    document = session_client.get("/api/openapi.json").json()
    schemes = document["components"]["securitySchemes"]

    assert set(schemes) == {"CookieAuth"}
    assert schemes["CookieAuth"]["type"] == "apiKey"
    assert schemes["CookieAuth"]["in"] == "cookie"
    assert schemes["CookieAuth"]["name"] == "access_token"
    assert document["paths"][ME_URL]["get"]["security"] == [{"CookieAuth": []}]
