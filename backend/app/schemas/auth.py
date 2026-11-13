"""Respostas públicas de autenticação e inicialização CSRF."""

from pydantic import BaseModel


class CsrfRead(BaseModel):
    """Token público a enviar em X-CSRF-Token; não é o JWT nem a pré-sessão."""

    csrf_token: str
