from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidTokenError
from app.models import RevokedToken, User
from app.services import auth_service


@pytest.fixture
def user(user_factory):
    return user_factory()


@pytest.fixture
def expires_at():
    return (datetime.now(UTC) + timedelta(minutes=30)).replace(microsecond=0)


def revoked_count(db_session):
    return db_session.scalar(select(func.count()).select_from(RevokedToken))


def test_logout_persists_revocation_until_original_expiration(db_session, user, expires_at):
    jti = str(uuid4())

    auth_service.logout(db_session, str(user.id), jti, expires_at)

    db_session.expunge_all()
    saved = db_session.get(RevokedToken, jti)
    assert saved is not None
    assert saved.user_id == user.id
    assert saved.expires_at == expires_at
    assert saved.revoked_at <= datetime.now(UTC)


def test_logout_twice_keeps_a_single_revocation(db_session, user, expires_at):
    jti = str(uuid4())

    auth_service.logout(db_session, str(user.id), jti, expires_at)
    auth_service.logout(db_session, str(user.id), jti, expires_at)

    assert revoked_count(db_session) == 1


def test_logout_after_revocation_by_another_session_does_not_fail(
    db_session, engine, user, expires_at
):
    jti = str(uuid4())
    with Session(engine) as other:
        other.add(RevokedToken(jti=jti, user_id=user.id, expires_at=expires_at))
        other.commit()

    auth_service.logout(db_session, str(user.id), jti, expires_at)

    assert revoked_count(db_session) == 1


def test_logout_tolerates_concurrent_insert_between_check_and_commit(
    db_session, engine, user, expires_at, monkeypatch
):
    """Outro logout grava o mesmo jti depois da checagem: o conflito não vira 500."""
    jti = str(uuid4())
    original_get = db_session.get
    calls = []

    def get_racing(entity, ident, *args, **kwargs):
        if entity is RevokedToken and not calls:
            calls.append(ident)
            with Session(engine) as other:
                other.add(RevokedToken(jti=jti, user_id=user.id, expires_at=expires_at))
                other.commit()
            return None
        return original_get(entity, ident, *args, **kwargs)

    monkeypatch.setattr(db_session, "get", get_racing)

    auth_service.logout(db_session, str(user.id), jti, expires_at)

    assert calls == [jti]
    assert revoked_count(db_session) == 1


def test_logout_keeps_other_sessions_of_the_same_user(db_session, user, expires_at):
    revoked, active = str(uuid4()), str(uuid4())

    auth_service.logout(db_session, str(user.id), revoked, expires_at)

    assert auth_service.get_session_user(db_session, str(user.id), active).id == user.id
    with pytest.raises(InvalidTokenError):
        auth_service.get_session_user(db_session, str(user.id), revoked)


@pytest.mark.parametrize("subject", ["nao-e-uuid", ""])
def test_logout_with_malformed_subject_raises_invalid_token(db_session, expires_at, subject):
    with pytest.raises(InvalidTokenError):
        auth_service.logout(db_session, subject, str(uuid4()), expires_at)

    assert revoked_count(db_session) == 0


def test_logout_for_unknown_user_does_not_fail_or_revoke(db_session, expires_at):
    auth_service.logout(db_session, str(uuid4()), str(uuid4()), expires_at)

    assert revoked_count(db_session) == 0


def test_logout_tolerates_user_removed_by_another_session(db_session, engine, user, expires_at):
    """O usuário ainda está no identity map, mas foi apagado: a FK falha sem virar 500."""
    with Session(engine) as other:
        other.execute(delete(User).where(User.id == user.id))
        other.commit()

    auth_service.logout(db_session, str(user.id), str(uuid4()), expires_at)

    assert revoked_count(db_session) == 0
