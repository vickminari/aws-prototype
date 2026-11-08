from datetime import UTC
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyExistsError, UsernameAlreadyExistsError
from app.core.security import verify_password
from app.models import User
from app.schemas.user import UserCreate
from app.services import auth_service


@pytest.fixture
def registration_data():
    return {
        "full_name": "Maria Silva",
        "username": "Maria.Silva",
        "email": "Maria.Silva@EXAMPLE.COM",
        "password": "Senha123",
    }


@pytest.mark.parametrize("description", [None, "", "Descrição do perfil"])
def test_register_persists_normalized_user_with_hashed_password(
    db_session, engine, registration_data, description
):
    payload = UserCreate(**registration_data, description=description)
    original_payload = payload.model_dump()

    user = auth_service.register(db_session, payload)

    assert isinstance(user, User)
    assert isinstance(user.id, UUID)
    # Outra Session confirma que o service efetivamente persistiu os dados.
    with Session(engine) as verification_session:
        saved = verification_session.get(User, user.id)
        assert saved is not None
        assert saved.full_name == "Maria Silva"
        assert saved.username == "maria.silva"
        assert saved.email == "maria.silva@example.com"
        assert saved.description == description
        assert saved.is_active is True
        assert saved.profile_image_key is None
        assert saved.created_at.utcoffset() == UTC.utcoffset(None)
        assert saved.updated_at.utcoffset() == UTC.utcoffset(None)
        assert saved.hashed_password != payload.password
        assert verify_password(payload.password, saved.hashed_password)

    assert payload.model_dump() == original_payload


@pytest.mark.parametrize("email", ["maria@example.com", "MARIA@example.com", "Maria@EXAMPLE.COM"])
def test_register_with_existing_email_raises_domain_error_without_creating_user(
    db_session, user_factory, registration_data, email
):
    existing = user_factory(username="outra.pessoa", email="maria@example.com")
    original_hash = existing.hashed_password
    payload = UserCreate(**(registration_data | {"email": email}))

    with pytest.raises(EmailAlreadyExistsError) as error:
        auth_service.register(db_session, payload)

    assert error.value.code == "EMAIL_ALREADY_EXISTS"
    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    db_session.refresh(existing)
    assert existing.hashed_password == original_hash
    assert existing.username == "outra.pessoa"


@pytest.mark.parametrize("username", ["maria.silva", "MARIA.SILVA", "Maria.Silva"])
def test_register_with_existing_username_raises_domain_error_without_creating_user(
    db_session, user_factory, registration_data, username
):
    existing = user_factory(username="maria.silva", email="outra@example.com")
    original_hash = existing.hashed_password
    payload = UserCreate(**(registration_data | {"username": username}))

    with pytest.raises(UsernameAlreadyExistsError) as error:
        auth_service.register(db_session, payload)

    assert error.value.code == "USERNAME_ALREADY_EXISTS"
    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    db_session.refresh(existing)
    assert existing.hashed_password == original_hash
    assert existing.email == "outra@example.com"


@pytest.mark.parametrize(
    "field, value, expected_error",
    [
        ("email", "maria@example.com", EmailAlreadyExistsError),
        ("username", "maria.silva", UsernameAlreadyExistsError),
    ],
)
def test_register_does_not_reuse_identity_of_inactive_user(
    db_session, user_factory, registration_data, field, value, expected_error
):
    user_factory(username="maria.silva", email="maria@example.com", is_active=False)
    data = registration_data | {"username": "novo.usuario", "email": "novo@example.com"}
    payload = UserCreate(**(data | {field: value}))

    with pytest.raises(expected_error):
        auth_service.register(db_session, payload)

    assert db_session.scalar(select(func.count()).select_from(User)) == 1


def test_register_after_rejected_duplicate_can_create_another_user(
    db_session, user_factory, registration_data
):
    user_factory(email="maria.silva@example.com")

    with pytest.raises(EmailAlreadyExistsError):
        auth_service.register(db_session, UserCreate(**registration_data))

    payload = UserCreate(**(registration_data | {"email": "novo@example.com"}))
    user = auth_service.register(db_session, payload)

    assert user.email == "novo@example.com"
    assert db_session.scalar(select(func.count()).select_from(User)) == 2


def test_register_preserves_unrelated_integrity_error_and_rolls_back(
    db_session, registration_data, monkeypatch
):
    failure = IntegrityError("INSERT", {}, RuntimeError("outra restrição"))

    def fail_commit():
        raise failure

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(IntegrityError) as error:
        auth_service.register(db_session, UserCreate(**registration_data))

    assert error.value is failure
    assert not db_session.new
    assert db_session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize(
    "field, expected_error",
    [("email", EmailAlreadyExistsError), ("username", UsernameAlreadyExistsError)],
)
def test_register_translates_database_duplicate_and_recovers_session(
    db_session, user_factory, registration_data, monkeypatch, field, expected_error
):
    payload = UserCreate(**registration_data)
    user_factory(**{field: getattr(payload, field).lower()})
    original_scalar = db_session.scalar
    checks = 0

    def miss_initial_checks(*args, **kwargs):
        nonlocal checks
        checks += 1
        # Simula consultas que não viram um cadastro concorrente: o índice
        # único real do SQLite rejeitará o INSERT, exigindo rollback.
        if checks <= 2:
            return None
        return original_scalar(*args, **kwargs)

    monkeypatch.setattr(db_session, "scalar", miss_initial_checks)

    with pytest.raises(expected_error):
        auth_service.register(db_session, payload)

    assert original_scalar(select(func.count()).select_from(User)) == 1
    user = auth_service.register(
        db_session,
        UserCreate(
            **(registration_data | {"username": "novo.usuario", "email": "novo@example.com"})
        ),
    )
    assert user.email == "novo@example.com"
