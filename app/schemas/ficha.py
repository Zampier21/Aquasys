from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─── Item do check-list de maquinários ───────────────────
class EquipamentoInput(BaseModel):
    equipamento: str = Field(..., min_length=1, max_length=100)
    presente: bool = False


class EquipamentoResponse(EquipamentoInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


# ─── Teste de água ───────────────────────────────────────
class TesteInput(BaseModel):
    parametro: str = Field(..., min_length=1, max_length=60)
    valor: Optional[float] = None
    unidade: Optional[str] = Field(default=None, max_length=10)


class TesteResponse(TesteInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


# ─── Aba de descrição ────────────────────────────────────
class DescricaoInput(BaseModel):
    chao_malhado: Optional[bool] = None
    conferido_2x: Optional[bool] = None
    stability_aplicado: Optional[bool] = None
    itens_deixados: Optional[str] = None
    descricao_livre: Optional[str] = None


class DescricaoResponse(DescricaoInput):
    model_config = ConfigDict(from_attributes=True)


# ─── Cliente de manutenção (o cadastro reaproveitado) ────
class ClienteManutencaoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    telefone: Optional[str] = Field(default=None, max_length=30)
    endereco: Optional[str] = Field(default=None, max_length=250)

    # Repetem entre visitas: saem daqui pré-preenchidos na ficha.
    tipo_instalacao: Optional[str] = Field(default=None, max_length=20)
    volume_litros: Optional[int] = Field(default=None, gt=0)
    agua_doce: Optional[bool] = None

    observacoes: Optional[str] = None


class ClienteManutencaoCreate(ClienteManutencaoBase):
    pass


class ClienteManutencaoUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=150)
    telefone: Optional[str] = Field(default=None, max_length=30)
    endereco: Optional[str] = Field(default=None, max_length=250)
    tipo_instalacao: Optional[str] = Field(default=None, max_length=20)
    volume_litros: Optional[int] = Field(default=None, gt=0)
    agua_doce: Optional[bool] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class ClienteManutencaoResponse(ClienteManutencaoBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ativo: bool
    criado_em: datetime
    # Quantas visitas já foram feitas — o histórico do cliente.
    total_fichas: int = 0
    ultima_visita: Optional[date] = None


# ─── Entrada: criar ficha ────────────────────────────────
class FichaCreate(BaseModel):
    cliente_id: Optional[UUID] = None
    nome_cliente: Optional[str] = Field(default=None, min_length=2, max_length=150)
    nome_empresa: Optional[str] = Field(default=None, max_length=150)
    data_atendimento: Optional[date] = None
    horario_chegada: Optional[str] = Field(default=None, max_length=10)
    horario_saida: Optional[str] = Field(default=None, max_length=10)
    tipo_instalacao: Optional[str] = Field(default=None, max_length=20)
    volume_litros: Optional[int] = Field(default=None, gt=0)
    agua_doce: Optional[bool] = None
    observacoes: Optional[str] = None

    equipamentos: List[EquipamentoInput] = Field(default_factory=list)
    testes: List[TesteInput] = Field(default_factory=list)
    descricao: Optional[DescricaoInput] = None


# ─── Entrada: editar ficha ───────────────────────────────
class FichaUpdate(BaseModel):
    nome_cliente: Optional[str] = Field(default=None, min_length=2, max_length=150)
    nome_empresa: Optional[str] = Field(default=None, max_length=150)
    data_atendimento: Optional[date] = None
    horario_chegada: Optional[str] = Field(default=None, max_length=10)
    horario_saida: Optional[str] = Field(default=None, max_length=10)
    tipo_instalacao: Optional[str] = Field(default=None, max_length=20)
    volume_litros: Optional[int] = Field(default=None, gt=0)
    agua_doce: Optional[bool] = None
    observacoes: Optional[str] = None

    # Quando vêm preenchidas, substituem a lista inteira da ficha.
    equipamentos: Optional[List[EquipamentoInput]] = None
    testes: Optional[List[TesteInput]] = None
    descricao: Optional[DescricaoInput] = None


# ─── Saída: resumo para a lista de manutenções ───────────
class FichaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cliente_id: Optional[UUID] = None
    nome_cliente: str
    nome_empresa: Optional[str] = None
    data_atendimento: Optional[date] = None
    tipo_instalacao: Optional[str] = None
    criado_em: datetime


# ─── Saída: ficha completa ───────────────────────────────
class FichaResponse(FichaResumo):
    horario_chegada: Optional[str] = None
    horario_saida: Optional[str] = None
    volume_litros: Optional[int] = None
    agua_doce: Optional[bool] = None
    observacoes: Optional[str] = None
    atualizado_em: Optional[datetime] = None

    equipamentos: List[EquipamentoResponse] = Field(default_factory=list)
    testes: List[TesteResponse] = Field(default_factory=list)
    descricao: Optional[DescricaoResponse] = None
