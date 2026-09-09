from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─── Entrada: criar/editar curso (feito pela loja) ───────
class CursoCreate(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=150)
    descricao: Optional[str] = None
    categoria: Optional[str] = Field(default=None, max_length=50)


# ─── Entrada: adicionar aula colando o link ──────────────
class AulaCreate(BaseModel):
    # Aceita a URL em qualquer formato, ou o id puro. Título e miniatura
    # vêm do YouTube; só é preciso digitar se quiser sobrescrever.
    url: str = Field(..., min_length=5, max_length=300)
    titulo: Optional[str] = Field(default=None, max_length=200)


class PlaylistImportar(BaseModel):
    """Link de uma playlist do YouTube (o que tem `list=` na URL)."""
    url: str = Field(..., min_length=12, max_length=300)


# ─── Saída ───────────────────────────────────────────────
class AulaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    titulo: str
    youtube_id: str
    canal: Optional[str] = None
    miniatura_url: Optional[str] = None
    ordem: int
    concluida: bool = False


class CursoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    titulo: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    miniatura_url: Optional[str] = None
    # True = curso global do AquaSys; False = curso próprio da loja.
    # ("global" é palavra reservada em Python, daí o nome composto.)
    curso_global: bool = True
    total_aulas: int = 0
    aulas_concluidas: int = 0
    percentual: int = 0


class CursoResponse(CursoResumo):
    aulas: List[AulaResponse] = Field(default_factory=list)
    publicado_em: Optional[datetime] = None
