"""Tenta descobrir o nome científico a partir do nome popular.

Serve à importação da lista da loja: quando um nome não existe no
catálogo, vale a pena adiantar o que der antes de pedir que alguém
preencha a ficha à mão.

O que NÃO se faz aqui, e por quê
────────────────────────────────
Não se preenche porte, temperamento, cardume mínimo nem faixa de pH.
O motor de compatibilidade decide a partir desses campos se dois peixes
podem dividir o mesmo aquário, e não existe fonte pública confiável
para eles. Errar ali não devolve um dado torto na tela: mata peixe.

Por que a verificação é tão dura
────────────────────────────────
A busca da Wikipédia sempre devolve alguma coisa, com a mesma cara de
certeza. Medido com nomes reais de uma lista de estoque:

    Kinguio             -> Carassius auratus     certo
    Tetra Neon Negro    -> Paracheirodon innesi  ERRADO, é outro peixe
    Barbo Sumatra       -> Sus barbatus          ERRADO, é um javali
    Camarão Red Cherry  -> Noodles & Company     ERRADO, é um restaurante

Duas exigências derrubam os três erros e mantêm o acerto:

  1. o item precisa ser um táxon, isto é, ter nome científico
     declarado no Wikidata (P225). Derruba o restaurante;
  2. toda palavra do nome buscado precisa aparecer no título, no
     rótulo em português, nos apelidos ou no próprio nome científico.
     Derruba o javali e, principalmente, o "negro" que o Tetra Neon
     Negro perde ao virar Tetra-néon.

A regra também recusa acertos: "Acará Bandeira" resolve certo para
Pterophyllum scalare e mesmo assim é barrado, porque "bandeira" não
aparece em lugar nenhum do item. É o lado certo do erro: recusa custa
um preenchimento manual, aceite errado custa um conselho errado.
"""

import json
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

BUSCA = "https://pt.wikipedia.org/w/api.php"
ENTIDADE = "https://www.wikidata.org/wiki/Special:EntityData/%s.json"
TEMPO_LIMITE = 8
# A política de uso da Wikimedia pede identificação com forma de
# contato. Agente genérico é estrangulado primeiro.
AGENTE = ("AquaSys/1.0 (trabalho academico; "
          "https://github.com/Zampier21/Aquasys)")

# Intervalo mínimo entre pedidos, em segundos.
#
# Sem isto a importação de uma lista grande é cortada: medindo com 42
# nomes, a Wikipedia respondeu 429 a partir do décimo segundo, porque
# cada nome custa dois pedidos e eles saíam em rajada. O resto da lista
# vinha sem nome científico, e a loja não tinha como saber por quê.
INTERVALO = 0.6

# Uma única nova tentativa depois do 429, respeitando o Retry-After que
# vier. Insistir mais do que isso é cavar o próprio bloqueio.
ESPERA_MAXIMA = 5.0

# Palavras que não ajudam a identificar e que, exigidas, barrariam
# acertos: a loja escreve "Peixe Palhaço" e o item se chama "Palhaço".
VAZIAS = {"peixe", "de", "da", "do", "e", "com", "o", "a"}


class Indisponivel(Exception):
    """A fonte não respondeu. Não é o mesmo que não ter achado."""


@dataclass
class Sugestao:
    nome_cientifico: str
    titulo: str            # página que originou a sugestão
    qid: str               # item do Wikidata, para conferência humana


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", (texto or "").lower())
    limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
    so_letras = "".join(c if c.isalnum() else " " for c in limpo)
    return " ".join(so_letras.split())


_ultimo_pedido = 0.0
_trava_do_ritmo = threading.Lock()


def _esperar_a_vez() -> None:
    """Segura o pedido até o intervalo mínimo ter passado."""
    global _ultimo_pedido
    with _trava_do_ritmo:
        agora = time.monotonic()
        atraso = INTERVALO - (agora - _ultimo_pedido)
        if atraso > 0:
            time.sleep(atraso)
        _ultimo_pedido = time.monotonic()


def _buscar(url: str) -> dict:
    _esperar_a_vez()
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
        return json.loads(resposta.read())


def _pedir(url: str) -> dict:
    try:
        return _buscar(url)
    except urllib.error.HTTPError as erro:
        if erro.code != 429:
            raise Indisponivel(str(erro)) from erro

        # O servidor diz quanto esperar; quando não diz, o intervalo
        # dobrado serve de palpite.
        try:
            espera = float(erro.headers.get("Retry-After") or INTERVALO * 2)
        except (TypeError, ValueError):
            espera = INTERVALO * 2
        time.sleep(min(espera, ESPERA_MAXIMA))

        try:
            return _buscar(url)
        except (urllib.error.URLError, TimeoutError, ValueError) as outra:
            raise Indisponivel(f"limite de uso da fonte: {outra}") from outra
    except (urllib.error.URLError, TimeoutError, ValueError) as erro:
        raise Indisponivel(str(erro)) from erro


def _pagina(nome: str) -> Optional[tuple]:
    """Primeira página da busca em português, com o item do Wikidata."""
    url = BUSCA + "?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": nome, "gsrlimit": 1,
        "prop": "pageprops", "ppprop": "wikibase_item",
    })
    paginas = (_pedir(url).get("query") or {}).get("pages") or {}
    if not paginas:
        return None
    pagina = list(paginas.values())[0]
    qid = (pagina.get("pageprops") or {}).get("wikibase_item")
    return (pagina.get("title", ""), qid) if qid else None


def _vocabulario(entidade: dict, titulo: str, cientifico: str) -> set:
    """Tudo por que o item pode ser chamado, já normalizado."""
    palavras = set()
    for texto in (titulo, cientifico):
        palavras |= set(normalizar(texto).split())
    for idioma in ("pt", "pt-br"):
        rotulo = entidade.get("labels", {}).get(idioma)
        if rotulo:
            palavras |= set(normalizar(rotulo["value"]).split())
        for apelido in entidade.get("aliases", {}).get(idioma, []):
            palavras |= set(normalizar(apelido["value"]).split())
    return palavras


def sugerir(nome: str) -> Optional[Sugestao]:
    """Nome científico para o nome popular, ou None se não der para afirmar.

    Levanta Indisponivel quando a rede falha, para que a importação
    distinga "não achei" de "não consegui perguntar".
    """
    if not (nome or "").strip():
        return None

    achado = _pagina(nome)
    if achado is None:
        return None
    titulo, qid = achado

    entidade = _pedir(ENTIDADE % qid)["entities"][qid]
    reivindicacoes = entidade.get("claims", {})

    # 1. Precisa ser um táxon.
    if "P225" not in reivindicacoes:
        return None
    cientifico = reivindicacoes["P225"][0]["mainsnak"]["datavalue"]["value"]

    # 2. Nenhuma palavra do que a loja escreveu pode ficar sem respaldo.
    procuradas = {p for p in normalizar(nome).split() if p not in VAZIAS}
    if not procuradas:
        return None
    if procuradas - _vocabulario(entidade, titulo, cientifico):
        return None

    return Sugestao(nome_cientifico=cientifico, titulo=titulo, qid=qid)
