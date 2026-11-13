"""Respostas públicas de autenticação e inicialização CSRF."""

from typing import Literal

from pydantic import BaseModel


class CsrfRead(BaseModel):
    """Token público a enviar em X-CSRF-Token; não é o JWT nem a pré-sessão."""

    csrf_token: str


class LoginResponse(BaseModel):
    """Confirma o login sem expor o JWT, que é transportado somente no cookie."""

    detail: Literal["Login realizado"] = "Login realizado"
