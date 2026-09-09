"""
Recalcula os alertas de todos os aquários.

    python regerar_alertas.py

Serve para duas situações:
  - aquários criados antes de os alertas existirem, que nunca passaram
    pelo gatilho de gravação;
  - quando você mexe nas faixas ideais em `app/services/parametros.py`
    e quer que os alertas já gravados reflitam a regra nova.

No dia a dia não precisa rodar: cada medição nova já regrava os alertas
do próprio aquário.
"""

from app.core.console import preparar

preparar()

from app.database import SessionLocal
from app.models.aquario import Aquario
from app.routers.aquarios import regerar_alertas


def main() -> None:
    db = SessionLocal()
    try:
        aquarios = db.query(Aquario).order_by(Aquario.criado_em).all()

        for aquario in aquarios:
            regerar_alertas(aquario, db)

        db.commit()

        # Releitura para relatar o que ficou de fato gravado.
        total = 0
        for aquario in aquarios:
            medicao = aquario.parametros[0] if aquario.parametros else None
            from app.services import parametros as svc

            problemas, _ = svc.avaliar(aquario, medicao)
            total += len(problemas)
            situacao = (
                ", ".join(p["nome"] for p in problemas) if problemas else "tudo ok"
            )
            print(f"  {aquario.nome:20} {situacao}")

        print(f"\n{len(aquarios)} aquário(s) processado(s), {total} alerta(s) abertos.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
