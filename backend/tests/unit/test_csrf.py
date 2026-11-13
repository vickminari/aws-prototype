import time

import pytest

from app.core.csrf import create_csrf_token, verify_csrf_token

SECRET = "csrf-exclusivo-dos-testes-00000000000000"
SESSION = "identificador-aleatorio-de-pre-sessao"


def test_csrf_token_is_random_and_bound_to_session():
    first = create_csrf_token(SESSION, SECRET)
    second = create_csrf_token(SESSION, SECRET)

    assert first != second
    assert SESSION not in first
    assert verify_csrf_token(first, SESSION, SECRET) is True
    assert verify_csrf_token(second, SESSION, SECRET) is True


@pytest.mark.parametrize(
    "session, secret",
    [("outra-sessao", SECRET), (SESSION, "outro-segredo-dos-testes-00000000000000")],
)
def test_csrf_token_rejects_another_session_or_secret(session, secret):
    token = create_csrf_token(SESSION, SECRET)

    assert verify_csrf_token(token, session, secret) is False


def test_csrf_token_rejects_tampering():
    token = create_csrf_token(SESSION, SECRET)
    replacement = "a" if token[0] != "a" else "b"

    assert verify_csrf_token(replacement + token[1:], SESSION, SECRET) is False


@pytest.mark.parametrize("token", ["", "invalido", "a.b.c", "☃", "a" * 10000])
def test_csrf_token_rejects_malformed_values_without_raising(token):
    assert verify_csrf_token(token, SESSION, SECRET) is False


def test_csrf_token_expires_at_deadline_without_sleep(monkeypatch):
    now = 1800000000
    monkeypatch.setattr(time, "time", lambda: now)
    token = create_csrf_token(SESSION, SECRET, expires_in=60)
    monkeypatch.setattr(time, "time", lambda: now + 59)
    assert verify_csrf_token(token, SESSION, SECRET) is True
    monkeypatch.setattr(time, "time", lambda: now + 60)
    assert verify_csrf_token(token, SESSION, SECRET) is False


def test_csrf_token_does_not_cross_session_rotation():
    old_token = create_csrf_token("pre-sessao", SECRET)
    new_token = create_csrf_token("jti-da-sessao-autenticada", SECRET)

    assert verify_csrf_token(old_token, "jti-da-sessao-autenticada", SECRET) is False
    assert verify_csrf_token(new_token, "pre-sessao", SECRET) is False
