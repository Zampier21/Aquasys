import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.documento import documento_valido, somente_digitos, tipo_documento

# Checagem leve de e-mail — evita depender do pacote email-validator.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _limpar_email(valor: Optional[str]) -> Optional[str]:
    if valor is None or valor.strip() == "":
        return None
    valor = valor.strip()
    if not _EMAIL.match(valor):
        raise ValueError("E-mail inválido")
    return valor


# ─── Entrada: cadastrar cliente (feito pelo dono) ────────
class ClienteCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    cpf_cnpj: str = Field(..., description="CPF ou CNPJ, com ou sem máscara")
    senha_inicial: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = Field(default=None, max_length=150)

    @field_validator("cpf_cnpj")
    @classmethod
    def _validar_documento(cls, valor: str) -> str:
        digitos = somente_digitos(valor)
        tipo = tipo_documento(digitos)

        if tipo is None:
            raise ValueError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos)")
        if not documento_valido(digitos):
            raise ValueError("CPF inválido" if tipo == "cpf" else "CNPJ inválido")

        # Guarda sempre sem máscara — a formatação é responsabilidade da tela.
        return digitos

    @field_validator("email")
    @classmethod
    def _validar_email(cls, valor: Optional[str]) -> Optional[str]:
        return _limpar_email(valor)


# ─── Entrada: editar cliente ─────────────────────────────
class ClienteUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=150)
    email: Optional[str] = Field(default=None, max_length=150)
    senha: Optional[str] = Field(default=None, min_length=6, max_length=100)
    ativo: Optional[bool] = None

    @field_validator("email")
    @classmethod
    def _validar_email(cls, valor: Optional[str]) -> Optional[str]:
        return _limpar_email(valor)


# ─── Saída: cliente para o app ───────────────────────────
class ClienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    cpf_cnpj: str          # já formatado pela rota
    email: Optional[str] = None
    ativo: bool
    criado_em: datetime


# ─── Saída: plano da loja e consumo de acessos ───────────
class PlanoResponse(BaseModel):
    """Quanto da assinatura já está em uso.

    O aplicativo mostra isto na tela de acessos, para que a loja veja o
    teto antes de esbarrar nele — e não depois, com um erro na cara.
    """

    plano: str
    rotulo: str
    ativos: int
    # Nulo quando o plano não tem teto.
    limite: Optional[int] = None
    restantes: Optional[int] = None
    ilimitado: bool
