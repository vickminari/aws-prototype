import pytest
from sqlalchemy import func, select

from app.core.exceptions import InvalidCredentialsError
from app.core.security import verify_password
from app.models import User
from app.services import auth_service

PASSWORD = "Senha-de-teste-123"


@pytest.fixture
def login_user(user_factory):
    return user_factory(username="maria.silva", email="maria@example.com", password=PASSWORD)


@pytest.mark.parametrize(
    "identifier",
    ["maria.silva", "MARIA.SILVA", "Maria.Silva", "maria@example.com", "MARIA@EXAMPLE.COM"],
)
def test_authenticate_with_username_or_email_returns_existing_user(
    db_session, login_user, identifier
):
    user = auth_service.authenticate(db_session, identifier, PASSWORD)

    assert isinstance(user, User)
    assert user.id == login_user.id
    assert user.username == "maria.silva"
    assert user.email == "maria@example.com"


@pytest.mark.parametrize(
    "identifier, password, active",
    [
        ("maria.silva", "Senha-incorreta-123", True),
        ("maria@example.com", "Senha-incorreta-123", True),
        ("nao.existe", PASSWORD, True),
        ("nao.existe@example.com", PASSWORD, True),
        ("maria.silva", PASSWORD, False),
        ("maria@example.com", PASSWORD, False),
        ("maria.silva", "Senha-incorreta-123", False),
    ],
)
def test_authenticate_with_invalid_credentials_or_inactive_user_raises_same_error(
    db_session, login_user, identifier, password, active
):
    login_user.is_active = active
    db_session.commit()

    with pytest.raises(InvalidCredentialsError) as error:
        auth_service.authenticate(db_session, identifier, password)

    assert error.value.code == "INVALID_CREDENTIALS"
    assert error.value.message == "Usuário ou senha inválidos"
    assert password not in str(error.value)
    assert identifier not in str(error.value)


def test_authenticate_does_not_change_or_create_users(db_session, login_user):
    original = (
        login_user.hashed_password,
        login_user.created_at,
        login_user.updated_at,
        login_user.is_active,
    )

    auth_service.authenticate(db_session, login_user.username, PASSWORD)
    db_session.refresh(login_user)

    assert (
        login_user.hashed_password,
        login_user.created_at,
        login_user.updated_at,
        login_user.is_active,
    ) == original
    assert db_session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize("wrong_password", [PASSWORD.lower(), f" {PASSWORD}", f"{PASSWORD} "])
def test_authenticate_does_not_normalize_password(db_session, login_user, wrong_password):
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(db_session, login_user.username, wrong_password)


def test_authenticate_preserves_spaces_in_valid_password(db_session, user_factory):
    password = f" {PASSWORD} "
    existing = user_factory(password=password)

    user = auth_service.authenticate(db_session, existing.username, password)

    assert user.id == existing.id


def test_authenticate_with_unknown_user_still_verifies_a_hash(db_session, monkeypatch):
    # Confere a mitigação sem depender de medições de tempo instáveis.
    verifications = []

    def tracked_verify(password, hashed_password):
        verifications.append((password, hashed_password))
        return verify_password(password, hashed_password)

    monkeypatch.setattr(auth_service, "verify_password", tracked_verify, raising=False)

    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(db_session, "nao.existe", PASSWORD)

    assert len(verifications) == 1
    assert verifications[0][0] == PASSWORD
    assert verifications[0][1] != PASSWORD
    assert db_session.scalar(select(func.count()).select_from(User)) == 0
