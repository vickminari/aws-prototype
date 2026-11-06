"""Exceções de domínio lançadas pelos services (ARQ §5.2).

Os services não conhecem HTTP: lançam estas exceções, e o handler global em
`app/main.py` as converte em resposta `{"detail": ..., "code": ...}` com o status
definido em `DOMAIN_ERROR_STATUS`.

Para criar uma nova exceção: herde de `DomainError`, defina `code` e `message`
e, se o status não for 400, adicione-a em `DOMAIN_ERROR_STATUS` no `main.py`.
"""


class DomainError(Exception):
    """Base das exceções de domínio.

    Attributes:
        code: identificador estável do erro, usado pelo frontend.
        message: mensagem legível padrão (pode ser sobrescrita no construtor).
    """

    code: str = "DOMAIN_ERROR"
    message: str = "Erro de regra de negócio"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or type(self).message
        super().__init__(self.message)


class EmailAlreadyExistsError(DomainError):
    """Já existe usuário com o email informado."""

    code = "EMAIL_ALREADY_EXISTS"
    message = "Email já cadastrado"


class UsernameAlreadyExistsError(DomainError):
    """Já existe usuário com o username informado."""

    code = "USERNAME_ALREADY_EXISTS"
    message = "Nome de usuário já cadastrado"


class InvalidCredentialsError(DomainError):
    """Login falhou; a mensagem é genérica para não revelar se o usuário existe."""

    code = "INVALID_CREDENTIALS"
    message = "Usuário ou senha inválidos"


class InvalidTokenError(DomainError):
    """Token ausente, expirado, adulterado ou revogado."""

    code = "INVALID_TOKEN"
    message = "Token inválido ou expirado"


class WrongPasswordError(DomainError):
    """A senha atual informada na troca de senha não confere."""

    code = "WRONG_PASSWORD"
    message = "Senha atual incorreta"


class InvalidImageError(DomainError):
    """Imagem de perfil com tipo, assinatura ou tamanho não permitidos."""

    code = "INVALID_IMAGE"
    message = "Imagem inválida: use JPEG, PNG ou WebP de até 2 MB"


class NotFoundError(DomainError):
    """Recurso não encontrado."""

    code = "NOT_FOUND"
    message = "Recurso não encontrado"
