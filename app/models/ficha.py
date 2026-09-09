import uuid

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ClienteManutencao(Base):
    """
    Quem a loja visita em casa.

    Não é o mesmo que o cliente com acesso ao app (esse vive em
    `usuario`, com senha): aqui não há login nenhum. É agenda de
    contato, para o técnico não redigitar os mesmos dados a cada
    visita ao mesmo endereço.

    Os campos de instalação repetem entre visitas, então saem daqui
    pré-preenchidos na ficha — que pode divergir se o cliente trocou
    de aquário e ainda não atualizou o cadastro.
    """

    __tablename__ = "cliente_manutencao"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dono_id = Column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)

    nome     = Column(String(150), nullable=False)
    telefone = Column(String(30), nullable=True)
    endereco = Column(String(250), nullable=True)

    tipo_instalacao = Column(String(20), nullable=True)   # aquario | lago
    volume_litros   = Column(Integer, nullable=True)
    agua_doce       = Column(Boolean, nullable=True)      # False = marinho

    observacoes   = Column(Text, nullable=True)
    ativo         = Column(Boolean, nullable=False, default=True)
    criado_em     = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=True)

    fichas = relationship("FichaManutencao", back_populates="cliente")


class FichaManutencao(Base):
    """
    Ficha técnica de atendimento.

    Atende quem a loja visita em casa — que não é a mesma lista de
    quem tem acesso ao app. O contato fica em `ClienteManutencao` e é
    reaproveitado entre visitas; aqui fica o que muda a cada uma.
    """

    __tablename__ = "ficha_manutencao"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dono_id = Column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)

    cliente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cliente_manutencao.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ─── Informações do atendimento ────────────────────
    # Retrato do nome no dia do atendimento: cliente renomeado depois
    # não reescreve a história das fichas antigas.
    nome_cliente     = Column(String(150), nullable=False)
    nome_empresa     = Column(String(150), nullable=True)
    data_atendimento = Column(Date, nullable=True)
    horario_chegada  = Column(String(10), nullable=True)   # "14:30"
    horario_saida    = Column(String(10), nullable=True)
    tipo_instalacao  = Column(String(20), nullable=True)   # aquario | lago
    volume_litros    = Column(Integer, nullable=True)
    agua_doce        = Column(Boolean, nullable=True)      # False = marinho
    observacoes      = Column(Text, nullable=True)

    criado_em     = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=True)

    cliente = relationship("ClienteManutencao", back_populates="fichas")

    equipamentos = relationship(
        "ChecklistEquipamento",
        back_populates="ficha",
        cascade="all, delete-orphan",
    )
    testes = relationship(
        "TesteAgua",
        back_populates="ficha",
        cascade="all, delete-orphan",
    )
    # Um-para-um: cada ficha tem no máximo uma descrição.
    descricao = relationship(
        "DescricaoManutencao",
        back_populates="ficha",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ChecklistEquipamento(Base):
    """Um maquinário conferido no atendimento."""

    __tablename__ = "checklist_equipamento"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ficha_id    = Column(UUID(as_uuid=True), ForeignKey("ficha_manutencao.id", ondelete="CASCADE"), nullable=False)
    equipamento = Column(String(100), nullable=False)
    presente    = Column(Boolean, nullable=False, default=False)

    ficha = relationship("FichaManutencao", back_populates="equipamentos")


class TesteAgua(Base):
    """Um parâmetro medido no atendimento."""

    __tablename__ = "teste_agua"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ficha_id  = Column(UUID(as_uuid=True), ForeignKey("ficha_manutencao.id", ondelete="CASCADE"), nullable=False)
    parametro = Column(String(60), nullable=False)
    valor     = Column(Float, nullable=True)
    unidade   = Column(String(10), nullable=True)

    ficha = relationship("FichaManutencao", back_populates="testes")


class DescricaoManutencao(Base):
    """Aba de descrição do serviço prestado."""

    __tablename__ = "descricao_manutencao"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ficha_id = Column(UUID(as_uuid=True), ForeignKey("ficha_manutencao.id", ondelete="CASCADE"), nullable=False)

    chao_malhado       = Column(Boolean, nullable=True)
    conferido_2x       = Column(Boolean, nullable=True)
    stability_aplicado = Column(Boolean, nullable=True)
    itens_deixados     = Column(Text, nullable=True)
    descricao_livre    = Column(Text, nullable=True)

    ficha = relationship("FichaManutencao", back_populates="descricao")
