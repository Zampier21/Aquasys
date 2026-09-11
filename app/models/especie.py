import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, LargeBinary, String, Text, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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

    # ─── Variedades ────────────────────────────────────
    # Tetra Neon Negro e Tetra Neon Negro Albino são o mesmo peixe: mesma
    # água, mesmo porte, mesmo temperamento. Muda a aparência, e é só ela
    # que a loja precisa mostrar. A variedade aponta para a espécie-base,
    # e o catálogo lista só as bases — assim oito acarás-bandeira não
    # ocupam oito linhas de uma lista percorrida com o polegar.
    #
    # Os campos de biologia da variedade são PREENCHIDOS a partir da
    # base, e não deixados nulos para herdar na leitura. O porquê está em
    # app/services/variedades.py, e resume-se a isto: campo nulo faz a
    # variedade sumir do cálculo da faixa ideal, silenciosamente.
    variante_de_id = Column(
        UUID(as_uuid=True),
        ForeignKey("especie.id", ondelete="CASCADE"),
        nullable=True,
    )
    base = relationship(
        "Especie",
        remote_side=[id],
        back_populates="variantes",
    )
    # Chama-se `variantes`, e não `variedades`, de propósito. O schema
    # de saída tem um campo `variedades`, e o Pydantic, lendo por nome de
    # atributo, tentaria validar estes objetos do ORM como se já fossem o
    # resumo pronto — e falharia por falta do `nome_curto`, que é
    # calculado. Nomes diferentes deixam claro que um é a relação e o
    # outro é o que sai na resposta.
    variantes = relationship(
        "Especie",
        back_populates="base",
        cascade="all, delete-orphan",
        order_by="Especie.nome_comum",
    )

    foto = relationship(
        "EspecieImagem",
        back_populates="especie",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (
        # Uma espécie-BASE por nome científico. O índice já existia no
        # banco sem estar declarado aqui, e por isso o banco de teste — que
        # é montado a partir destes modelos — não o tinha: os testes das
        # variedades passavam, e o banco real as recusava. Declarado, os
        # dois passam a se comportar igual. Variedades ficam de fora porque
        # compartilham o nome científico da base: são o mesmo animal.
        Index(
            "idx_especie_cientifico",
            func.lower(nome_cientifico),
            unique=True,
            postgresql_where=text("variante_de_id IS NULL"),
        ),
        # A listagem do catálogo filtra por esta coluna a cada abertura.
        Index("idx_especie_variante_de", "variante_de_id"),
    )


class EspecieImagem(Base):
    __tablename__ = "especie_imagem"

    especie_id = Column(
        UUID(as_uuid=True),
        ForeignKey("especie.id", ondelete="CASCADE"),
        primary_key=True,
    )
    miniatura = Column(LargeBinary, nullable=False)
    completa  = Column(LargeBinary, nullable=False)
    mime      = Column(String(30), nullable=False, default="image/jpeg")
    hash      = Column(String(64), nullable=False)
    largura         = Column(Integer)
    altura          = Column(Integer)
    bytes_miniatura = Column(Integer)
    bytes_completa  = Column(Integer)
    fonte       = Column(Text)
    autor       = Column(String(300))
    licenca     = Column(String(80))
    licenca_url = Column(Text)

    atualizado_em = Column(DateTime, nullable=False, server_default=func.now())

    especie = relationship("Especie", back_populates="foto")

    @property
    def credito(self) -> str | None:
        """'Autor (CC BY-SA 4.0)' — a linha que vai embaixo da foto."""
        if not self.autor and not self.licenca:
            return None
        if not self.autor:
            return self.licenca
        if not self.licenca:
            return self.autor
        return f"{self.autor} ({self.licenca})"


class CompatibEspecie(Base):
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