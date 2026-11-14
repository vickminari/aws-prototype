"""Helpers dos testes de sessão HTTP (login, CSRF, usuário autenticado e logout).

As fixtures correspondentes (`session_settings`, `session_client`, ...) ficam em
`tests/integration/conftest.py` e rodam cada teste em `test` e `prod`.
"""

from http.cookies import SimpleCookie

SESSION_ORIGIN = "https://app.example.com"
SESSION_HOST = "app.example.com"
PASSWORD = "Senha-de-teste-123"  # DEFAULT_PASSWORD do user_factory
CSRF_URL = "/api/auth/csrf"
LOGIN_URL = "/api/auth/login"
LOGOUT_URL = "/api/auth/logout"
ME_URL = "/api/users/me"


def cookie_name(settings, base: str = "access_token") -> str:
    """Nome do cookie no ambiente: produção usa o prefixo `__Host-`."""
    return ("__Host-" if settings.environment == "prod" else "") + base


def csrf_headers(client) -> dict[str, str]:
    """Busca o token CSRF da sessão atual e devolve os headers de uma escrita."""
    response = client.get(CSRF_URL)
    assert response.status_code == 200
    return {"Origin": SESSION_ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def login(client, user) -> dict[str, str]:
    """Faz login real e devolve os headers CSRF já vinculados à nova sessão."""
    response = client.post(
        LOGIN_URL,
        data={"username": user.username, "password": PASSWORD},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    return csrf_headers(client)


def put_cookie(client, name: str, value: str) -> None:
    """Define um cookie no escopo do host, substituindo o que o servidor definiu."""
    client.cookies.set(name, value, domain=SESSION_HOST, path="/")


def response_cookies(response) -> SimpleCookie:
    """Interpreta todos os `Set-Cookie` da resposta, com seus atributos."""
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    return cookies
