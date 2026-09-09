import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float,
    ForeignKey, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Aquario(Base):
    __tablename__ = "aquario"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id    = Column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    nome          = Column(String(100), nullable=False)
    volume_litros = Column(Float, nullable=False)
    temperatura   = Column(Float, nullable=False)
    ph            = Column(Float, nullable=False)
    tipo          = Column(String(20), nullable=True)
    criado_em     = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("volume_litros > 0", name="chk_volume"),
        CheckConstraint("ph BETWEEN 0 AND 14", name="chk_ph"),
    )
    parametros = relationship(
        "ParametrosAgua",
        back_populates="aquario",
        cascade="all, delete-orphan",
        order_by="desc(ParametrosAgua.registrado_em)",
    )
    habitantes = relationship(
        "Especie",
        secondary="aquario_especie",
        viewonly=True,
        order_by="Especie.nome_comum",
    )


class ParametrosAgua(Base):
    __tablename__ = "parametros_agua"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aquario_id    = Column(UUID(as_uuid=True), ForeignKey("aquario.id", ondelete="CASCADE"), nullable=False)
    amonia_ppm    = Column(Float, nullable=False, default=0)
    nitrito_ppm   = Column(Float, nullable=False, default=0)
    nitrato_ppm   = Column(Float, nullable=False, default=0)
    registrado_em = Column(DateTime, nullable=False, server_default=func.now())

    aquario = relationship("Aquario", back_populates="parametros")
