from http.cookies import SimpleCookie

import pytest
from fastapi import Response

from app.controllers.auth_cookies import clear_auth_cookie, set_auth_cookie
from app.core.config import Settings


def cookie_settings(environment, minutes=15):
    return Settings(
        _env_file=None,
        environment=environment,
        jwt_expire_minutes=minutes,
        jwt_secret="jwt-exclusivo-dos-testes-0000000000000000",
        csrf_secret="csrf-exclusivo-dos-testes-00000000000000",
        csrf_trusted_origins=["https://app.example.com"],
    )


@pytest.mark.parametrize(
    "environment, expected_name, expected_secure",
    [
        ("dev", "access_token", False),
        ("test", "access_token", False),
        ("prod", "__Host-access_token", True),
    ],
)
@pytest.mark.parametrize("minutes", [15, 60])
def test_set_auth_cookie_uses_environment_security_and_configured_lifetime(
    environment, expected_name, expected_secure, minutes
):
    response = Response()

    set_auth_cookie(response, "jwt-ficticio-de-teste", cookie_settings(environment, minutes))

    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])
    assert set(cookies) == {expected_name}
    cookie = cookies[expected_name]
    assert cookie.value == "jwt-ficticio-de-teste"
    assert cookie["httponly"] is True
    assert bool(cookie["secure"]) is expected_secure
    assert cookie["samesite"].lower() == "lax"
    assert cookie["path"] == "/"
    assert cookie["domain"] == ""
    assert int(cookie["max-age"]) == minutes * 60


@pytest.mark.parametrize(
    "environment, expected_name, expected_secure",
    [("dev", "access_token", False), ("prod", "__Host-access_token", True)],
)
def test_clear_auth_cookie_expires_same_cookie_with_matching_scope(
    environment, expected_name, expected_secure
):
    response = Response()

    clear_auth_cookie(response, cookie_settings(environment))

    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])
    assert set(cookies) == {expected_name}
    cookie = cookies[expected_name]
    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert cookie["expires"]
    assert cookie["path"] == "/"
    assert cookie["domain"] == ""
    assert cookie["httponly"] is True
    assert bool(cookie["secure"]) is expected_secure
    assert cookie["samesite"].lower() == "lax"
