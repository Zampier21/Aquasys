import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Especie(Base):
    """Catálogo de espécies — base do motor de compatibilidade."""

    __tablename__ = "especie"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_comum      = Column(String(100), nullable=False)
    nome_cientifico = Column(String(150))
    nomes_alternativos = Column(Text)   # outros nomes populares, entram na busca
    familia         = Column(String(80))
    tipo_agua       = Column(String(10))     # doce | salobra | marinho
    origem          = Column(String(120))

    # ─── Parâmetros de água ────────────────────────────
    temp_min = Column(Float)
    temp_max = Column(Float)
    ph_min   = Column(Float)
    ph_max   = Column(Float)
    dgh_min  = Column(Float)
    dgh_max  = Column(Float)

    # ─── Porte e espaço ────────────────────────────────
    tamanho_adulto_cm = Column(Float)
    volume_minimo_l   = Column(Integer)

    # ─── Comportamento ─────────────────────────────────
    comportamento           = Column(String(20))  # pacifico | semi_agressivo | territorial | agressivo
    agressivo_coespecificos = Column(Boolean, default=False)
    agrupamento             = Column(String(15))  # cardume | par | harem | solitario
    cardume_minimo          = Column(Integer)
    nivel_natacao           = Column(String(15))  # fundo | meio | superficie | todos

    # ─── Flags de conflito ─────────────────────────────
    morde_barbatana    = Column(Boolean, default=False)
    barbatana_longa    = Column(Boolean, default=False)
    come_plantas       = Column(Boolean, default=False)
    come_invertebrados = Column(Boolean, default=False)
    reef_safe          = Column(String(15))       # sim | com_ressalva | nao

    # ─── Manejo ────────────────────────────────────────
    alimentacao           = Column(String(100))
    nivel_dificuldade     = Column(String(15))    # facil | medio | dificil
    expectativa_vida_anos = Column(Integer)

    imagem_url  = Column(String(255))
    observacoes = Column(Text)
    ativo       = Column(Boolean, nullable=False, default=True)
    criado_em   = Column(DateTime, nullable=False, server_default=func.now())


class CompatibEspecie(Base):
    """
    Exceções curadas de compatibilidade.

    Sobrescrevem o motor de regras quando a lógica automática
    não representa bem a realidade de uma combinação específica.
    """

    __tablename__ = "compatib_especie"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    especie_a_id = Column(UUID(as_uuid=True), ForeignKey("especie.id", ondelete="CASCADE"), nullable=False)
    especie_b_id = Column(UUID(as_uuid=True), ForeignKey("especie.id", ondelete="CASCADE"), nullable=False)
    nivel        = Column(String(10), nullable=False)  # otimo | ok | ruim | fatal
    motivo       = Column(String(30))
    observacao   = Column(Text)
    fonte        = Column(String(120))

    __table_args__ = (
        UniqueConstraint("especie_a_id", "especie_b_id", name="uq_par_especies"),
    )


class AquarioEspecie(Base):
    """Povoamento: quais espécies vivem em cada aquário e em que quantidade."""

    __tablename__ = "aquario_especie"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aquario_id    = Column(UUID(as_uuid=True), ForeignKey("aquario.id", ondelete="CASCADE"), nullable=False)
    especie_id    = Column(UUID(as_uuid=True), ForeignKey("especie.id", ondelete="CASCADE"), nullable=False)
    quantidade    = Column(Integer, nullable=False, default=1)
    adicionado_em = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("aquario_id", "especie_id", name="uq_aquario_especie"),
    )