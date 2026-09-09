import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, LargeBinary, String, Text, UniqueConstraint,
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

    # Chama-se `foto`, e não `imagem`, para não colidir com o campo
    # `imagem` da resposta da API — que é só o caminho da URL. A colisão
    # existiu: o Pydantic lia este atributo ao montar a resposta e o
    # `lazy="raise"` estourava.
    #
    # E o `lazy="raise"` é de propósito: carregar isto sem querer traz os
    # bytes da foto junto, em toda espécie da listagem. Quem precisa da
    # imagem consulta `EspecieImagem` direto.
    foto = relationship(
        "EspecieImagem",
        back_populates="especie",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )


class EspecieImagem(Base):
    """
    Foto da espécie, em duas resoluções.

    Tabela à parte de `especie` porque o catálogo inteiro é lido a cada
    abertura da aba Peixes: com os bytes na mesma linha, cada listagem
    arrastaria megabytes que ninguém pediu.
    """

    __tablename__ = "especie_imagem"

    especie_id = Column(
        UUID(as_uuid=True),
        ForeignKey("especie.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # miniatura: quadrada, o círculo da lista.
    # completa:  proporção original, o card aberto.
    miniatura = Column(LargeBinary, nullable=False)
    completa  = Column(LargeBinary, nullable=False)
    mime      = Column(String(30), nullable=False, default="image/jpeg")

    # sha256 da imagem completa — vira o ETag da resposta.
    hash      = Column(String(64), nullable=False)

    largura         = Column(Integer)
    altura          = Column(Integer)
    bytes_miniatura = Column(Integer)
    bytes_completa  = Column(Integer)

    # Crédito. As fotos vêm sob licença Creative Commons, que exige
    # citar autor e licença onde a imagem é exibida.
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