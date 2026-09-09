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
    email         = Column(String(150), nullable=True)
    # Foto de perfil / logo em base64 puro. Nulo = o app usa o ícone padrão.
    avatar        = Column(Text, nullable=True)
    ativo         = Column(Boolean, nullable=False, default=True)
    criado_em     = Column(DateTime, nullable=False, default=func.now())
    atualizado_em = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("tipo IN ('dono', 'cliente')", name="chk_tipo"),
    )
