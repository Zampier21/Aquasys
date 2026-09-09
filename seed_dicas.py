"""
Popula a tabela `dica` com o conteúdo da Home.

    python seed_dicas.py

Seguro de rodar de novo: dica já existente (mesmo conteúdo) é ignorada.

São dois tipos:
  - gerais      (especie_id nulo) — valem para qualquer aquário;
  - por espécie (especie_id preenchido) — só aparecem para quem tem
    aquela espécie. Estas são derivadas dos próprios dados do catálogo,
    então acompanham sozinhas qualquer espécie nova que você semear.

Categorias aceitas pelo banco: quimica | comportamento | equipamento
"""

from app.core.console import preparar

preparar()

from app.database import SessionLocal
from app.models.dica import Dica
from app.models.especie import Especie

DICAS_GERAIS = [
    ("quimica",
     "Faça a troca parcial de água toda semana — entre 20% e 30% do volume."),
    ("quimica",
     "Mantenha a temperatura entre 24 °C e 28 °C. Variação brusca estressa "
     "mais o peixe do que um valor um pouco fora do ideal."),
    ("quimica",
     "Amônia e nitrito têm de ficar sempre em zero. Qualquer valor acima "
     "disso já indica problema no ciclo do aquário."),
    ("equipamento",
     "Nunca lave a mídia do filtro em água da torneira: o cloro mata as "
     "bactérias que fazem a filtragem biológica."),
    ("equipamento",
     "Use termostato com desligamento automático — superaquecimento mata "
     "um aquário inteiro em poucas horas."),
]


def dicas_por_especie(db):
    """Monta a dica de convívio a partir do catálogo de espécies."""
    for especie in db.query(Especie).filter(Especie.ativo.is_(True)).all():
        nome = especie.nome_comum

        if especie.agrupamento == "cardume" and especie.cardume_minimo:
            yield especie.id, (
                f"Seus {nome} precisam estar em um grupo de pelo menos "
                f"{especie.cardume_minimo} peixes para se sentirem seguros."
            )
        elif especie.agrupamento == "solitario":
            yield especie.id, (
                f"{nome} vive sozinho. Dois no mesmo aquário brigam até um "
                f"deles morrer."
            )
        elif especie.agrupamento == "par":
            yield especie.id, (
                f"{nome} se dá melhor em casal. Sozinho fica arisco; em "
                f"trio, costuma sobrar briga."
            )
        elif especie.agrupamento == "harem":
            yield especie.id, (
                f"Em {nome}, mantenha duas ou três fêmeas para cada macho — "
                f"assim nenhuma fêmea é perseguida o tempo todo."
            )


def main() -> None:
    db = SessionLocal()
    try:
        existentes = {d.conteudo for d in db.query(Dica).all()}
        novas = 0

        for categoria, conteudo in DICAS_GERAIS:
            if conteudo in existentes:
                continue
            db.add(Dica(conteudo=conteudo, categoria=categoria, ativa=True))
            novas += 1

        for especie_id, conteudo in dicas_por_especie(db):
            if conteudo in existentes:
                continue
            db.add(Dica(
                conteudo=conteudo,
                categoria="comportamento",
                especie_id=especie_id,
                ativa=True,
            ))
            novas += 1

        db.commit()
        total = db.query(Dica).count()
        print(f"{novas} dica(s) inserida(s). Total na tabela: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
