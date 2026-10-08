import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Sessao(Base):
    """Token de renovação de um aparelho conectado.

    O token em si nunca chega aqui: grava-se o SHA-256 dele, pela mesma
    razão que não se guarda senha em texto. Ver sql/014 para o resto do
    raciocínio.
    """

    __tablename__ = "sessao"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    hash        = Column(String(64), nullable=False, unique=True)
    criado_em   = Column(DateTime, nullable=False, default=func.now())
    expira_em   = Column(DateTime, nullable=False)
    # Preenchido quando este token já foi trocado por outro.
    usado_em    = Column(DateTime, nullable=True)
    # Preenchido no logout, ou quando se detecta reúso.
    revogado_em = Column(DateTime, nullable=True)

    @property
    def vale(self) -> bool:
        """Serve para renovar? Só se nunca foi usada, nem revogada, nem venceu."""
        from datetime import datetime

        return (
            self.usado_em is None
            and self.revogado_em is None
            and self.expira_em > datetime.utcnow()
        )
