import pytest

from app.core.origins import parse_origin


@pytest.mark.parametrize(
    "value, expected",
    [
        ("https://app.example.com", ("https", "app.example.com", 443)),
        ("http://localhost:5173", ("http", "localhost", 5173)),
        ("HTTPS://APP.EXAMPLE.COM:8443", ("https", "app.example.com", 8443)),
    ],
)
def test_parse_origin_normalizes_scheme_host_and_port(value, expected):
    assert parse_origin(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        " https://app.example.com",
        "https://app.example.com\n",
        "ftp://app.example.com",
        "https://",
        "https://user:pass@app.example.com",
        "https://app.example.com:0",
        "https://app.example.com:99999",
        "https://app.example.com:porta",
        "https://app.example.com/",
        "https://app.example.com?x=1",
        "https://app.example.com#frag",
        "null",
    ],
)
def test_parse_origin_rejects_non_exact_origins(value):
    assert parse_origin(value) is None


def test_referer_accepts_path_and_query_but_not_fragment():
    assert parse_origin("https://app.example.com/login?next=/", referer=True) == (
        "https",
        "app.example.com",
        443,
    )
    assert parse_origin("https://app.example.com/login#x", referer=True) is None
