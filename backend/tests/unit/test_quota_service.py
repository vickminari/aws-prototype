from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import QuotaExceededError
from app.models import User
from app.services import quota_service

MB = 1024 * 1024
QUOTA = 100 * MB


def stored_usage(db_session, user) -> int:
    """Valor gravado no banco, sem passar pelo mapa de identidade da sessão."""
    return db_session.scalar(select(User.storage_used_bytes).where(User.id == user.id))


def test_reserve_up_to_exact_quota_is_accepted(db_session, user_factory):
    user = user_factory()

    quota_service.reserve(db_session, user.id, QUOTA, quota_bytes=QUOTA)
    db_session.commit()

    assert stored_usage(db_session, user) == QUOTA


def test_reserve_one_byte_above_quota_raises_and_keeps_usage(db_session, user_factory):
    user = user_factory(storage_used_bytes=QUOTA)

    with pytest.raises(QuotaExceededError):
        quota_service.reserve(db_session, user.id, 1, quota_bytes=QUOTA)

    assert stored_usage(db_session, user) == QUOTA


def test_reserve_with_99mb_used_and_2mb_file_raises_with_free_space_message(
    db_session, user_factory
):
    """Exemplo do RNF-10 (ARQ §5.12)."""
    user = user_factory(storage_used_bytes=99 * MB)

    with pytest.raises(QuotaExceededError) as error:
        quota_service.reserve(db_session, user.id, 2 * MB, quota_bytes=QUOTA)

    assert error.value.message == "Cota de 100 MB excedida: você tem 1 MB livre"


def test_reserve_accumulates_successive_reservations(db_session, user_factory):
    user = user_factory()

    quota_service.reserve(db_session, user.id, 30 * MB, quota_bytes=QUOTA)
    quota_service.reserve(db_session, user.id, 20 * MB, quota_bytes=QUOTA)
    db_session.commit()

    assert stored_usage(db_session, user) == 50 * MB


def test_reserve_updates_user_loaded_in_session(db_session, user_factory):
    user = user_factory()

    quota_service.reserve(db_session, user.id, 10 * MB, quota_bytes=QUOTA)

    assert user.storage_used_bytes == 10 * MB


@pytest.mark.parametrize("size", [0, -1])
def test_reserve_non_positive_size_raises_value_error(size, db_session, user_factory):
    user = user_factory()

    with pytest.raises(ValueError):
        quota_service.reserve(db_session, user.id, size, quota_bytes=QUOTA)


def test_reserve_for_unknown_user_raises_quota_exceeded(db_session):
    with pytest.raises(QuotaExceededError):
        quota_service.reserve(db_session, uuid4(), 1, quota_bytes=QUOTA)


def test_release_returns_bytes_to_quota(db_session, user_factory):
    user = user_factory(storage_used_bytes=50 * MB)

    quota_service.release(db_session, user.id, 20 * MB)
    db_session.commit()

    assert stored_usage(db_session, user) == 30 * MB


def test_release_more_than_used_never_goes_negative(db_session, user_factory):
    user = user_factory(storage_used_bytes=5 * MB)

    quota_service.release(db_session, user.id, 20 * MB)
    db_session.commit()

    assert stored_usage(db_session, user) == 0


def test_release_non_positive_size_does_nothing(db_session, user_factory):
    user = user_factory(storage_used_bytes=5 * MB)

    quota_service.release(db_session, user.id, 0)
    db_session.commit()

    assert stored_usage(db_session, user) == 5 * MB


def test_usage_returns_used_and_quota(db_session, user_factory):
    user = user_factory(storage_used_bytes=7 * MB)

    usage = quota_service.usage(db_session, user.id, quota_bytes=QUOTA)

    assert (usage.used_bytes, usage.quota_bytes) == (7 * MB, QUOTA)


def test_format_megabytes_uses_comma_and_drops_trailing_zero():
    assert quota_service.format_megabytes(100 * MB) == "100"
    assert quota_service.format_megabytes(int(1.5 * MB)) == "1,5"
    assert quota_service.format_megabytes(0) == "0"
