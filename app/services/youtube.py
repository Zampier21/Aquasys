import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional

OEMBED = "https://www.youtube.com/oembed"
FEED_PLAYLIST = "https://www.youtube.com/feeds/videos.xml"
LIMITE_DO_FEED = 15
API_PLAYLIST_ITEMS = "https://www.googleapis.com/youtube/v3/playlistItems"
PAGINA_API = 50
TIMEOUT_SEGUNDOS = 8

# Um id de vídeo do YouTube tem 11 caracteres de [A-Za-z0-9_-].
_ID_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")

_PADROES = [
    re.compile(r"[?&]v=([A-Za-z0-9_-]{11})"),
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"/embed/([A-Za-z0-9_-]{11})"),
    re.compile(r"/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"/live/([A-Za-z0-9_-]{11})"),
]


# Id de playlist: PL..., UU..., FL..., OL...
_ID_PLAYLIST = re.compile(r"[?&]list=([A-Za-z0-9_-]{12,})")

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


class VideoInvalido(Exception):
    """URL não é de um vídeo do YouTube, ou o vídeo não existe."""


class PlaylistInvalida(Exception):
    """URL não tem playlist, ou a playlist é privada/inexistente."""


def extrair_id(url_ou_id: str) -> Optional[str]:
    """
    Aceita a URL colada em qualquer formato — ou o id puro.

    Devolve o id de 11 caracteres, ou None se não reconhecer.
    """
    texto = (url_ou_id or "").strip()
    if not texto:
        return None

    # Já veio só o id.
    if _ID_VIDEO.match(texto):
        return texto

    for padrao in _PADROES:
        achado = padrao.search(texto)
        if achado:
            return achado.group(1)

    return None


def buscar_metadados(url_ou_id: str) -> dict:
    video_id = extrair_id(url_ou_id)
    if video_id is None:
        raise VideoInvalido(
            "Não reconheci um vídeo do YouTube nesse link. "
            "Cole o endereço completo, como https://www.youtube.com/watch?v=..."
        )

    consulta = urllib.parse.urlencode({
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "format": "json",
    })

    try:
        with urllib.request.urlopen(f"{OEMBED}?{consulta}", timeout=TIMEOUT_SEGUNDOS) as r:
            dados = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        # 401/403 = incorporação desabilitada; 404/400 = não existe.
        if erro.code in (401, 403):
            raise VideoInvalido(
                "O dono desse vídeo não permite que ele seja assistido fora "
                "do YouTube, então ele não pode virar aula."
            ) from erro
        raise VideoInvalido(
            "Vídeo não encontrado no YouTube. Confira se o link está certo "
            "e se o vídeo não é privado."
        ) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise VideoInvalido(
            "Não consegui falar com o YouTube agora. Tente de novo."
        ) from erro

    return {
        "youtube_id": video_id,
        "titulo": dados.get("title") or "Vídeo sem título",
        "canal": dados.get("author_name"),
        "miniatura_url": dados.get("thumbnail_url"),
    }


def extrair_playlist_id(url: str) -> Optional[str]:
    """Devolve o `list=` da URL, ou None quando o link é de vídeo avulso."""
    achado = _ID_PLAYLIST.search(url or "")
    return achado.group(1) if achado else None


def buscar_playlist(url_ou_id: str) -> dict:
    playlist_id = extrair_playlist_id(url_ou_id) or (url_ou_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{12,}", playlist_id):
        raise PlaylistInvalida(
            "Não achei uma playlist nesse link. A URL precisa ter a parte "
            "\"list=\", como youtube.com/watch?v=...&list=PL..."
        )

    consulta = urllib.parse.urlencode({"playlist_id": playlist_id})

    try:
        with urllib.request.urlopen(
            f"{FEED_PLAYLIST}?{consulta}", timeout=TIMEOUT_SEGUNDOS
        ) as r:
            xml = r.read()
    except urllib.error.HTTPError as erro:
        raise PlaylistInvalida(
            "Playlist não encontrada. Confira se ela é pública."
        ) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise PlaylistInvalida(
            "Não consegui falar com o YouTube agora. Tente de novo."
        ) from erro

    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError as erro:
        raise PlaylistInvalida("O YouTube devolveu algo inesperado.") from erro

    titulo_feed = raiz.findtext("atom:title", default="", namespaces=_NS)
    canal_feed = raiz.findtext("atom:author/atom:name", default=None, namespaces=_NS)

    videos: List[dict] = []
    for entrada in raiz.findall("atom:entry", _NS):
        video_id = entrada.findtext("yt:videoId", default="", namespaces=_NS)
        if not video_id:
            continue

        miniatura = entrada.find("media:group/media:thumbnail", _NS)
        videos.append({
            "youtube_id": video_id,
            "titulo": entrada.findtext("atom:title", default="Vídeo", namespaces=_NS),
            "canal": entrada.findtext(
                "atom:author/atom:name", default=canal_feed, namespaces=_NS
            ),
            "miniatura_url": (
                miniatura.get("url") if miniatura is not None
                else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            ),
        })

    if not videos:
        raise PlaylistInvalida(
            "A playlist existe mas veio vazia. Ela pode ser privada."
        )

    return {
        "playlist_id": playlist_id,
        "titulo": titulo_feed or "Curso",
        "canal": canal_feed,
        "videos": videos,
        "truncada": len(videos) >= LIMITE_DO_FEED,
    }


def _buscar_playlist_pela_api(playlist_id: str, chave: str) -> dict:
    videos: List[dict] = []
    titulo = None
    canal = None
    pagina = None

    while True:
        parametros = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": PAGINA_API,
            "key": chave,
        }
        if pagina:
            parametros["pageToken"] = pagina

        url = f"{API_PLAYLIST_ITEMS}?{urllib.parse.urlencode(parametros)}"

        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_SEGUNDOS) as r:
                dados = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            detalhe = ""
            try:
                corpo = json.loads(erro.read().decode("utf-8"))
                detalhe = corpo.get("error", {}).get("message", "")
            except Exception:
                pass

            if erro.code == 403:
                raise PlaylistInvalida(
                    "A YouTube Data API recusou a chave. Confira se a "
                    f"YouTube Data API v3 está ativada no projeto. {detalhe}"
                ) from erro
            if erro.code == 404:
                raise PlaylistInvalida(
                    "Playlist não encontrada. Confira se ela é pública."
                ) from erro
            raise PlaylistInvalida(
                f"A YouTube Data API respondeu {erro.code}. {detalhe}"
            ) from erro
        except (urllib.error.URLError, TimeoutError) as erro:
            raise PlaylistInvalida(
                "Não consegui falar com a YouTube Data API agora."
            ) from erro

        for item in dados.get("items", []):
            trecho = item.get("snippet", {})
            recurso = trecho.get("resourceId", {})
            video_id = recurso.get("videoId")
            if not video_id:
                continue

            # Vídeo removido ou privado entra na playlist como "Private
            # video"/"Deleted video" e não tem como tocar — fica de fora.
            nome = trecho.get("title", "")
            if nome in ("Private video", "Deleted video"):
                continue

            titulo = titulo or trecho.get("channelTitle")
            canal = canal or trecho.get("videoOwnerChannelTitle") or trecho.get("channelTitle")

            miniaturas = trecho.get("thumbnails") or {}
            melhor = (
                miniaturas.get("high")
                or miniaturas.get("medium")
                or miniaturas.get("default")
                or {}
            )

            videos.append({
                "youtube_id": video_id,
                "titulo": nome or "Vídeo",
                "canal": trecho.get("videoOwnerChannelTitle")
                or trecho.get("channelTitle"),
                "miniatura_url": melhor.get("url")
                or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            })

        pagina = dados.get("nextPageToken")
        if not pagina:
            break

    if not videos:
        raise PlaylistInvalida(
            "A playlist existe mas veio vazia. Ela pode ser privada."
        )

    return {
        "playlist_id": playlist_id,
        "titulo": None,
        "canal": canal,
        "videos": videos,
        "truncada": False,
    }


def buscar_playlist_completa(url_ou_id: str, chave: Optional[str] = None) -> dict:
    try:
        pelo_feed = buscar_playlist(url_ou_id)
    except PlaylistInvalida:
        if not chave:
            raise
        pelo_feed = None

    if not chave:
        return pelo_feed

    playlist_id = extrair_playlist_id(url_ou_id) or (url_ou_id or "").strip()
    completa = _buscar_playlist_pela_api(playlist_id, chave)

    if pelo_feed:
        completa["titulo"] = pelo_feed["titulo"]
        completa["canal"] = completa["canal"] or pelo_feed["canal"]

    return completa
