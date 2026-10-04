"""Lê uma lista de peixes em CSV e casa cada nome com o catálogo.

A loja exporta do seu sistema de estoque uma lista com os peixes que
vende e sobe o arquivo. Aqui não se cria espécie nenhuma: o serviço só
confere o que já existe no catálogo e devolve um relatório com o que
encontrou, o que ficou ambíguo e o que não existe.

Criar a espécie automaticamente a partir do nome seria o passo seguinte,
e não é feito de propósito. O motor de compatibilidade decide se dois
peixes podem dividir o mesmo aquário a partir de porte, territorialidade
e cardume mínimo, e não existe fonte pública confiável para esses três
campos. Preencher por adivinhação daria conselho errado sobre animal
vivo.
"""

import csv
import difflib
import io
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.especie import Especie, LojaEspecie
from app.services import enriquecimento, fishbase

# Uma lista de estoque de loja tem dezenas de linhas, não milhares. Os
# tetos existem para que um arquivo errado (um banco de dados inteiro,
# um binário renomeado) seja recusado com mensagem, e não processado.
LIMITE_BYTES = 512 * 1024
LIMITE_NOMES = 500

# Cabeçalhos que costumam nomear a coluna do peixe nos sistemas de
# estoque. Comparados já normalizados.
CABECALHOS = {
    "nome", "nomes", "peixe", "peixes", "especie", "especies",
    "nome comum", "nome_comum", "nome do peixe", "descricao",
    "produto", "item",
}

# Codificações na ordem em que vale a pena tentar. O utf-8-sig vem antes
# do utf-8 porque o Excel brasileiro grava o marcador de ordem de bytes,
# e sem tratá-lo o primeiro nome viria com lixo na frente.
CODIFICACOES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class ArquivoInvalido(Exception):
    pass


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e com os espaços colapsados."""
    sem_acento = unicodedata.normalize("NFKD", (texto or "").lower().strip())
    limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(limpo.split())


# ═══════════════════════════════════════════════════════
# LEITURA DO ARQUIVO
# ═══════════════════════════════════════════════════════
def _decodificar(bruto: bytes) -> str:
    for codificacao in CODIFICACOES:
        try:
            return bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
    raise ArquivoInvalido(
        "Não foi possível ler o arquivo. Salve como CSV em UTF-8 e tente "
        "de novo."
    )


def _separador(primeira_linha: str) -> str:
    """Escolhe o separador pelo que mais aparece fora de aspas.

    O csv.Sniffer erra em arquivo de uma coluna só, que é o caso mais
    comum aqui: uma lista de nomes, um por linha. Contar é mais previsível.
    """
    candidatos = {";": 0, ",": 0, "\t": 0}
    dentro_de_aspas = False
    for caractere in primeira_linha:
        if caractere == '"':
            dentro_de_aspas = not dentro_de_aspas
        elif not dentro_de_aspas and caractere in candidatos:
            candidatos[caractere] += 1
    melhor = max(candidatos, key=lambda c: candidatos[c])
    return melhor if candidatos[melhor] else ","


def _coluna_dos_nomes(cabecalho: List[str]) -> Optional[int]:
    """Índice da coluna de nome, quando a primeira linha for cabeçalho."""
    for i, celula in enumerate(cabecalho):
        if normalizar(celula) in CABECALHOS:
            return i
    return None


def ler_nomes(bruto: bytes) -> List[str]:
    """Extrai a lista de nomes do arquivo, na ordem em que aparecem.

    Aceita CSV com ou sem cabeçalho, separado por vírgula, ponto e vírgula
    ou tabulação, e também um arquivo de texto com um nome por linha.
    """
    if not bruto.strip():
        raise ArquivoInvalido("O arquivo está vazio.")
    if len(bruto) > LIMITE_BYTES:
        raise ArquivoInvalido(
            "O arquivo tem mais de %d KB. Envie apenas a lista de peixes."
            % (LIMITE_BYTES // 1024)
        )

    texto = _decodificar(bruto)
    # O \x00 denuncia binário renomeado para .csv, que decodificaria em
    # latin-1 sem erro nenhum e viraria uma lista de lixo.
    if "\x00" in texto:
        raise ArquivoInvalido("O arquivo não é um CSV de texto.")

    linhas = [l for l in texto.splitlines() if l.strip()]
    if not linhas:
        raise ArquivoInvalido("O arquivo está vazio.")

    leitor = csv.reader(linhas, delimiter=_separador(linhas[0]))
    registros = [r for r in leitor if any(c.strip() for c in r)]
    if not registros:
        raise ArquivoInvalido("O arquivo está vazio.")

    coluna = _coluna_dos_nomes(registros[0])
    if coluna is None:
        coluna = 0                      # sem cabeçalho: a primeira coluna
    else:
        registros = registros[1:]       # com cabeçalho: descarta a linha

    nomes = []
    for registro in registros:
        if coluna < len(registro) and registro[coluna].strip():
            nomes.append(registro[coluna].strip())
    if not nomes:
        raise ArquivoInvalido("Nenhum nome de peixe foi encontrado no arquivo.")
    if len(nomes) > LIMITE_NOMES:
        raise ArquivoInvalido(
            "A lista tem %d linhas, acima do limite de %d."
            % (len(nomes), LIMITE_NOMES)
        )
    return nomes


# ═══════════════════════════════════════════════════════
# CASAMENTO COM O CATÁLOGO
# ═══════════════════════════════════════════════════════
@dataclass
class Casamento:
    linha: int
    nome_lido: str
    vezes: int
    situacao: str                      # encontrado | ambiguo | nao_encontrado
    como: Optional[str] = None         # como foi encontrado
    especie: Optional[Especie] = None
    candidatos: List[Especie] = field(default_factory=list)
    sugestoes: List[str] = field(default_factory=list)


def _raiz(especie: Especie):
    """Id da espécie-base, ou o próprio id quando já for a base."""
    return getattr(especie, "variante_de_id", None) or especie.id


def _resolver_familia(especies: List[Especie]) -> List[Especie]:
    """Colapsa cada família de variedades na sua espécie-base.

    A variedade herda os nomes populares da base, então "escalar" casa ao
    mesmo tempo com o Acará Bandeira e com as sete variedades dele. Isso
    não é ambiguidade de verdade: quem escreveu "escalar" quis dizer a
    espécie, e a base é a resposta.

    Quando sobram famílias diferentes, a ambiguidade é real, mas a
    resposta continua sendo por espécie: "Acará" pergunta se é bandeira
    ou disco, e não qual das treze linhas do catálogo.
    """
    if len(especies) < 2:
        return especies

    por_familia: dict = {}
    for especie in especies:
        por_familia.setdefault(_raiz(especie), []).append(especie)

    reduzido = []
    for membros in por_familia.values():
        bases = [m for m in membros
                 if getattr(m, "variante_de_id", None) is None]
        reduzido.extend(bases if len(bases) == 1 else membros)
    return reduzido


def _chaves(especie: Especie):
    """Todos os nomes pelos quais a espécie pode ser escrita na lista."""
    brutos = [especie.nome_comum, especie.nome_cientifico]
    for alternativo in (especie.nomes_alternativos or "").split(","):
        brutos.append(alternativo)
    return {normalizar(b): b for b in brutos if b and normalizar(b)}


def casar(nomes: List[str], db: Session, dono=None) -> List[Casamento]:
    """Procura cada nome no catálogo, do mais exato ao mais tolerante.

    O catálogo inteiro é carregado de uma vez. São dezenas de linhas, e
    fazer uma consulta por nome da lista multiplicaria idas ao banco sem
    necessidade; em memória ainda dá para sugerir correção de digitação.
    """
    catalogo = _catalogo_visivel(db, dono)

    # chave exata -> espécies que atendem por ela
    por_chave: dict = {}
    for especie in catalogo:
        for chave in _chaves(especie):
            por_chave.setdefault(chave, []).append(especie)

    # texto de busca por espécie, para o casamento por palavras soltas
    texto_de = {
        e.id: normalizar(
            " ".join(filter(None, [e.nome_comum, e.nome_cientifico,
                                   e.nomes_alternativos]))
        )
        for e in catalogo
    }
    nome_por_normalizado = {normalizar(e.nome_comum): e.nome_comum
                            for e in catalogo}

    # Nome repetido na planilha vira uma linha só, com a contagem.
    vistos: dict = {}
    ordem: List[str] = []
    for i, nome in enumerate(nomes, start=1):
        chave = normalizar(nome)
        if not chave:
            continue
        if chave in vistos:
            vistos[chave]["vezes"] += 1
            continue
        vistos[chave] = {"linha": i, "nome": nome, "vezes": 1}
        ordem.append(chave)

    resultado = []
    for chave in ordem:
        dados = vistos[chave]
        base = Casamento(
            linha=dados["linha"],
            nome_lido=dados["nome"],
            vezes=dados["vezes"],
            situacao="nao_encontrado",
        )

        exatos = _resolver_familia(por_chave.get(chave, []))
        if len(exatos) == 1:
            base.situacao = "encontrado"
            base.especie = exatos[0]
            base.como = (
                "nome do catálogo"
                if normalizar(exatos[0].nome_comum) == chave
                else "outro nome da mesma espécie"
            )
        elif len(exatos) > 1:
            base.situacao = "ambiguo"
            base.candidatos = exatos
        else:
            # Sem acerto exato, exige-se que todas as palavras do nome
            # apareçam em algum dos nomes da espécie. "acara" sozinho traz
            # bandeira e disco, e o resultado é ambíguo, não um palpite.
            palavras = chave.split()
            parciais = _resolver_familia([
                e for e in catalogo
                if all(p in texto_de[e.id] for p in palavras)
            ])
            if len(parciais) == 1:
                base.situacao = "encontrado"
                base.especie = parciais[0]
                base.como = "aproximação pelo nome"
            elif len(parciais) > 1:
                base.situacao = "ambiguo"
                base.candidatos = parciais
            else:
                base.sugestoes = [
                    nome_por_normalizado[p]
                    for p in difflib.get_close_matches(
                        chave, list(nome_por_normalizado), n=3, cutoff=0.6
                    )
                ]
        resultado.append(base)

    return resultado


# ═══════════════════════════════════════════════════════
# GRAVAÇÃO
# ═══════════════════════════════════════════════════════
def _catalogo_visivel(db: Session, dono) -> List[Especie]:
    """O catálogo curado mais o rascunho da própria loja.

    Espécie com dono é rascunho de quem a importou: existe para aquela
    loja e para os clientes dela, e não para as concorrentes.
    """
    consulta = db.query(Especie).filter(Especie.ativo.is_(True))
    if dono is None:
        consulta = consulta.filter(Especie.dono_id.is_(None))
    else:
        consulta = consulta.filter(
            (Especie.dono_id.is_(None)) | (Especie.dono_id == dono.id)
        )
    return consulta.order_by(Especie.nome_comum).all()


def _ja_tem(db: Session, dono, especie_id) -> bool:
    return (
        db.query(LojaEspecie)
        .filter(LojaEspecie.dono_id == dono.id,
                LojaEspecie.especie_id == especie_id)
        .first()
        is not None
    )


def _vincular(db: Session, dono, especie: Especie, nome_lido: str) -> bool:
    """Registra que a loja tem a espécie. Devolve se era novidade."""
    if _ja_tem(db, dono, especie.id):
        return False
    db.add(LojaEspecie(
        dono_id=dono.id, especie_id=especie.id, nome_na_lista=nome_lido
    ))
    return True


def _por_cientifico(db: Session, dono, cientifico: str) -> Optional[Especie]:
    return (
        db.query(Especie)
        .filter(
            Especie.ativo.is_(True),
            Especie.variante_de_id.is_(None),
            func.lower(Especie.nome_cientifico) == cientifico.lower(),
            (Especie.dono_id.is_(None)) | (Especie.dono_id == dono.id),
        )
        .first()
    )


def aplicar(casados: List[Casamento], db: Session, dono, buscar=True) -> dict:
    """Grava a lista: vincula o que casou e cria rascunho do que faltou.

    O ambíguo fica de fora de propósito. "Acará" pode ser bandeira ou
    disco, e escolher por conta própria colocaria no estoque da loja um
    peixe que ela não vende.

    A espécie criada aqui nasce com `revisada=False`: o nome científico
    pode ter vindo de uma sugestão automática, e porte, temperamento e
    faixas continuam vazios. Quem decide se ela está boa é gente.
    """
    resumo = {
        "vinculados": 0,      # já existiam no catálogo e entraram no estoque
        "criados": 0,         # viraram rascunho da loja
        "com_cientifico": 0,  # dos criados, quantos ganharam nome científico
        "ja_estavam": 0,      # já constavam do estoque de antes
        "ignorados": 0,       # ambíguos, que exigem decisão da loja
        "sem_busca": False,   # a fonte externa não respondeu
        "com_ficha": 0,       # dos criados, quantos a FishBase preencheu
        "sem_fishbase": False,  # a FishBase não respondeu
    }

    for caso in casados:
        if caso.situacao == "ambiguo":
            resumo["ignorados"] += 1
            continue

        if caso.situacao == "encontrado":
            novo = _vincular(db, dono, caso.especie, caso.nome_lido)
            resumo["vinculados" if novo else "ja_estavam"] += 1
            continue

        # ─── Não existe no catálogo: vira rascunho da loja ───
        cientifico = None
        ficha = None
        veio_do_cientifico = False

        if buscar:
            # A lista pode já trazer o nome científico, e aí não há nada
            # a adivinhar: a própria FishBase diz se o nome existe nela.
            # Esse caminho é melhor que o outro em tudo, porque não
            # depende de busca por nome popular, que erra, nem da
            # Wikipedia, que estrangula lista grande.
            if not resumo["sem_fishbase"]:
                try:
                    ficha = fishbase.consultar(caso.nome_lido)
                except fishbase.Indisponivel:
                    resumo["sem_fishbase"] = True

            if ficha is not None:
                cientifico = ficha.nome_cientifico
                veio_do_cientifico = True
            else:
                try:
                    sugestao = enriquecimento.sugerir(caso.nome_lido)
                    cientifico = sugestao.nome_cientifico if sugestao else None
                except enriquecimento.Indisponivel:
                    resumo["sem_busca"] = True

        # A sugestão pode apontar para algo que o catálogo já tem sob
        # outro nome popular. Vincular é melhor do que duplicar.
        if cientifico:
            existente = _por_cientifico(db, dono, cientifico)
            if existente is not None:
                novo = _vincular(db, dono, existente, caso.nome_lido)
                resumo["vinculados" if novo else "ja_estavam"] += 1
                caso.situacao = "encontrado"
                caso.especie = existente
                caso.como = "nome científico descoberto na busca"
                continue

        especie = Especie(
            nome_comum=caso.nome_lido,
            nome_cientifico=cientifico,
            dono_id=dono.id,
            revisada=False,
            ativo=True,
        )
        db.add(especie)
        db.flush()               # precisa do id para o vínculo

        # Com o nome científico em mão, a FishBase preenche o que é
        # medida: porte, tipo de água, pH, dureza e clima. Temperamento,
        # cardume e a faixa de temperatura em graus continuam vazios, e
        # é por isso que `revisada` segue falso mesmo quando isto dá
        # certo. Ver app/services/fishbase.py.
        campos = []
        if ficha is None and cientifico and not resumo["sem_fishbase"]:
            try:
                ficha = fishbase.consultar(cientifico)
            except fishbase.Indisponivel:
                # Uma falha vale para a lista inteira: a primeira
                # consulta é que baixa o snapshot, e insistir a cada
                # nome tentaria baixar nove megabytes por peixe.
                resumo["sem_fishbase"] = True

        if ficha is not None:
            campos = ficha.preencher(especie)
            # Quando a lista trouxe o nome científico, ele ficou como
            # nome comum, e "Paracheirodon innesi" na aba de peixes do
            # aquarista não é nome de peixe. O nome popular da FishBase
            # é melhor ponto de partida, e a loja renomeia na revisão.
            # O nome como veio na lista fica guardado em
            # `loja_especie.nome_na_lista`, que é por ele que o lojista
            # reconhece o item.
            if veio_do_cientifico and ficha.nome_popular:
                especie.nome_comum = ficha.nome_popular[:100]

        _vincular(db, dono, especie, caso.nome_lido)
        resumo["criados"] += 1
        if cientifico:
            resumo["com_cientifico"] += 1
        if campos:
            resumo["com_ficha"] += 1

        caso.situacao = "criado"
        caso.especie = especie
        if campos and veio_do_cientifico:
            caso.como = (
                "nome científico reconhecido na FishBase, com %d campo(s) "
                "preenchidos" % len(campos)
            )
        elif campos:
            caso.como = (
                "criado como %s, com %d campo(s) da FishBase"
                % (cientifico, len(campos))
            )
        elif cientifico:
            caso.como = "criado com nome científico %s" % cientifico
        else:
            caso.como = "criado só com o nome, ficha a preencher"

    db.commit()
    return resumo
