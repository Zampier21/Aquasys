from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─── Entrada: criar aquário ──────────────────────────────
class AquarioCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    volume_litros: float = Field(..., gt=0)
    temperatura: float
    ph: float = Field(..., ge=0, le=14)
    tipo: Optional[str] = None

    # Parâmetros químicos — opcionais no cadastro
    amonia_ppm: float = Field(default=0, ge=0)
    nitrito_ppm: float = Field(default=0, ge=0)
    nitrato_ppm: float = Field(default=0, ge=0)


# ─── Entrada: editar aquário ─────────────────────────────
class AquarioUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=100)
    volume_litros: Optional[float] = Field(default=None, gt=0)
    temperatura: Optional[float] = None
    ph: Optional[float] = Field(default=None, ge=0, le=14)
    tipo: Optional[str] = None

    amonia_ppm: Optional[float] = Field(default=None, ge=0)
    nitrito_ppm: Optional[float] = Field(default=None, ge=0)
    nitrato_ppm: Optional[float] = Field(default=None, ge=0)


# ─── Saída: aquário completo para o app ──────────────────
class AquarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    volume_litros: float
    temperatura: float
    ph: float
    tipo: Optional[str] = None

    # Vêm da última medição em parametros_agua
    amonia_ppm: float = 0
    nitrito_ppm: float = 0
    nitrato_ppm: float = 0
    medido_em: Optional[datetime] = None
    problemas: List[str] = Field(default_factory=list)
    faixas: Dict[str, str] = Field(default_factory=dict)
    explicacoes: Dict[str, str] = Field(default_factory=dict)
    escala_ph: str = ""

    criado_em: datetime


# ─── Entrada: registrar nova medição ─────────────────────
class ParametrosCreate(BaseModel):
    amonia_ppm: float = Field(default=0, ge=0)
    nitrito_ppm: float = Field(default=0, ge=0)
    nitrato_ppm: float = Field(default=0, ge=0)


# ─── Saída: histórico de medições ────────────────────────
class ParametrosResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amonia_ppm: float
    nitrito_ppm: float
    nitrato_ppm: float
    registrado_em: datetime