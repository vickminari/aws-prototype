from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import verify_password
from app.models import RevokedToken, User
from tests.conftest import DEFAULT_PASSWORD


def test_create_user_persists_and_reads_with_defaults(db_session):
    user = User(
        full_name="Maria Silva",
        username="maria",
        email="maria@example.com",
        hashed_password="hash",
    )
    db_session.add(user)
    db_session.commit()
    db_session.expunge_all()

    saved = db_session.scalars(select(User).where(User.username == "maria")).one()

    assert isinstance(saved.id, UUID)
    assert saved.full_name == "Maria Silva"
    assert saved.email == "maria@example.com"
    assert saved.is_active is True
    assert saved.description is None
    assert saved.profile_image_key is None
    assert isinstance(saved.created_at, datetime)
    assert isinstance(saved.updated_at, datetime)


def test_update_user_refreshes_updated_at_and_keeps_created_at(db_session, user_factory):
    # Data antiga fixa: no Windows o relógio pode não avançar entre o INSERT e o UPDATE
    old_updated_at = datetime(2000, 1, 1, tzinfo=UTC)
    user = user_factory(updated_at=old_updated_at)
    created_at = user.created_at

    user.full_name = "Nome Alterado"
    db_session.commit()
    db_session.refresh(user)

    assert user.created_at == created_at
    assert user.updated_at > old_updated_at


@pytest.mark.parametrize("field", ["email", "username"])
def test_create_user_with_duplicate_field_raises_integrity_error(field, db_session, user_factory):
    existing = user_factory()

    with pytest.raises(IntegrityError):
        user_factory(**{field: getattr(existing, field)})


def test_user_factory_creates_unique_users_with_hashed_password(user_factory):
    first, second = user_factory(), user_factory()

    assert first.username != second.username
    assert first.email != second.email
    assert first.hashed_password != DEFAULT_PASSWORD
    assert verify_password(DEFAULT_PASSWORD, first.hashed_password)


def test_create_revoked_token_persists_with_revoked_at(db_session, user_factory):
    user = user_factory()
    jti = str(uuid4())
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.add(RevokedToken(jti=jti, user_id=user.id, expires_at=expires_at))
    db_session.commit()
    db_session.expunge_all()

    saved = db_session.get(RevokedToken, jti)

    assert saved.user_id == user.id
    assert isinstance(saved.revoked_at, datetime)
    assert isinstance(saved.expires_at, datetime)


def test_create_revoked_token_with_unknown_user_raises_integrity_error(db_session):
    db_session.add(RevokedToken(jti=str(uuid4()), user_id=uuid4(), expires_at=datetime.now(UTC)))

    with pytest.raises(IntegrityError):
        db_session.commit()
