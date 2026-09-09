"""
Prepara o banco: cria as tabelas que faltam e aplica as migrações pendentes.

    python criar_tabelas.py

Seguro de rodar várias vezes — e essa é a razão de existir a tabela de
controle `_migracao`: uma migração antiga pode mencionar algo que uma
migração posterior removeu (a 001 fala da tabela `cliente`, que a 004
apagou). Reexecutar tudo do zero quebraria. Cada arquivo roda uma vez só.

Banco novo, do zero:
  `create_all` já monta o esquema atual a partir dos modelos, então as
  migrações são apenas marcadas como aplicadas — elas descrevem o caminho
  até aqui, não o destino.

Banco que já existia:
  roda só os arquivos de `sql/` que ainda não foram registrados.
"""

from app.core.console import preparar

preparar()

from pathlib import Path

from sqlalchemy import inspect, text

import app.models  # noqa: F401  — registra todos os modelos no metadata
from app.database import Base, engine

PASTA_SQL = Path(__file__).parent / "sql"

CONTROLE = """
CREATE TABLE IF NOT EXISTS _migracao (
    arquivo     VARCHAR(120) PRIMARY KEY,
    aplicada_em TIMESTAMP NOT NULL DEFAULT now()
)
"""


def main() -> None:
    tabelas_antes = set(inspect(engine).get_table_names())
    banco_novo = not (tabelas_antes - {"_migracao"})

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conexao:
        conexao.execute(text(CONTROLE))

    criadas = sorted(set(inspect(engine).get_table_names()) - tabelas_antes)
    criadas = [t for t in criadas if t != "_migracao"]
    if criadas:
        print(f"Tabelas criadas ({len(criadas)}):")
        for nome in criadas:
            print(f"  + {nome}")
    else:
        print("Nenhuma tabela faltando.")

    with engine.begin() as conexao:
        aplicadas = {
            linha[0] for linha in conexao.execute(text("SELECT arquivo FROM _migracao"))
        }

    pendentes = [a for a in sorted(PASTA_SQL.glob("*.sql")) if a.name not in aplicadas]

    if not pendentes:
        print("\nNenhuma migração pendente.")
        return

    if banco_novo:
        # O esquema saiu dos modelos, já no formato final: as migrações
        # descrevem como se chegou aqui e não têm o que fazer.
        with engine.begin() as conexao:
            for arquivo in pendentes:
                conexao.execute(
                    text("INSERT INTO _migracao (arquivo) VALUES (:a)"),
                    {"a": arquivo.name},
                )
        print(f"\nBanco novo: {len(pendentes)} migração(ões) marcadas como aplicadas.")
        return

    print(f"\nAplicando {len(pendentes)} migração(ões) pendente(s):")
    for arquivo in pendentes:
        with engine.begin() as conexao:
            conexao.execute(text(arquivo.read_text(encoding="utf-8")))
            conexao.execute(
                text("INSERT INTO _migracao (arquivo) VALUES (:a)"),
                {"a": arquivo.name},
            )
        print(f"  · {arquivo.name}")

    print("\nBanco pronto.")


if __name__ == "__main__":
    main()
