import hashlib
import io
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps

# ═══════════════════════════════════════════════════════
# FORMATO DE SAÍDA
# ═══════════════════════════════════════════════════════
LADO_MINIATURA = 192
MAIOR_LADO_COMPLETA = 900

# Largura que pedimos ao Commons. O servidor deles gera a miniatura, e
# é por isso que este número existe.
#
# Antes baixávamos o arquivo original, e isso derrubou o servidor com
# erro 502 durante um lote de fotos. Medindo os originais de seis
# espécies do catálogo: de 5 a 10 megapixels, arquivos de até 7 MB. O
# Pillow precisa de cerca de 29 MB só para abrir um de 10 MP, e faz
# cópias no caminho (girar pelo EXIF, achatar transparência,
# redimensionar). Num servidor de 512 MB que já carrega o índice da
# FishBase, uma foto grande basta para matar o processo.
#
# Pedir 1200 resolve na origem: chega um arquivo de algumas centenas de
# kilobytes, e é mais do que os 900 que o card usa.
LARGURA_PEDIDA = 1200

# Teto de segurança para imagem que venha de outro caminho, como a foto
# que a loja envia. 40 MP são cerca de 120 MB de bitmap, e nada que o
# AquaSys mostre precisa disso.
MAXIMO_DE_PIXELS = 40_000_000

QUALIDADE_COMPLETA = 85
QUALIDADE_MINIATURA = 82

MIME = "image/jpeg"


@dataclass(frozen=True)
class ImagemPronta:
    completa: bytes
    miniatura: bytes
    largura: int
    altura: int
    hash: str

    @property
    def resumo(self) -> str:
        return (
            f"{self.largura}x{self.altura}, "
            f"{len(self.completa) // 1024} KB + "
            f"{len(self.miniatura) // 1024} KB"
        )


class ImagemInvalida(Exception):
    """O arquivo baixado não é uma imagem que dê para usar."""


class FonteIndisponivel(Exception):
    """O Wikimedia recusou ou não respondeu.

    Diferente de não achar foto, e a diferença importa: "esta espécie
    não tem foto no acervo livre" manda a loja fotografar o peixe;
    "a fonte nos recusou" é problema nosso e passa com o tempo. Sem
    separar, a tela dizia a primeira coisa quando era a segunda.
    """


def preparar(bruto: bytes) -> ImagemPronta:
    try:
        original = Image.open(io.BytesIO(bruto))
    except Exception as erro:
        raise ImagemInvalida(f"não deu para abrir a imagem: {erro}") from erro

    # Conferido ANTES de `load()`, que é quem descomprime. Depois já
    # seria tarde: o estouro de memória acontece exatamente ali.
    largura, altura = original.size
    if largura * altura > MAXIMO_DE_PIXELS:
        raise ImagemInvalida(
            "imagem grande demais: %d x %d. O limite é %d megapixels."
            % (largura, altura, MAXIMO_DE_PIXELS // 1_000_000)
        )

    # Para JPEG, o `draft` manda o decodificador já entregar reduzido,
    # em vez de montar o bitmap inteiro para depois encolher. Não faz
    # nada nos outros formatos, e não atrapalha.
    original.draft("RGB", (MAIOR_LADO_COMPLETA, MAIOR_LADO_COMPLETA))

    try:
        original.load()
    except Exception as erro:
        raise ImagemInvalida(f"não deu para abrir a imagem: {erro}") from erro

    # Foto de celular guarda a orientação num campo à parte; sem isto,
    # metade das imagens sairia deitada.
    original = ImageOps.exif_transpose(original)

    # JPEG não tem transparência: sem achatar antes, PNG transparente
    # vira fundo preto.
    if original.mode in ("RGBA", "LA", "P"):
        original = original.convert("RGBA")
        fundo = Image.new("RGB", original.size, (255, 255, 255))
        fundo.paste(original, mask=original.split()[-1])
        original = fundo
    else:
        original = original.convert("RGB")

    completa = original.copy()
    completa.thumbnail(
        (MAIOR_LADO_COMPLETA, MAIOR_LADO_COMPLETA), Image.LANCZOS
    )

    miniatura = ImageOps.fit(
        original,
        (LADO_MINIATURA, LADO_MINIATURA),
        method=Image.LANCZOS,
        centering=(0.5, 0.5),
    )

    bytes_completa = _para_jpeg(completa, QUALIDADE_COMPLETA)
    bytes_miniatura = _para_jpeg(miniatura, QUALIDADE_MINIATURA)

    return ImagemPronta(
        completa=bytes_completa,
        miniatura=bytes_miniatura,
        largura=completa.width,
        altura=completa.height,
        hash=hashlib.sha256(bytes_completa).hexdigest(),
    )


def _para_jpeg(imagem: Image.Image, qualidade: int) -> bytes:
    saida = io.BytesIO()
    imagem.save(
        saida,
        format="JPEG",
        quality=qualidade,
        optimize=True,
        progressive=True,
    )
    return saida.getvalue()


# ═══════════════════════════════════════════════════════
# WIKIMEDIA COMMONS
# ═══════════════════════════════════════════════════════
WIKIPEDIA = "https://en.wikipedia.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"

# O Wikimedia pede que robôs se identifiquem e digam como falar com o
# responsável. Ponha seu e-mail aqui antes de rodar em volume — sem isso
# você é só mais um agente anônimo, e é quem eles limitam primeiro.
CONTATO = "https://github.com/Zampier21/Aquasys"
AGENTE = f"AquaSys/1.0 ({CONTATO}) python-httpx"

# Licenças aceitas. Commons é quase todo livre, mas "quase" não serve
# para um produto comercial: o que não bate com isto é descartado.
_LICENCAS_OK = re.compile(r"^(cc[\s-]|public domain|pd|cc0)", re.IGNORECASE)

# Arquivo de som, vídeo ou diagrama não serve de foto de peixe.
_EXTENSOES_OK = (".jpg", ".jpeg", ".png", ".webp")


def _e_imagem(url_ou_titulo: str) -> bool:
    """
    Confere a extensão olhando só o caminho.

    O Commons devolve a URL com rastreio pendurado no fim
    (`...jpg?utm_source=commons.wikimedia.org&...`), então comparar a
    string inteira reprovava toda foto — que foi exatamente o que
    aconteceu na primeira rodada: oito espécies, oito "nada encontrado",
    com a licença certa e a imagem certa do outro lado.
    """
    caminho = urlparse(url_ou_titulo).path or url_ou_titulo
    return caminho.lower().endswith(_EXTENSOES_OK)

# Intervalo mínimo entre duas chamadas ao Wikimedia.
#
# Não é excesso de zelo: sem isto o script disparava duas requisições por
# espécie sem pausa nenhuma e o Wikimedia devolvia 429 já na primeira,
# derrubando o lote inteiro. Popular o catálogo é coisa de rodar uma vez;
# ir devagar custa minutos e evita virar tráfego abusivo.
INTERVALO_MINIMO = 1.0
TENTATIVAS = 4

_ultimo_pedido = 0.0


def _get(
    cliente: httpx.Client, url: str, params: Optional[dict] = None
) -> httpx.Response:
    """
    GET no Wikimedia respeitando o ritmo pedido por eles.

    Em 429 (rápido demais) ou 503 (ocupado) espera e tenta de novo,
    honrando o `Retry-After` quando ele vem.

    Todo acesso ao Wikimedia passa por aqui, inclusive o download da foto
    em si. Deixar o download de fora foi um erro real: as consultas iam
    no ritmo certo, o arquivo ia a toda, e três das oito espécies
    voltaram com 429 na hora de baixar a imagem que já tinha sido
    encontrada.
    """
    global _ultimo_pedido

    espera = 2.0
    for tentativa in range(TENTATIVAS):
        folga = INTERVALO_MINIMO - (time.monotonic() - _ultimo_pedido)
        if folga > 0:
            time.sleep(folga)

        resposta = cliente.get(url, params=params)
        _ultimo_pedido = time.monotonic()

        if resposta.status_code not in (429, 503):
            resposta.raise_for_status()
            return resposta

        if tentativa == TENTATIVAS - 1:
            resposta.raise_for_status()

        cabecalho = resposta.headers.get("retry-after")
        time.sleep(float(cabecalho) if cabecalho and cabecalho.isdigit() else espera)
        espera *= 2

    raise RuntimeError("inalcançável: a última volta sempre levanta")


def _pedir(cliente: httpx.Client, url: str, params: dict) -> dict:
    return _get(cliente, url, params).json()


@dataclass(frozen=True)
class FotoEncontrada:
    url: str
    fonte: str
    autor: Optional[str]
    licenca: Optional[str]
    licenca_url: Optional[str]


def _cliente() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": AGENTE},
        timeout=30.0,
        follow_redirects=True,
    )


def _limpar_html(texto: Optional[str]) -> Optional[str]:
    """O campo de autor vem como HTML — às vezes um link inteiro."""
    if not texto:
        return None
    limpo = re.sub(r"<[^>]+>", "", texto)
    limpo = re.sub(r"\s+", " ", limpo).strip()
    return limpo[:300] or None


def _extrair_credito(extmetadata: dict, titulo_arquivo: str) -> Optional[FotoEncontrada]:
    """Lê autor e licença do bloco de metadados do Commons."""
    def campo(nome):
        valor = extmetadata.get(nome, {}).get("value")
        return _limpar_html(valor) if isinstance(valor, str) else None

    licenca = campo("LicenseShortName")
    if licenca and not _LICENCAS_OK.match(licenca):
        return None

    return FotoEncontrada(
        url="",  # preenchido por quem chamou
        fonte=f"https://commons.wikimedia.org/wiki/{titulo_arquivo.replace(' ', '_')}",
        autor=campo("Artist"),
        licenca=licenca,
        licenca_url=extmetadata.get("LicenseUrl", {}).get("value"),
    )


def _detalhes_do_arquivo(cliente: httpx.Client, titulo: str) -> Optional[FotoEncontrada]:
    """Pega URL e crédito de um arquivo do Commons pelo título."""
    dados = _pedir(cliente, COMMONS, {
        "action": "query",
        "titles": titulo,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        # Faz o Commons devolver também `thumburl`, já reduzida no
        # servidor deles. Ver LARGURA_PEDIDA.
        "iiurlwidth": LARGURA_PEDIDA,
        "format": "json",
    })

    paginas = dados.get("query", {}).get("pages", {})
    for pagina in paginas.values():
        infos = pagina.get("imageinfo")
        if not infos:
            continue

        info = infos[0]
        # `thumburl` é a versão reduzida pelo Commons; `url` é o
        # original, que pode ter 10 megapixels. A reduzida vem primeiro,
        # e o original fica de reserva para o caso raro de o Commons não
        # conseguir gerar miniatura (alguns formatos antigos).
        url = info.get("thumburl") or info.get("url", "")
        if not _e_imagem(info.get("url", "")):
            continue

        credito = _extrair_credito(info.get("extmetadata", {}), titulo)
        if credito is None:
            continue  # licença que não serve

        return FotoEncontrada(
            url=url,
            fonte=credito.fonte,
            autor=credito.autor,
            licenca=credito.licenca,
            licenca_url=credito.licenca_url,
        )

    return None


def _foto_do_artigo(cliente: httpx.Client, titulo: str) -> Optional[FotoEncontrada]:
    """
    Imagem principal do artigo da Wikipédia sobre a espécie.

    É a melhor fonte: alguém já escolheu, entre todas as fotos daquele
    peixe, a que representa a espécie. A busca crua do Commons devolve
    desde aquário de loja até desenho científico.
    """
    dados = _pedir(cliente, WIKIPEDIA, {
        "action": "query",
        "titles": titulo,
        "prop": "pageimages",
        "piprop": "name",
        "redirects": 1,
        "format": "json",
    })

    paginas = dados.get("query", {}).get("pages", {})
    for pagina in paginas.values():
        nome = pagina.get("pageimage")
        if nome:
            return _detalhes_do_arquivo(cliente, f"File:{nome}")

    return None


def _busca_no_commons(cliente: httpx.Client, termo: str) -> Optional[FotoEncontrada]:
    """Rede de segurança: espécie sem artigo próprio na Wikipédia."""
    dados = _pedir(cliente, COMMONS, {
        "action": "query",
        "generator": "search",
        "gsrsearch": termo,
        "gsrnamespace": 6,          # 6 = arquivo
        "gsrlimit": 5,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": LARGURA_PEDIDA,
        "format": "json",
    })

    paginas = dados.get("query", {}).get("pages", {})
    # A busca não vem ordenada; `index` é a posição de relevância.
    for pagina in sorted(paginas.values(), key=lambda p: p.get("index", 99)):
        titulo = pagina.get("title", "")
        if not _e_imagem(titulo):
            continue

        encontrada = _detalhes_do_arquivo(cliente, titulo)
        if encontrada:
            return encontrada

    return None


def buscar(
    nome_cientifico: Optional[str],
    nome_comum: Optional[str] = None,
    cliente: Optional[httpx.Client] = None,
) -> Optional[FotoEncontrada]:
    """
    Procura uma foto livre da espécie, do mais confiável para o menos.

    O nome científico vem primeiro porque é único: "Betta" acha de tudo,
    "Betta splendens" acha o peixe certo.
    """
    proprio = cliente is None
    cliente = cliente or _cliente()

    try:
        tentativas = []
        if nome_cientifico:
            tentativas.append(("artigo", nome_cientifico))
        if nome_cientifico:
            tentativas.append(("commons", nome_cientifico))
        if nome_comum:
            tentativas.append(("commons", f"{nome_comum} fish"))

        for modo, termo in tentativas:
            achado = (
                _foto_do_artigo(cliente, termo) if modo == "artigo"
                else _busca_no_commons(cliente, termo)
            )
            if achado:
                return achado

        return None
    finally:
        if proprio:
            cliente.close()


def baixar(url: str, cliente: Optional[httpx.Client] = None) -> bytes:
    """Baixa o arquivo da foto."""
    proprio = cliente is None
    cliente = cliente or _cliente()
    try:
        return _get(cliente, url).content
    finally:
        if proprio:
            cliente.close()


# ═══════════════════════════════════════════════════════
# CICLO COMPLETO: ACHAR, BAIXAR, PREPARAR E GRAVAR
# ═══════════════════════════════════════════════════════
# Isto morava dentro do `baixar_imagens.py`, como função privada, e era
# o motivo de a importação pelo aplicativo criar espécie sem foto: o
# caminho de gravar só existia no script. Agora mora aqui, e os dois
# usam o mesmo.


def obter(
    nome_cientifico: Optional[str],
    nome_comum: Optional[str] = None,
    cliente: Optional[httpx.Client] = None,
) -> Optional[tuple]:
    """Devolve (ImagemPronta, FotoEncontrada), ou None se não achou.

    Não toca no banco de propósito: quem chama decide o que fazer com o
    resultado, e assim esta parte continua testável sem banco.
    """
    try:
        achado = buscar(nome_cientifico, nome_comum, cliente=cliente)
    except httpx.HTTPError as erro:
        # Recusa ou queda do Wikimedia não é "esta espécie não tem
        # foto": é a fonte fora de alcance, e quem chama precisa saber
        # da diferença para não mandar a loja fotografar à toa.
        raise FonteIndisponivel(str(erro)) from erro

    if achado is None:
        return None

    try:
        bruto = baixar(achado.url, cliente=cliente)
    except httpx.HTTPError as erro:
        raise FonteIndisponivel(str(erro)) from erro

    try:
        return preparar(bruto), achado
    except ImagemInvalida:
        # Arquivo encontrado mas ilegível é como não ter achado: a
        # fonte respondeu, o conteúdo é que não serve.
        return None


def gravar(db, especie, pronta: "ImagemPronta", achado) -> None:
    """Insere ou substitui a linha de imagem daquela espécie.

    O crédito é gravado junto, e não é enfeite: as fotos do Wikimedia
    Commons vêm sob licenças que exigem atribuição, e é por estes
    campos que o aplicativo mostra o autor embaixo da foto.
    """
    from app.models.especie import EspecieImagem

    linha = (
        db.query(EspecieImagem)
        .filter(EspecieImagem.especie_id == especie.id)
        .first()
    )
    if linha is None:
        linha = EspecieImagem(especie_id=especie.id)
        db.add(linha)

    linha.miniatura = pronta.miniatura
    linha.completa = pronta.completa
    linha.mime = MIME
    linha.hash = pronta.hash
    linha.largura = pronta.largura
    linha.altura = pronta.altura
    linha.bytes_miniatura = len(pronta.miniatura)
    linha.bytes_completa = len(pronta.completa)

    linha.fonte = achado.fonte if achado else None
    linha.autor = achado.autor if achado else None
    linha.licenca = achado.licenca if achado else None
    linha.licenca_url = achado.licenca_url if achado else None
