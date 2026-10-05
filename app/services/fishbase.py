"""Consulta à FishBase para preencher a ficha a partir do nome científico.

A FishBase é a base de referência de peixes mantida pelo consórcio
Q-quatics, com mais de 35 mil espécies. O acesso programático é por
snapshots em parquet publicados pelo rOpenSci no Source Cooperative.

Duas coisas precisam ficar registradas aqui, porque não são óbvias de
fora e já custaram tempo.

**Por que este endereço e não o oficial.** A documentação do rfishbase
manda usar `fishbase.ropensci.org`. Esse domínio está com a cadeia de
certificados quebrada: curl com os certificados do Windows, httpx com
os do certifi e um cliente de outra rede falharam todos, enquanto o
Wikidata respondia normalmente no mesmo instante. O dado mora de fato
no Source Cooperative, com TLS válido, e é de lá que se busca. A
verificação de certificado **não** é desligada em nenhuma hipótese: uma
conexão sem verificação deixaria qualquer intermediário escrever o que
quisesse na ficha dos peixes.

**Por que a temperatura não é lida.** `stocks.TempMin` e
`stocks.TempMax` existem e seriam o caminho natural para `temp_min` e
`temp_max`. Para Carassius auratus, o kinguio, a FishBase registra
0 a 41 graus, que é a faixa de sobrevivência da espécie na natureza
somando as populações introduzidas no mundo. Gravado como faixa de
aquário, isso faria o motor de compatibilidade aprovar kinguio num
aquário de disco a 29 graus. O que se lê, no lugar, é `EnvTemp`, a
classificação de clima, que é categoria e não finge ser recomendação.

A licença é CC BY-NC 4.0: uso não comercial, com atribuição. Por isso
toda ficha preenchida por aqui sai com `fonte_dados` gravado.
"""

import io
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import httpx

VERSAO = "v24.07"
BASE = f"https://data.source.coop/cboettig/fishbase/fb/{VERSAO}/parquet/"
ATRIBUICAO = f"FishBase {VERSAO} (CC BY-NC 4.0)"
PAGINA = "https://www.fishbase.se/summary/{}.html"

TEMPO_LIMITE = 60.0

# Quantas vezes tentar baixar cada tabela antes de desistir.
TENTATIVAS = 2
ESPERA_ENTRE_TENTATIVAS = 2.0

# Categorias de clima da FishBase, traduzidas para o padrão dos outros
# enumerados da tabela especie.
CLIMAS = {
    "tropical": "tropical",
    "subtropical": "subtropical",
    "temperate": "temperado",
    "boreal": "boreal",
    "polar": "polar",
    "high altitude": "altitude",
    "deep-water": "agua_profunda",
}

# Só estas colunas são lidas de cada tabela. O parquet é colunar, então
# projetar aqui é o que evita carregar as 102 colunas de `species` e as
# 123 de `stocks` na memória de um servidor de 512 MB.
COLUNAS_ESPECIE = ["SpecCode", "Genus", "Species", "FBname", "Fresh",
                   "Brack", "Saltwater", "Length"]
COLUNAS_ESTOQUE = ["SpecCode", "Level", "EnvTemp", "pHMin", "pHMax",
                   "dHMin", "dHMax"]


class Indisponivel(Exception):
    """A FishBase não respondeu.

    Mesmo contrato do `enriquecimento`: a importação trata isto como
    "não deu para buscar agora" e segue gravando o que já tem, em vez
    de falhar inteira por causa de uma rede ruim.
    """


# `slots=True` tira o dicionário de atributos de cada instância. São 35
# mil instâncias vivas no índice, e o ganho medido foi modesto, de
# 27,2 MB para 25,6 MB: aqui o peso está nas cadeias de texto, e não na
# estrutura dos objetos. Fica porque não custa nada.
#
# O índice inteiro ocupa esses 25,6 MB, com pico de 58 MB durante a
# carga, medido com tracemalloc. Cabe nos 512 MB do plano gratuito do
# Render com folga, e foi medido antes de publicar justamente para não
# descobrir isso com usuário na frente.
@dataclass(slots=True)
class Ficha:
    """O que a FishBase sabe e cabe na ficha do AquaSys."""

    spec_code: int
    nome_cientifico: str
    # Nome popular que a FishBase publica, em inglês. Serve de ponto de
    # partida quando a lista da loja trouxe só o nome científico:
    # "Neon tetra" na tela é melhor que "Paracheirodon innesi".
    nome_popular: Optional[str] = None
    tamanho_adulto_cm: Optional[float] = None
    tipo_agua: Optional[str] = None
    ph_min: Optional[float] = None
    ph_max: Optional[float] = None
    dgh_min: Optional[float] = None
    dgh_max: Optional[float] = None
    clima: Optional[str] = None

    @property
    def fonte(self) -> str:
        return ATRIBUICAO

    @property
    def pagina(self) -> str:
        """Endereço da espécie na FishBase, para o crédito clicável."""
        return PAGINA.format(self.spec_code)

    def preencher(self, especie) -> list:
        """Copia para a espécie só os campos que ainda estão vazios.

        Nunca sobrescreve: se alguém da loja já digitou o porte, o que
        veio de fora não vale mais do que isso. Devolve a lista dos
        campos que foram realmente preenchidos.
        """
        preenchidos = []
        for campo in ("tamanho_adulto_cm", "tipo_agua", "ph_min", "ph_max",
                      "dgh_min", "dgh_max", "clima"):
            valor = getattr(self, campo)
            if valor is not None and getattr(especie, campo, None) is None:
                setattr(especie, campo, valor)
                preenchidos.append(campo)

        if preenchidos:
            especie.fonte_dados = self.fonte
        return preenchidos


# ═══════════════════════════════════════════════════════
# CARGA DO SNAPSHOT
# ═══════════════════════════════════════════════════════
# O índice é montado uma vez por processo. São dois arquivos, somando
# cerca de 9 MB, e o resultado é um dicionário de nome científico para
# os poucos campos que interessam.
#
# Baixar o arquivo inteiro para depois projetar as colunas é desperdício
# de banda, e é deliberado: a alternativa é leitura por faixas de bytes
# sobre HTTP, que exigiria duckdb com a extensão httpfs baixada em tempo
# de execução. Num servidor com saída de rede restrita isso falha de um
# jeito difícil de diagnosticar; 9 MB uma vez por processo, não.
_indice: Optional[Dict[str, Ficha]] = None
_trava = threading.Lock()


def _baixar(tabela: str, colunas: list) -> list:
    import pyarrow.parquet as pq

    # Duas tentativas. São dois arquivos de alguns megabytes, e queda no
    # meio do segundo joga fora o primeiro: a importação perderia o
    # preenchimento inteiro por causa de um soluço de rede. Aconteceu em
    # teste, com EOF no meio do TLS.
    ultimo = None
    for tentativa in range(TENTATIVAS):
        if tentativa:
            time.sleep(ESPERA_ENTRE_TENTATIVAS)
        try:
            resposta = httpx.get(BASE + tabela + ".parquet",
                                 timeout=TEMPO_LIMITE, follow_redirects=True)
            resposta.raise_for_status()
            break
        except httpx.HTTPError as erro:
            ultimo = erro
    else:
        raise Indisponivel(
            f"Falha ao buscar {tabela} em {TENTATIVAS} tentativas: {ultimo}"
        ) from ultimo

    try:
        tabela_arrow = pq.read_table(io.BytesIO(resposta.content),
                                     columns=colunas)
    except Exception as erro:                       # arquivo corrompido
        raise Indisponivel(f"{tabela} veio ilegível: {erro}") from erro

    return tabela_arrow.to_pylist()


def _arredondar(valor) -> Optional[float]:
    """Corta o ruído de precisão do parquet.

    Os números vêm em float de 32 bits, e o pH máximo da molinésia
    chegava como 8.19999980926514. Gravado assim, apareceria desse
    jeito na ficha. Duas casas bastam para pH, dureza e centímetros.
    """
    if valor is None:
        return None
    return round(float(valor), 2)


def _agua(fresh, brack, salt) -> Optional[str]:
    """Traduz os três sinalizadores da FishBase para o enumerado daqui.

    A coluna `tipo_agua` guarda um valor só, e há espécie marcada em
    mais de um ambiente. A ordem é a do aquarismo ornamental, que é o
    uso do AquaSys: doce ganha de tudo, e marinho ganha de salobra.

    Essa segunda parte foi medida antes de ser escolhida. Na v24.07,
    1460 espécies são salobra e marinha sem serem de doce, contra 97
    exclusivamente salobras. Aquelas 1460 são peixes de recife e de
    estuário que o aquarista mantém em aquário marinho, e o cavalo-
    marinho `Hippocampus reidi` é uma delas. Chamando-as de salobras, o
    motor de compatibilidade as recusaria num aquário marinho, e a
    recusa por ambiente é impeditiva: não há como o usuário contornar.
    """
    if fresh:
        return "doce"
    if salt:
        return "marinho"
    if brack:
        return "salobra"
    return None


def _melhor_estoque(linhas: list) -> dict:
    """Escolhe entre os estoques de uma espécie.

    Quase toda espécie tem um só, mas 135 delas têm vários, uma linha
    por subespécie ou população, e o kinguio é uma dessas. A linha que
    descreve a espécie como um todo é a marcada `species in general`;
    as outras descrevem recortes geográficos e vêm quase sempre vazias.
    """
    for linha in linhas:
        if (linha.get("Level") or "").strip().lower() == "species in general":
            return linha
    return linhas[0] if linhas else {}


def _montar() -> Dict[str, Ficha]:
    especies = _baixar("species", COLUNAS_ESPECIE)
    estoques_brutos = _baixar("stocks", COLUNAS_ESTOQUE)

    por_codigo: Dict[int, list] = {}
    for linha in estoques_brutos:
        por_codigo.setdefault(linha["SpecCode"], []).append(linha)

    indice: Dict[str, Ficha] = {}
    for linha in especies:
        genero = (linha["Genus"] or "").strip()
        epiteto = (linha["Species"] or "").strip()
        if not genero or not epiteto:
            continue

        cientifico = f"{genero} {epiteto}"
        estoque = _melhor_estoque(por_codigo.get(linha["SpecCode"], []))

        indice[cientifico.lower()] = Ficha(
            spec_code=linha["SpecCode"],
            nome_cientifico=cientifico,
            nome_popular=(linha["FBname"] or "").strip() or None,
            tamanho_adulto_cm=_arredondar(linha["Length"]),
            tipo_agua=_agua(linha["Fresh"], linha["Brack"], linha["Saltwater"]),
            ph_min=_arredondar(estoque.get("pHMin")),
            ph_max=_arredondar(estoque.get("pHMax")),
            dgh_min=_arredondar(estoque.get("dHMin")),
            dgh_max=_arredondar(estoque.get("dHMax")),
            clima=CLIMAS.get((estoque.get("EnvTemp") or "").strip().lower()),
        )

    return indice


def carregar(forcar: bool = False) -> Dict[str, Ficha]:
    """Devolve o índice, montando-o na primeira chamada do processo."""
    global _indice
    with _trava:
        if _indice is None or forcar:
            _indice = _montar()
        return _indice


def esquecer() -> None:
    """Descarta o índice. Usado pelos testes."""
    global _indice
    with _trava:
        _indice = None


# ═══════════════════════════════════════════════════════
# CONSULTA
# ═══════════════════════════════════════════════════════
def consultar(nome_cientifico: Optional[str]) -> Optional[Ficha]:
    """Ficha da espécie, ou None se o nome não existe na FishBase.

    A busca é exata sobre gênero mais epíteto, em minúsculas. Não há
    busca aproximada de propósito: nome científico errado por uma letra
    costuma ser outra espécie, e aproximar aqui traria a ficha do peixe
    errado sem ninguém perceber.
    """
    if not nome_cientifico:
        return None

    chave = " ".join(nome_cientifico.strip().lower().split())
    if not chave:
        return None

    return carregar().get(chave)
