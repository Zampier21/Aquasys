from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import Entrada

# ═══════════════════════════════════════════════════════
# CATÁLOGO DE ESPÉCIES
# ═══════════════════════════════════════════════════════
class EspecieBase(BaseModel):
    nome_comum: str = Field(..., min_length=1, max_length=100)
    nome_cientifico: Optional[str] = None
    nomes_alternativos: Optional[str] = None
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

    # Classificação climática da espécie. Sai na resposta para a tela
    # poder avisar "subtropical" num aquário tropical, mesmo antes de
    # alguém preencher a faixa em graus.
    clima: Optional[str] = None
    # Crédito de quem publicou a medida. A licença da FishBase exige
    # atribuição onde o dado aparecer, então isto não é enfeite: é o
    # que a ficha mostra embaixo dos números.
    fonte_dados: Optional[str] = None


class EspecieCreate(EspecieBase, Entrada):
    """Cadastro manual de espécie.

    Herda de `Entrada` para recusar campo não declarado: a rota monta a
    espécie com `Especie(**dados.model_dump())`, e é justamente essa
    forma que transforma um campo a mais em coluna escrita.
    """
class VariedadeResumo(BaseModel):
    """Uma variedade dentro do card da espécie-base.

    Leva só identidade e foto: a biologia é a mesma da base, e repeti-la
    aqui faria a resposta do catálogo crescer sem informar nada novo.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # Nome completo, para busca e para o título da ficha.
    nome_comum: str
    # Nome sem repetir o da base: "Leopardo Azul" dentro de "Acará Bandeira".
    nome_curto: str
    imagem: Optional[str] = None
    imagem_miniatura: Optional[str] = None
    imagem_credito: Optional[str] = None


class EspecieResponse(EspecieBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ativo: bool
    criado_em: datetime
    imagem: Optional[str] = None
    imagem_miniatura: Optional[str] = None
    imagem_credito: Optional[str] = None
    # Variedades desta espécie. Vazia na maioria delas; o catálogo lista
    # apenas as bases, e as variedades aparecem ao abrir o card.
    variedades: List[VariedadeResumo] = []


# ═══════════════════════════════════════════════════════
# ANÁLISE DE COMPATIBILIDADE
# ═══════════════════════════════════════════════════════
class AvisoCompat(BaseModel):
    nivel: str      # otimo | ok | ruim | fatal
    motivo: str     # ambiente | parametros | predacao | agressao | ...
    mensagem: str


class AnaliseResponse(BaseModel):
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


class SimulacaoRequest(Entrada):
    especie_id: UUID
    aquario_id: UUID
    quantidade: int = Field(default=1, gt=0)


# ═══════════════════════════════════════════════════════
# POVOAMENTO — espécies dentro de cada aquário
# ═══════════════════════════════════════════════════════
class PovoamentoCreate(Entrada):
    """Corpo do POST que adiciona uma espécie ao aquário."""

    especie_id: UUID
    quantidade: int = Field(default=1, gt=0)


class PovoamentoUpdate(Entrada):
    """Ajuste de quantidade de uma espécie já presente."""

    quantidade: int = Field(..., gt=0)


class HabitanteResponse(BaseModel):
    """Uma espécie que vive no aquário, com dados úteis para a tela."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID                 # id da linha em aquario_especie
    especie_id: UUID
    nome_comum: str
    nome_cientifico: Optional[str] = None
    quantidade: int
    tamanho_adulto_cm: Optional[float] = None
    comportamento: Optional[str] = None
    # Nulo = sem foto; o app desenha o ícone padrão.
    imagem_miniatura: Optional[str] = None
    adicionado_em: datetime

# ═══════════════════════════════════════════════════════
# IMPORTAÇÃO DA LISTA DA LOJA
# ═══════════════════════════════════════════════════════
class CandidatoImportacao(BaseModel):
    """Uma das espécies que o nome lido pode designar."""

    id: UUID
    nome_comum: str
    nome_cientifico: Optional[str] = None


class ItemImportado(BaseModel):
    """O resultado da conferência de um nome da planilha."""

    linha: int
    nome_lido: str
    vezes: int                       # quantas vezes o nome se repete na lista
    # encontrado | criado | ambiguo | nao_encontrado
    situacao: str

    # Preenchidos quando a situação é "encontrado".
    como: Optional[str] = None       # por qual nome o casamento aconteceu
    especie_id: Optional[UUID] = None
    nome_comum: Optional[str] = None
    nome_cientifico: Optional[str] = None
    variedade_de: Optional[str] = None

    # "ambiguo" traz as espécies possíveis; "nao_encontrado", os nomes do
    # catálogo parecidos com o que foi digitado.
    candidatos: List[CandidatoImportacao] = []
    sugestoes: List[str] = []


class ResumoGravacao(BaseModel):
    """O que a importação efetivamente gravou."""

    vinculados: int        # já existiam no catálogo e entraram no estoque
    criados: int           # viraram rascunho da loja, a revisar
    com_cientifico: int    # dos criados, quantos ganharam nome científico
    ja_estavam: int        # já constavam do estoque de antes
    ignorados: int         # ambíguos, que exigem decisão da loja
    sem_busca: bool        # a fonte externa não respondeu

    # Quantos dos criados a FishBase conseguiu preencher, e se ela
    # respondeu. A tela usa os dois para dizer à loja quanto de ficha
    # ainda falta digitar.
    com_ficha: int = 0
    sem_fishbase: bool = False


class ImportacaoResponse(BaseModel):
    """Conferência da lista e, quando pedido, o que foi gravado."""

    total_linhas: int                # nomes lidos, contando repetições
    total_nomes: int                 # nomes distintos conferidos
    encontrados: int
    ambiguos: int
    nao_encontrados: int
    criados: int = 0
    aplicado: bool = False
    gravacao: Optional[ResumoGravacao] = None
    itens: List[ItemImportado]
