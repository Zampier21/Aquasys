import argparse
import sys
from pathlib import Path

from app.core.console import preparar as preparar_console

preparar_console()

from app.database import SessionLocal
from app.models.especie import Especie, EspecieImagem
from app.services import imagens as svc


def _especies(db, filtro: str | None, refazer: bool, limite: int | None):
    """Espécies a processar, na ordem do nome."""
    consulta = db.query(Especie).filter(Especie.ativo.is_(True))

    if filtro:
        consulta = consulta.filter(Especie.nome_comum.ilike(f"%{filtro}%"))

    if not refazer:
        # A subconsulta evita trazer os bytes só para saber quem já tem.
        ja_tem = db.query(EspecieImagem.especie_id).subquery()
        consulta = consulta.filter(~Especie.id.in_(ja_tem.select()))

    consulta = consulta.order_by(Especie.nome_comum)
    return consulta.limit(limite).all() if limite else consulta.all()


def _gravar(db, especie, pronta: svc.ImagemPronta, achado) -> None:
    """Insere ou substitui a linha da imagem daquela espécie."""
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
    linha.mime = svc.MIME
    linha.hash = pronta.hash
    linha.largura = pronta.largura
    linha.altura = pronta.altura
    linha.bytes_miniatura = len(pronta.miniatura)
    linha.bytes_completa = len(pronta.completa)

    linha.fonte = achado.fonte if achado else None
    linha.autor = achado.autor if achado else None
    linha.licenca = achado.licenca if achado else None
    linha.licenca_url = achado.licenca_url if achado else None

    db.commit()


# ═══════════════════════════════════════════════════════
# COMANDOS
# ═══════════════════════════════════════════════════════
def listar(db) -> None:
    total = db.query(Especie).filter(Especie.ativo.is_(True)).count()
    linhas = db.query(
        EspecieImagem.especie_id,
        EspecieImagem.bytes_completa,
        EspecieImagem.bytes_miniatura,
        EspecieImagem.licenca,
    ).all()

    com_foto = {linha[0] for linha in linhas}
    peso = sum((linha[1] or 0) + (linha[2] or 0) for linha in linhas)

    print(f"\nEspécies ativas: {total}")
    print(f"Com foto:        {len(com_foto)}")
    print(f"Sem foto:        {total - len(com_foto)}")
    print(f"Peso no banco:   {peso / 1024 / 1024:.1f} MB\n")

    creditos = {
        linha.especie_id: linha
        for linha in db.query(EspecieImagem).with_entities(
            EspecieImagem.especie_id, EspecieImagem.licenca, EspecieImagem.autor
        )
    }

    for especie in (
        db.query(Especie)
        .filter(Especie.ativo.is_(True))
        .order_by(Especie.nome_comum)
        .all()
    ):
        credito = creditos.get(especie.id)
        if credito is None:
            print(f"  ·  {especie.nome_comum:<28} sem foto")
        else:
            autor = (credito.autor or "autor não informado")[:34]
            print(
                f"  OK {especie.nome_comum:<28} {credito.licenca or '?':<18} {autor}"
            )
    print()


def remover(db, filtro: str) -> None:
    alvos = (
        db.query(Especie)
        .filter(Especie.ativo.is_(True), Especie.nome_comum.ilike(f"%{filtro}%"))
        .all()
    )
    if not alvos:
        print(f"Nenhuma espécie casa com '{filtro}'.")
        return

    apagadas = 0
    for especie in alvos:
        removidas = (
            db.query(EspecieImagem)
            .filter(EspecieImagem.especie_id == especie.id)
            .delete()
        )
        if removidas:
            print(f"  removida a foto de {especie.nome_comum}")
            apagadas += removidas

    db.commit()
    print(f"\n{apagadas} foto(s) removida(s).")


def de_arquivo(db, filtro: str, caminho: Path) -> int:
    """Usa uma imagem local — a saída para quando o Commons não tem nada."""
    if not caminho.is_file():
        print(f"Arquivo não encontrado: {caminho}")
        return 1

    especies = (
        db.query(Especie)
        .filter(Especie.ativo.is_(True), Especie.nome_comum.ilike(f"%{filtro}%"))
        .all()
    )
    if len(especies) != 1:
        # Gravar a foto errada em massa é pior do que não gravar nada.
        print(
            f"'{filtro}' casa com {len(especies)} espécies — precisa casar com "
            f"exatamente uma."
        )
        for e in especies[:10]:
            print(f"  · {e.nome_comum}")
        return 1

    especie = especies[0]
    try:
        pronta = svc.preparar(caminho.read_bytes())
    except svc.ImagemInvalida as erro:
        print(f"{especie.nome_comum}: {erro}")
        return 1

    _gravar(db, especie, pronta, achado=None)
    print(f"OK {especie.nome_comum} ← {caminho.name} ({pronta.resumo})")
    return 0


def baixar_faltantes(db, filtro, refazer, limite) -> int:
    especies = _especies(db, filtro, refazer, limite)
    if not especies:
        print("Nada a fazer: todas as espécies já têm foto.")
        return 0

    print(f"\n{len(especies)} espécie(s) para buscar no Wikimedia Commons.\n")

    achadas = falhas = 0
    with svc._cliente() as cliente:
        for especie in especies:
            rotulo = especie.nome_comum
            cientifico = especie.nome_cientifico or ""

            try:
                achado = svc.buscar(cientifico, rotulo, cliente=cliente)
            except Exception as erro:
                print(f"  !  {rotulo:<28} erro na busca: {erro}")
                falhas += 1
                continue

            if achado is None:
                print(f"  ·  {rotulo:<28} nada com licença livre encontrado")
                falhas += 1
                continue

            try:
                pronta = svc.preparar(svc.baixar(achado.url, cliente=cliente))
            except (svc.ImagemInvalida, Exception) as erro:
                print(f"  !  {rotulo:<28} {erro}")
                falhas += 1
                continue

            _gravar(db, especie, pronta, achado)
            achadas += 1
            print(
                f"  OK {rotulo:<28} {pronta.resumo:<26} "
                f"{achado.licenca or 'licença não informada'}"
            )

    print(f"\n{achadas} foto(s) gravada(s), {falhas} sem resultado.")
    if falhas:
        print(
            "Para as que faltaram, use:\n"
            '  python baixar_imagens.py --especie "<nome>" --arquivo <foto.jpg>'
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Popula as fotos do catálogo de espécies."
    )
    parser.add_argument("--listar", action="store_true",
                        help="mostra o estado de cada espécie, sem baixar nada")
    parser.add_argument("--refazer", action="store_true",
                        help="rebaixa também as espécies que já têm foto")
    parser.add_argument("--especie", metavar="NOME",
                        help="filtra pelo nome comum (busca parcial)")
    parser.add_argument("--arquivo", metavar="CAMINHO", type=Path,
                        help="usa uma imagem local em vez de buscar na internet")
    parser.add_argument("--remover", metavar="NOME",
                        help="apaga a foto das espécies que casam com o nome")
    parser.add_argument("--limite", type=int, metavar="N",
                        help="processa no máximo N espécies")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.listar:
            listar(db)
            return 0

        if args.remover:
            remover(db, args.remover)
            return 0

        if args.arquivo:
            if not args.especie:
                print("--arquivo precisa de --especie para saber de quem é a foto.")
                return 1
            return de_arquivo(db, args.especie, args.arquivo)

        return baixar_faltantes(db, args.especie, args.refazer, args.limite)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
