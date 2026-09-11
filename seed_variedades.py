"""
Cadastra variedades de aquariofilia para as espécies-base do catálogo.

    python seed_variedades.py

Seguro de rodar várias vezes: variedade que já existe é ignorada.

Uma variedade é o mesmo peixe com outra aparência — Acará Bandeira
Marmorato, Betta Halfmoon. Ela herda toda a biologia da base e declara
só o que de fato difere. Aqui, o único caso é o Betta Plakat, que é
justamente a forma de nadadeira curta: isso pesa no motor, porque o
Barbo Sumatra morde nadadeira longa e deixa a curta em paz.

O que NÃO está aqui, de propósito:

  · Tetra Neon Negro. Não é variedade do Neon Tetra do catálogo: é outra
    espécie, de outro gênero (Hyphessobrycon herbertaxelrodi, contra
    Paracheirodon innesi). Pendurá-lo no Neon Tetra faria ele herdar pH,
    temperatura e cardume de outro animal. Precisa entrar como espécie-base
    própria, com a biologia dele, e só então receber o albino.

  · Fotos. A busca automática no Wikimedia é pelo nome científico, que a
    variedade compartilha com a base — todas receberiam a foto do peixe
    selvagem. Cada foto de variedade entra por:

        python baixar_imagens.py --especie "Marmorato" --arquivo caminho/da/foto.jpg
"""

from app.core.console import preparar

preparar()
from app.database import SessionLocal  # noqa: E402
from app.models.especie import Especie  # noqa: E402
from app.services import variedades as svc_variedades  # noqa: E402

# Base (nome_comum exato) -> variedades.
# Cada variedade é (nome completo, diferenças em relação à base).
VARIEDADES = {
    "Acará Bandeira": [
        ("Acará Bandeira Marmorato", {}),
        ("Acará Bandeira Leopardo Azul", {}),
        ("Acará Bandeira Albino", {}),
        ("Acará Bandeira Koi", {}),
        ("Acará Bandeira Negro", {}),
        ("Acará Bandeira Platinum", {}),
        ("Acará Bandeira Véu", {}),
    ],
    "Betta": [
        ("Betta Halfmoon", {}),
        ("Betta Crowntail", {}),
        ("Betta Véu", {}),
        ("Betta Koi", {}),
        # A forma de nadadeira curta. Continua brigando com outros machos —
        # isso ela herda —, mas deixa de ser alvo de quem morde nadadeira.
        ("Betta Plakat", {"barbatana_longa": False}),
    ],
    "Molinésia": [
        ("Molinésia Balão", {}),
        ("Molinésia Dálmata", {}),
        ("Molinésia Negra", {}),
        ("Molinésia Lira", {}),
    ],
    "Acará Disco": [
        ("Acará Disco Pigeon Blood", {}),
        ("Acará Disco Turquesa Vermelho", {}),
        ("Acará Disco Diamante Azul", {}),
        ("Acará Disco Leopardo", {}),
    ],
    "Barbo Sumatra": [
        ("Barbo Sumatra Albino", {}),
        ("Barbo Sumatra Verde", {}),
        ("Barbo Sumatra Dourado", {}),
    ],
}


def executar():
    db = SessionLocal()
    criadas = ignoradas = 0
    sem_base = []

    try:
        for nome_base, lista in VARIEDADES.items():
            base = (
                db.query(Especie)
                .filter(
                    Especie.nome_comum == nome_base,
                    Especie.variante_de_id.is_(None),
                )
                .first()
            )
            if base is None:
                sem_base.append(nome_base)
                continue

            print(f"\n{nome_base}")
            for nome, diferencas in lista:
                # Deduplica pelo nome, e não pelo científico como faz o
                # seed_especies: a variedade compartilha o científico da base.
                if db.query(Especie).filter(Especie.nome_comum == nome).first():
                    ignoradas += 1
                    print(f"  ja existe  · {svc_variedades.nome_curto_de(nome, nome_base)}")
                    continue

                db.add(svc_variedades.criar_variedade(base, nome, **diferencas))
                criadas += 1
                marca = "  (nadadeira curta)" if diferencas else ""
                print(f"  cadastrada · {svc_variedades.nome_curto_de(nome, nome_base)}{marca}")

        db.commit()
        print(f"\n{criadas} variedade(s) cadastrada(s), {ignoradas} ignorada(s).")
        if sem_base:
            print("Sem base no catálogo, puladas: " + ", ".join(sem_base))

    except Exception as erro:
        db.rollback()
        print(f"\nErro: {erro}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    executar()
