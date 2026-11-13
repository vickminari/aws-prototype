from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_db
from app.main import create_app
from app.models import RevokedToken

ORIGIN = "https://app.example.com"
PASSWORD = "Senha-de-teste-123"
ME_URL = "/api/users/me"
OTHER_SECRET = "outro-segredo-dos-testes-00000000000000"


@pytest.fixture(params=["test", "prod"])
def auth_settings(request):
    return Settings(
        _env_file=None,
        environment=request.param,
        jwt_secret="jwt-exclusivo-dos-testes-0000000000000000",
        jwt_expire_minutes=30,
        csrf_secret="csrf-exclusivo-dos-testes-00000000000000",
        csrf_trusted_origins=[ORIGIN],
    )


@pytest.fixture
def auth_client(db_session, auth_settings):
    app = create_app(auth_settings)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app, base_url=ORIGIN) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def current_user(user_factory):
    return user_factory(username="maria.silva", email="maria@example.com", password=PASSWORD)


def cookie_name(settings):
    return ("__Host-" if settings.environment == "prod" else "") + "access_token"


def login(client, user):
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/auth/login",
        data={"username": user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
    )
    assert response.status_code == 200


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
    client.cookies.set(name or cookie_name(settings), value, domain="app.example.com", path="/")


def assert_unauthenticated(response, *, secret_value=None):
    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido ou expirado", "code": "INVALID_TOKEN"}
    if secret_value:
        assert secret_value not in response.text


def test_login_cookie_authenticates_protected_route(auth_client, current_user):
    login(auth_client, current_user)

    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["id"] == str(current_user.id)
    assert response.json()["username"] == current_user.username
    assert "hashed_password" not in response.json()


def test_valid_token_for_existing_user_authenticates(auth_client, auth_settings, current_user):
    use_cookie(auth_client, auth_settings, make_token(auth_settings, sub=str(current_user.id)))

    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["id"] == str(current_user.id)


def test_protected_route_without_cookie_returns_401(auth_client):
    assert_unauthenticated(auth_client.get(ME_URL))


@pytest.mark.parametrize("defect", ["malformed", "wrong_secret", "expired", "no_jti", "no_exp"])
def test_invalid_jwt_cookie_returns_401(auth_client, auth_settings, current_user, defect):
    claims = {"sub": str(current_user.id)}
    token = {
        "malformed": lambda: "nao-e-jwt",
        "wrong_secret": lambda: make_token(auth_settings, secret=OTHER_SECRET, **claims),
        "expired": lambda: make_token(auth_settings, minutes=-1, **claims),
        "no_jti": lambda: make_token(auth_settings, omit=("jti",), **claims),
        "no_exp": lambda: make_token(auth_settings, omit=("exp",), **claims),
    }[defect]()
    use_cookie(auth_client, auth_settings, token)

    assert_unauthenticated(auth_client.get(ME_URL), secret_value=token)


@pytest.mark.parametrize("sub", ["nao-e-uuid", "123", "00000000-0000-0000-0000", " "])
def test_malformed_sub_returns_401_without_internal_error(auth_client, auth_settings, sub):
    use_cookie(auth_client, auth_settings, make_token(auth_settings, sub=sub))

    assert_unauthenticated(auth_client.get(ME_URL))


def test_token_for_unknown_user_returns_401(auth_client, auth_settings):
    use_cookie(auth_client, auth_settings, make_token(auth_settings, sub=str(uuid4())))

    assert_unauthenticated(auth_client.get(ME_URL))


def test_user_deactivated_after_login_is_rejected(auth_client, current_user, db_session):
    login(auth_client, current_user)
    assert auth_client.get(ME_URL).status_code == 200

    current_user.is_active = False
    db_session.commit()

    assert_unauthenticated(auth_client.get(ME_URL))


def test_revoked_jti_is_rejected_even_from_a_copied_cookie(
    auth_client, auth_settings, current_user, db_session
):
    login(auth_client, current_user)
    assert auth_client.get(ME_URL).status_code == 200
    token = auth_client.cookies[cookie_name(auth_settings)]
    claims = jwt.decode(token, auth_settings.jwt_secret, algorithms=["HS256"])

    db_session.add(
        RevokedToken(
            jti=claims["jti"],
            user_id=current_user.id,
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
        )
    )
    db_session.commit()

    assert_unauthenticated(auth_client.get(ME_URL))
    copy = TestClient(auth_client.app, base_url=ORIGIN)
    use_cookie(copy, auth_settings, token)
    assert_unauthenticated(copy.get(ME_URL))


def test_revoking_one_session_keeps_other_sessions_valid(
    auth_client, auth_settings, current_user, db_session
):
    revoked = make_token(auth_settings, sub=str(current_user.id))
    active = make_token(auth_settings, sub=str(current_user.id))
    claims = jwt.decode(revoked, auth_settings.jwt_secret, algorithms=["HS256"])
    db_session.add(
        RevokedToken(
            jti=claims["jti"],
            user_id=current_user.id,
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
        )
    )
    db_session.commit()

    use_cookie(auth_client, auth_settings, revoked)
    assert_unauthenticated(auth_client.get(ME_URL))
    use_cookie(auth_client, auth_settings, active)
    assert auth_client.get(ME_URL).status_code == 200


def test_bearer_header_alone_does_not_authenticate(auth_client, auth_settings, current_user):
    token = make_token(auth_settings, sub=str(current_user.id))

    response = auth_client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert_unauthenticated(response, secret_value=token)


def test_cookie_with_name_of_other_environment_is_ignored(auth_client, auth_settings, current_user):
    other_name = "access_token" if auth_settings.environment == "prod" else "__Host-access_token"
    token = make_token(auth_settings, sub=str(current_user.id))
    use_cookie(auth_client, auth_settings, token, name=other_name)

    assert_unauthenticated(auth_client.get(ME_URL))
