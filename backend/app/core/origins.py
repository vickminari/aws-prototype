"""Normalização de origens HTTP(S), compartilhada pela configuração e pela validação CSRF."""

from urllib.parse import urlsplit

Origin = tuple[str, str, int]


def parse_origin(value: str, *, referer: bool = False) -> Origin | None:
    """Extrai `(esquema, host, porta)` de uma origem exata; só o Referer aceita caminho e query.

    Retorna `None` para valores com espaços ou caracteres de controle, esquema diferente de
    HTTP(S), credenciais, fragmento, porta inválida ou, fora do Referer, caminho e query.
    """
    if not value or any(char.isspace() or ord(char) < 32 for char in value):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port == 0
        or (not referer and (parsed.path or parsed.query or "?" in value or "#" in value))
    ):
        return None
    default_port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, parsed.hostname, port if port is not None else default_port
