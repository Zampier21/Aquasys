"""
Popula os cursos GLOBAIS do AquaSys (os que toda loja e todo cliente veem).

    python seed_cursos.py            importa
    python seed_cursos.py --listar   mostra o que já está importado

Curso global tem `dono_id` nulo — e é por isso que ele não pode ser criado
pelo app: a rota POST /cursos/ sempre carimba a loja logada como dona.
Este script é o caminho para o conteúdo que é seu, não de uma loja.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DE ONDE VÊM OS VÍDEOS

1. `playlist` — o link da playlist. Sem chave de API isso usa o feed RSS
   público do YouTube, que entrega no máximo 15 vídeos. É de graça e não
   pede cadastro nenhum.

2. `cursos.txt` — os links que você cola à mão, um por linha, embaixo do
   nome do curso. É como se completa o que passou de 15.

Os dois se somam, e link repetido é ignorado: dá para colar a playlist
inteira em `cursos.txt` sem conferir o que já entrou. Rodar o script de
novo nunca duplica nada.

`esperado` é quantos vídeos a playlist tem de verdade — o script compara
e diz quanto ainda falta.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from app.core.console import preparar

preparar()

import re
import sys
from pathlib import Path

from app.core.config import settings
from app.database import SessionLocal
from app.models.curso import Aula, Curso
from app.services import youtube

ARQUIVO_LINKS = Path(__file__).parent / "cursos.txt"

CURSOS = [
    {
        "titulo": "O Segredo do Aquarismo",
        "descricao": "Curso de introdução ao aquarismo, do canal Alô Aquarista. "
                     "Começa do zero: por que ter um aquário e o que você "
                     "precisa saber antes de montar o seu.",
        "categoria": "iniciante",
        "playlist": "https://www.youtube.com/watch?v=dmS280duxkc"
                    "&list=PLHL_oeAq-y70XJ8vHUHr0H9hfzd5bqR2c",
        "esperado": 17,
    },
    {
        "titulo": "Aquário Plantado de A a Z",
        "descricao": "Série do canal Amantes do Aquarismo sobre aquário "
                     "plantado: substrato, iluminação, CO₂, móvel e "
                     "manutenção, do primeiro passo ao aquário montado.",
        "categoria": "plantado",
        "playlist": "https://www.youtube.com/watch?v=xFohosK3hXA"
                    "&list=PLiifQMZcVdfFgJ3Z_CGw0RJNFFDvGhJVu",
        "esperado": 22,
    },
    {
        "titulo": "Aquário Marinho de A a Z",
        "descricao": "Série do canal Amantes do Aquarismo sobre aquarismo "
                     "marinho: como iniciar, equipamentos e os cuidados que "
                     "a água salgada exige.",
        "categoria": "marinho",
        "playlist": "https://www.youtube.com/watch?v=i9E2a5u515Q"
                    "&list=PLiifQMZcVdfHl7AD5CnrZ7QZ5qz0qIKKa",
        "esperado": 39,
    },
]


def asc(texto: str) -> str:
    """O console do Windows engasga em emoji de título de vídeo."""
    return (texto or "").encode("ascii", "replace").decode("ascii")


def ler_links_do_arquivo() -> dict:
    """
    Lê `cursos.txt` e devolve {titulo_do_curso: [links]}.

    Formato: `[Nome do curso]` abre uma seção, e cada linha seguinte é um
    link. Linha vazia e linha começando com # são ignoradas.
    """
    if not ARQUIVO_LINKS.exists():
        return {}

    por_curso: dict = {}
    atual = None

    for numero, linha in enumerate(
        ARQUIVO_LINKS.read_text(encoding="utf-8").splitlines(), start=1
    ):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue

        cabecalho = re.fullmatch(r"\[(.+)\]", linha)
        if cabecalho:
            atual = cabecalho.group(1).strip()
            por_curso.setdefault(atual, [])
            continue

        if atual is None:
            print(f"  ! {ARQUIVO_LINKS.name} linha {numero}: link fora de "
                  f"qualquer [curso], ignorado")
            continue

        por_curso[atual].append(linha)

    return por_curso


def coletar_videos(
    dados: dict, links_manuais: list, ja_tem: set
) -> tuple[list, bool, list]:
    """
    Junta os vídeos da playlist com os colados à mão.

    Devolve `(novos, truncada, ordem_playlist)`. `ordem_playlist` é a
    sequência de youtube_id como o YouTube entrega — inclusive os que já
    estavam no curso —, usada para consertar a ordem das aulas.

    `ja_tem` são os youtube_id que o curso já tem: usado para não gastar
    uma consulta ao YouTube por vídeo que seria descartado em seguida.
    """
    videos, truncada, ordem_playlist = [], False, []
    vistos = set(ja_tem)

    if dados.get("playlist"):
        try:
            playlist = youtube.buscar_playlist_completa(
                dados["playlist"], settings.YOUTUBE_API_KEY
            )
            ordem_playlist = [v["youtube_id"] for v in playlist["videos"]]
            for video in playlist["videos"]:
                if video["youtube_id"] not in vistos:
                    vistos.add(video["youtube_id"])
                    videos.append(video)
            truncada = playlist["truncada"]
        except youtube.PlaylistInvalida as erro:
            print(f"  ! playlist: {erro}")

    for link in links_manuais:
        # Descarta antes de consultar o YouTube o que já está no curso.
        video_id = youtube.extrair_id(link)
        if video_id and video_id in vistos:
            continue

        try:
            video = youtube.buscar_metadados(link)
        except youtube.VideoInvalido as erro:
            print(f"  ! {link[:60]}\n    {erro}")
            continue

        if video["youtube_id"] in vistos:
            continue

        vistos.add(video["youtube_id"])
        videos.append(video)

    return videos, truncada, ordem_playlist


def reordenar(curso: Curso, ordem_playlist: list) -> bool:
    """
    Põe as aulas na sequência da playlist do YouTube.

    Necessário porque o feed RSS pode pular vídeos do meio: importados
    depois, eles seriam anexados no fim e a AULA 15 acabaria atrás da 16.
    Vídeo que não está na playlist (colado à mão) vai para o final,
    mantendo a ordem relativa que já tinha.
    """
    posicao = {video_id: i for i, video_id in enumerate(ordem_playlist)}
    fim = len(posicao)

    atual = [(a.ordem, a) for a in curso.aulas]
    nova = sorted(
        atual,
        # Quem não está na playlist entra depois, desempatado pela
        # ordem que já ocupava.
        key=lambda par: (posicao.get(par[1].youtube_id, fim + par[0]), par[0]),
    )

    mudou = False
    for indice, (_, aula) in enumerate(nova):
        if aula.ordem != indice:
            aula.ordem = indice
            mudou = True
    return mudou


def listar() -> None:
    """Mostra o que já está no banco, para conferir contra o YouTube."""
    db = SessionLocal()
    try:
        cursos = (
            db.query(Curso)
            .filter(Curso.dono_id.is_(None))
            .order_by(Curso.titulo)
            .all()
        )
        if not cursos:
            print("Nenhum curso global cadastrado ainda.")
            return

        esperados = {c["titulo"]: c.get("esperado") for c in CURSOS}

        for curso in cursos:
            alvo = esperados.get(curso.titulo)
            de = f" de {alvo}" if alvo else ""
            print(f"\n{asc(curso.titulo)}  —  {len(curso.aulas)}{de} aulas")
            for aula in curso.aulas:
                print(f"  {aula.ordem:>2}. {aula.youtube_id}  {asc(aula.titulo)[:60]}")
    finally:
        db.close()


def conferir_secoes(links_por_curso: dict) -> None:
    """
    Avisa sobre seção de `cursos.txt` que não bate com curso nenhum.

    Sem isso, um nome digitado errado faria os links serem ignorados em
    silêncio — e você só descobriria estranhando o total no app.
    """
    conhecidos = {c["titulo"] for c in CURSOS}

    for secao, links in links_por_curso.items():
        if secao in conhecidos or not links:
            continue

        print(
            f"\n  ! {ARQUIVO_LINKS.name}: a secao [{asc(secao)}] nao "
            f"corresponde a nenhum curso.\n"
            f"    {len(links)} link(s) foram ignorados. Os nomes validos sao:"
        )
        for titulo in sorted(conhecidos):
            print(f"      [{asc(titulo)}]")


def main() -> None:
    links_por_curso = ler_links_do_arquivo()
    conferir_secoes(links_por_curso)
    db = SessionLocal()

    try:
        cursos_novos = aulas_novas = 0
        faltando = []

        for dados in CURSOS:
            curso = (
                db.query(Curso)
                .filter(Curso.titulo == dados["titulo"], Curso.dono_id.is_(None))
                .first()
            )

            if curso is None:
                curso = Curso(
                    dono_id=None,  # nulo = global
                    titulo=dados["titulo"],
                    descricao=dados.get("descricao"),
                    categoria=dados.get("categoria"),
                    ativo=True,
                )
                db.add(curso)
                db.flush()
                cursos_novos += 1
                print(f'\n+ curso "{asc(curso.titulo)}"')
            else:
                print(f'\n  curso "{asc(curso.titulo)}"')

            existentes = {a.youtube_id for a in curso.aulas}
            ordem = len(existentes)

            videos, truncada, ordem_playlist = coletar_videos(
                dados,
                links_por_curso.get(dados["titulo"], []),
                existentes,
            )

            for video in videos:
                db.add(Aula(
                    curso_id=curso.id,
                    titulo=video["titulo"],
                    youtube_id=video["youtube_id"],
                    canal=video["canal"],
                    miniatura_url=video["miniatura_url"],
                    ordem=ordem,
                ))
                existentes.add(video["youtube_id"])
                ordem += 1
                aulas_novas += 1
                print(f"    + {asc(video['titulo'])[:64]}")

            # Só reordena quando a playlist veio inteira: com o feed
            # truncado, a sequência conhecida é parcial e mexer na ordem
            # faria mais mal que bem.
            if ordem_playlist and not truncada:
                db.flush()
                if reordenar(curso, ordem_playlist):
                    print("    ~ ordem das aulas ajustada pela playlist")

            total = len(existentes)
            esperado = dados.get("esperado")
            if esperado and total < esperado:
                faltando.append((curso.titulo, total, esperado))
            elif truncada and not esperado:
                faltando.append((curso.titulo, total, None))

        db.commit()

        fonte = (
            "YouTube Data API"
            if settings.YOUTUBE_API_KEY
            else "feed RSS (teto de 15) + cursos.txt"
        )
        print(
            f"\n{cursos_novos} curso(s) e {aulas_novas} aula(s) inseridos. "
            f"Fonte: {fonte}."
        )

        if not faltando:
            print("\nTodos os cursos estao completos.")
            return

        print("\nAINDA FALTAM VIDEOS:")
        for titulo, tem, esperado in faltando:
            if esperado:
                print(f"  - {asc(titulo)}: {tem} de {esperado} "
                      f"({esperado - tem} faltando)")
            else:
                print(f"  - {asc(titulo)}: {tem} (a playlist pode ter mais)")

        print(
            f"\nAbra a playlist no YouTube e cole os links em "
            f"{ARQUIVO_LINKS.name}, embaixo do nome do curso.\n"
            f"Pode colar todos sem conferir: repetido nao duplica.\n"
            f"Para ver o que ja entrou: python seed_cursos.py --listar"
        )
    finally:
        db.close()


if __name__ == "__main__":
    if "--listar" in sys.argv:
        listar()
    else:
        main()
