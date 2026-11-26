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


class InvalidCsrfTokenError(DomainError):
    """Origem ou token CSRF ausente, adulterado, expirado ou de outra sessão."""

    code = "CSRF_INVALID"
    message = "Validação CSRF inválida; atualize a sessão e tente novamente"


class WrongPasswordError(DomainError):
    """A senha atual informada na troca de senha não confere."""

    code = "WRONG_PASSWORD"
    message = "Senha atual incorreta"


class InvalidPasswordError(DomainError):
    """A nova senha não atende à política ou é igual à senha atual."""

    code = "INVALID_PASSWORD"
    message = "A nova senha é inválida"


class InvalidImageError(DomainError):
    """Imagem de perfil com tipo, assinatura ou tamanho não permitidos."""

    code = "INVALID_IMAGE"
    message = "Imagem inválida: use JPEG, PNG ou WebP de até 2 MB"


class NotFoundError(DomainError):
    """Recurso não encontrado."""

    code = "NOT_FOUND"
    message = "Recurso não encontrado"


class DatabaseUnavailableError(DomainError):
    """O banco de dados não respondeu (usado pelo health check)."""

    code = "DATABASE_UNAVAILABLE"
    message = "Banco de dados indisponível"


class QuotaExceededError(DomainError):
    """O arquivo não cabe na cota do usuário (ADR-022). O service informa o espaço livre."""

    code = "QUOTA_EXCEEDED"
    message = "Cota de armazenamento excedida"


class FileTooLargeError(DomainError):
    """O arquivo passa do limite por arquivo (`MAX_UPLOAD_BYTES`)."""

    code = "FILE_TOO_LARGE"
    message = "O arquivo passa do tamanho máximo permitido"


class UnsupportedFileError(DomainError):
    """Tipo não aceito, ou conteúdo (magic bytes) diferente do tipo declarado."""

    code = "UNSUPPORTED_FILE"
    message = "Tipo de arquivo não suportado"


class UploadNotPendingError(DomainError):
    """`complete` de um arquivo que não está mais aguardando o envio."""

    code = "UPLOAD_NOT_PENDING"
    message = "Este upload já foi concluído ou cancelado"


class UploadMissingError(DomainError):
    """`complete` chamado sem o arquivo ter chegado ao storage."""

    code = "UPLOAD_MISSING"
    message = "O arquivo ainda não foi enviado"
