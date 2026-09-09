import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Alerta(Base):
    """
    Um problema aberto de um aquário.

    Guarda só o estado atual, sem histórico: cada nova medição apaga os
    alertas anteriores daquele aquário e grava os que ainda valem. O que
    fica registrado no tempo é a medição (`parametros_agua`), não o alerta.

    Ficam gravados — em vez de calculados a cada request — porque o
    celular do cliente precisa lembrá-lo do problema mesmo com o app
    fechado.
    """

    __tablename__ = "alerta"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aquario_id = Column(UUID(as_uuid=True), ForeignKey("aquario.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    mensagem   = Column(Text, nullable=False)
    # parametro | compatibilidade | manutencao (CHECK no banco)
    tipo       = Column(String(25), nullable=True)
    lido       = Column(Boolean, nullable=False, default=False)
    criado_em  = Column(DateTime, nullable=False, server_default=func.now())
