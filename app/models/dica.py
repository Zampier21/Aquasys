import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Dica(Base):
    """
    Dica exibida na Home.

    `especie_id` nulo = dica geral, vale para todo mundo. Preenchido, a
    dica só aparece para quem tem aquela espécie no aquário.
    """

    __tablename__ = "dica"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conteudo   = Column(Text, nullable=False)
    # quimica | comportamento | equipamento (CHECK no banco)
    categoria  = Column(String(30), nullable=True)
    especie_id = Column(UUID(as_uuid=True), ForeignKey("especie.id", ondelete="CASCADE"), nullable=True)
    ativa      = Column(Boolean, nullable=False, default=True)
