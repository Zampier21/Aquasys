from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome          = Column(String(150), nullable=False)
    cpf_cnpj      = Column(String(18), nullable=False, unique=True)
    senha_hash    = Column(String(255), nullable=False)
    tipo          = Column(String(10), nullable=False)
    dono_id       = Column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=True)
    # Plano da assinatura. Só faz sentido para a loja (tipo='dono'); no
    # cliente fica nulo, porque quem assina é a loja. O teto de acessos
    # que cada plano concede está em app/core/planos.py — aqui guarda-se
    # apenas qual plano é, para que a régua comercial possa mudar sem
    # migração de banco.
    plano         = Column(String(20), nullable=True)
    email         = Column(String(150), nullable=True)
    # Foto de perfil / logo em base64 puro. Nulo = o app usa o ícone padrão.
    avatar        = Column(Text, nullable=True)
    ativo         = Column(Boolean, nullable=False, default=True)
    criado_em     = Column(DateTime, nullable=False, default=func.now())
    atualizado_em = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("tipo IN ('dono', 'cliente')", name="chk_tipo"),
        # Nulo é permitido: é o que o cliente guarda, e é o que as contas
        # criadas antes desta coluna existir têm. O que não se admite é um
        # plano inventado, que faria o teto cair silenciosamente no padrão.
        CheckConstraint(
            "plano IS NULL OR plano IN ('basico', 'profissional', 'ilimitado')",
            name="chk_plano",
        ),
    )
