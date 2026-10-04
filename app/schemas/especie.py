from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

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
# ─── Entrada: revisar a ficha de uma espécie da loja ─────
# Os enumerados são validados aqui, e não só no banco. A tabela tem
# restrição de verificação para cada um deles; sem o `Literal`, um
# valor fora da lista chegaria ao PostgreSQL, estouraria lá e voltaria
# como erro 500. Validado aqui, volta 422 dizendo o que é aceito.
TipoAgua = Literal["doce", "salobra", "marinho"]
Comportamento = Literal["pacifico", "semi_agressivo", "territorial",
                        "agressivo"]
Agrupamento = Literal["cardume", "par", "harem", "solitario"]
NivelNatacao = Literal["fundo", "meio", "superficie", "todos"]
ReefSafe = Literal["sim", "com_ressalva", "nao"]
Dificuldade = Literal["facil", "medio", "dificil"]


class EspecieUpdate(Entrada):
    """Campos que a loja pode corrigir na própria ficha.

    Ficam de fora, de propósito: `dono_id` e `ativo`, que são governo do
    sistema; `variante_de_id`, que mudaria a espécie de família; e
    `clima` e `fonte_dados`, que descrevem de onde o dado veio e não
    seriam mais verdade se fossem digitados por cima.
    """

    nome_comum: Optional[str] = Field(default=None, min_length=1, max_length=100)
    nome_cientifico: Optional[str] = Field(default=None, max_length=150)
    nomes_alternativos: Optional[str] = None
    familia: Optional[str] = Field(default=None, max_length=80)
    origem: Optional[str] = Field(default=None, max_length=120)

    tipo_agua: Optional[TipoAgua] = None
    temp_min: Optional[float] = Field(default=None, ge=-5, le=50)
    temp_max: Optional[float] = Field(default=None, ge=-5, le=50)
    ph_min: Optional[float] = Field(default=None, ge=0, le=14)
    ph_max: Optional[float] = Field(default=None, ge=0, le=14)
    dgh_min: Optional[float] = Field(default=None, ge=0, le=60)
    dgh_max: Optional[float] = Field(default=None, ge=0, le=60)

    tamanho_adulto_cm: Optional[float] = Field(default=None, gt=0, le=500)
    volume_minimo_l: Optional[int] = Field(default=None, gt=0, le=100000)

    comportamento: Optional[Comportamento] = None
    agressivo_coespecificos: Optional[bool] = None
    agrupamento: Optional[Agrupamento] = None
    cardume_minimo: Optional[int] = Field(default=None, gt=0, le=1000)
    nivel_natacao: Optional[NivelNatacao] = None

    morde_barbatana: Optional[bool] = None
    barbatana_longa: Optional[bool] = None
    come_plantas: Optional[bool] = None
    come_invertebrados: Optional[bool] = None
    reef_safe: Optional[ReefSafe] = None

    alimentacao: Optional[str] = Field(default=None, max_length=100)
    nivel_dificuldade: Optional[Dificuldade] = None
    expectativa_vida_anos: Optional[int] = Field(default=None, gt=0, le=200)
    observacoes: Optional[str] = None

    # Marcar como conferida só é aceito quando nada essencial estiver
    # faltando. A rota confere depois de aplicar as mudanças.
    revisada: Optional[bool] = None

    @model_validator(mode="after")
    def _faixas_na_ordem(self):
        """Mínimo acima do máximo é erro de digitação, não faixa.

        Gravado assim, o motor calcularia sobreposição vazia e a espécie
        ficaria incompatível com todo aquário, sem dizer por quê.
        """
        for menor, maior, nome in (
            (self.temp_min, self.temp_max, "temperatura"),
            (self.ph_min, self.ph_max, "pH"),
            (self.dgh_min, self.dgh_max, "dureza"),
        ):
            if menor is not None and maior is not None and menor > maior:
                raise ValueError(
                    f"A {nome} mínima não pode ser maior que a máxima"
                )
        return self


class EspecieIncompleta(BaseModel):
    """Uma espécie da loja à espera de revisão, e o que falta nela."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome_comum: str
    nome_cientifico: Optional[str] = None
    clima: Optional[str] = None
    fonte_dados: Optional[str] = None
    # Rótulos legíveis, na ordem em que a tela pergunta.
    faltam: List[str] = []


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
