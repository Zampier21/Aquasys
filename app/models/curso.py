import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Curso(Base):
    __tablename__ = "curso"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dono_id       = Column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=True)
    titulo        = Column(String(150), nullable=False)
    descricao     = Column(Text, nullable=True)
    miniatura_url = Column(String(255), nullable=True)
    categoria     = Column(String(50), nullable=True)
    publicado_em  = Column(DateTime, nullable=True, server_default=func.now())
    ativo         = Column(Boolean, nullable=False, default=True)

    aulas = relationship(
        "Aula",
        back_populates="curso",
        cascade="all, delete-orphan",
        order_by="Aula.ordem",
    )

    @property
    def global_(self) -> bool:
        return self.dono_id is None


class Aula(Base):
    __tablename__ = "aula"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    curso_id      = Column(UUID(as_uuid=True), ForeignKey("curso.id", ondelete="CASCADE"), nullable=False)
    titulo        = Column(String(200), nullable=False)
    youtube_id    = Column(String(20), nullable=False)
    canal         = Column(String(120), nullable=True)
    miniatura_url = Column(String(255), nullable=True)
    ordem         = Column(Integer, nullable=False, default=0)
    criado_em     = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("curso_id", "youtube_id", name="uq_aula_curso_video"),
    )

    curso = relationship("Curso", back_populates="aulas")


class ProgressoAula(Base):
    __tablename__ = "progresso_aula"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id    = Column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    aula_id       = Column(UUID(as_uuid=True), ForeignKey("aula.id", ondelete="CASCADE"), nullable=False)
    concluida     = Column(Boolean, nullable=False, default=False)
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("usuario_id", "aula_id", name="uq_progresso_aula"),
    )


class ProgressoCurso(Base):
    """Cache do percentual concluído, para a lista não recalcular tudo."""

    __tablename__ = "progresso_curso"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id    = Column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    curso_id      = Column(UUID(as_uuid=True), ForeignKey("curso.id", ondelete="CASCADE"), nullable=False)
    percentual    = Column(Integer, nullable=False, default=0)
    iniciado_em   = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=True)
