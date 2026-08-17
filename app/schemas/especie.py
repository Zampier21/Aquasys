from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EspecieBase(BaseModel):
    nome_comum: str = Field(..., min_length=1, max_length=100)
    nome_cientifico: Optional[str] = None
    familia: Optional[str] = None
    tipo_agua: Optional[str] = None
    origem: Optional[str] = None

    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    ph_min: Optional[float] = Field(default=None, ge=0, le=14)
    ph_max: Optional[float] = Field(default=None, ge=0, le=14)
    dgh_min: Optional[float] = None
    dgh_max: Optional[float] = None

    tamanho_adulto_cm: Optional[float] = Field(default=None, gt=0)
    volume_minimo_l: Optional[int] = Field(default=None, gt=0)

    comportamento: Optional[str] = None
    agressivo_coespecificos: bool = False
    agrupamento: Optional[str] = None
    cardume_minimo: Optional[int] = None
    nivel_natacao: Optional[str] = None

    morde_barbatana: bool = False
    barbatana_longa: bool = False
    come_plantas: bool = False
    come_invertebrados: bool = False
    reef_safe: Optional[str] = None

    alimentacao: Optional[str] = None
    nivel_dificuldade: Optional[str] = None
    expectativa_vida_anos: Optional[int] = None

    imagem_url: Optional[str] = None
    observacoes: Optional[str] = None


class EspecieCreate(EspecieBase):
    pass


class EspecieResponse(EspecieBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ativo: bool
    criado_em: datetime


# ═══════════════════════════════════════════════════════
# ANÁLISE DE COMPATIBILIDADE
# ═══════════════════════════════════════════════════════
class AvisoCompat(BaseModel):
    nivel: str      # otimo | ok | ruim | fatal
    motivo: str     # ambiente | parametros | predacao | agressao | ...
    mensagem: str


class AnaliseResponse(BaseModel):
    """
    decisao assume três valores:

      liberado             tudo dentro do ideal
      requer_confirmacao   ressalvas corrigíveis (pH, temperatura, cardume)
      bloqueado            impedimento sem solução
    """

    nivel: str
    decisao: str
    pode_adicionar: bool
    exige_confirmacao: bool
    motivos_bloqueio: List[str] = []
    ressalvas: List[str] = []
    avisos: List[AvisoCompat] = []


class CompatividadeResumo(BaseModel):
    """Item da listagem de espécies avaliadas contra um aquário."""

    especie_id: str
    nome_comum: str
    nivel: str
    decisao: str
    avisos: List[str] = []


class SimulacaoRequest(BaseModel):
    especie_id: UUID
    aquario_id: UUID
    quantidade: int = Field(default=1, gt=0)