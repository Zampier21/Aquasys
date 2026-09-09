
from app.core.console import preparar

preparar()
from app.database import SessionLocal
from app.models.especie import Especie

# ═══════════════════════════════════════════════════════════
# VALORES ACEITOS
#   tipo_agua      : doce | salobra | marinho
#   comportamento  : pacifico | semi_agressivo | territorial | agressivo
#   agrupamento    : cardume | par | harem | solitario
#   nivel_natacao  : fundo | meio | superficie | todos
#   alimentacao    : carnivoro | onivoro | herbivoro | limnivoro
#   dificuldade    : facil | medio | dificil
#   reef_safe      : sim | com_ressalva | nao   (apenas marinhos)
# ═══════════════════════════════════════════════════════════

ESPECIES = [
    {
        "nome_comum": "Neon Tetra",
        "nome_cientifico": "Paracheirodon innesi",
        "familia": "Characidae",
        "tipo_agua": "doce",
        "origem": "Bacia do Rio Amazonas — Peru, Colômbia, Brasil",
        "temp_min": 20, "temp_max": 26,
        "ph_min": 5.0, "ph_max": 7.0,
        "dgh_min": 1, "dgh_max": 10,
        "tamanho_adulto_cm": 4,
        "volume_minimo_l": 40,
        "comportamento": "pacifico",
        "agressivo_coespecificos": False,
        "agrupamento": "cardume",
        "cardume_minimo": 10,
        "nivel_natacao": "meio",
        "morde_barbatana": False,
        "barbatana_longa": False,
        "come_plantas": False,
        "come_invertebrados": False,
        "alimentacao": "onivoro",
        "nivel_dificuldade": "facil",
        "expectativa_vida_anos": 5,
        "observacoes": "Vira presa de ciclídeos médios. Realça a cor em água escura.",
    },
    {
        "nome_comum": "Acará Bandeira",
        "nome_cientifico": "Pterophyllum scalare",
        "familia": "Cichlidae",
        "tipo_agua": "doce",
        "origem": "Bacia amazônica",
        "temp_min": 24, "temp_max": 30,
        "ph_min": 6.0, "ph_max": 7.5,
        "dgh_min": 3, "dgh_max": 13,
        "tamanho_adulto_cm": 15,
        "volume_minimo_l": 120,
        "comportamento": "semi_agressivo",
        "agressivo_coespecificos": False,
        "agrupamento": "par",
        "cardume_minimo": None,
        "nivel_natacao": "meio",
        "morde_barbatana": False,
        "barbatana_longa": True,
        "come_plantas": False,
        "come_invertebrados": True,
        "alimentacao": "onivoro",
        "nivel_dificuldade": "medio",
        "expectativa_vida_anos": 10,
        "observacoes": "Adulto preda peixes pequenos como Neon. Fica territorial ao reproduzir.",
    },
    {
        "nome_comum": "Betta",
        "nome_cientifico": "Betta splendens",
        "familia": "Osphronemidae",
        "tipo_agua": "doce",
        "origem": "Tailândia, Camboja, Vietnã",
        "temp_min": 24, "temp_max": 28,
        "ph_min": 6.0, "ph_max": 7.5,
        "dgh_min": 2, "dgh_max": 15,
        "tamanho_adulto_cm": 6,
        "volume_minimo_l": 20,
        "comportamento": "territorial",
        "agressivo_coespecificos": True,
        "agrupamento": "solitario",
        "cardume_minimo": None,
        "nivel_natacao": "superficie",
        "morde_barbatana": False,
        "barbatana_longa": True,
        "come_plantas": False,
        "come_invertebrados": True,
        "alimentacao": "carnivoro",
        "nivel_dificuldade": "facil",
        "expectativa_vida_anos": 3,
        "observacoes": "Machos brigam até a morte. Respira ar atmosférico pelo labirinto.",
    },
    {
        "nome_comum": "Barbo Sumatra",
        "nome_cientifico": "Puntigrus tetrazona",
        "familia": "Cyprinidae",
        "tipo_agua": "doce",
        "origem": "Sumatra e Bornéu",
        "temp_min": 23, "temp_max": 27,
        "ph_min": 6.0, "ph_max": 7.5,
        "dgh_min": 5, "dgh_max": 15,
        "tamanho_adulto_cm": 7,
        "volume_minimo_l": 80,
        "comportamento": "semi_agressivo",
        "agressivo_coespecificos": False,
        "agrupamento": "cardume",
        "cardume_minimo": 8,
        "nivel_natacao": "meio",
        "morde_barbatana": True,
        "barbatana_longa": False,
        "come_plantas": True,
        "come_invertebrados": True,
        "alimentacao": "onivoro",
        "nivel_dificuldade": "medio",
        "expectativa_vida_anos": 6,
        "observacoes": "Belisca véus. Em cardume pequeno a agressividade aumenta.",
    },
    {
        "nome_comum": "Coridora Panda",
        "nome_cientifico": "Corydoras panda",
        "familia": "Callichthyidae",
        "tipo_agua": "doce",
        "origem": "Peru — afluentes do Rio Ucayali",
        "temp_min": 22, "temp_max": 26,
        "ph_min": 6.0, "ph_max": 7.4,
        "dgh_min": 2, "dgh_max": 12,
        "tamanho_adulto_cm": 5,
        "volume_minimo_l": 60,
        "comportamento": "pacifico",
        "agressivo_coespecificos": False,
        "agrupamento": "cardume",
        "cardume_minimo": 6,
        "nivel_natacao": "fundo",
        "morde_barbatana": False,
        "barbatana_longa": False,
        "come_plantas": False,
        "come_invertebrados": False,
        "alimentacao": "onivoro",
        "nivel_dificuldade": "facil",
        "expectativa_vida_anos": 10,
        "observacoes": "Exige substrato liso — cascalho grosso machuca os barbilhões.",
    },
    {
        "nome_comum": "Acará Disco",
        "nome_cientifico": "Symphysodon aequifasciatus",
        "familia": "Cichlidae",
        "tipo_agua": "doce",
        "origem": "Bacia amazônica central",
        "temp_min": 28, "temp_max": 30,
        "ph_min": 5.0, "ph_max": 6.5,
        "dgh_min": 1, "dgh_max": 8,
        "tamanho_adulto_cm": 20,
        "volume_minimo_l": 200,
        "comportamento": "pacifico",
        "agressivo_coespecificos": False,
        "agrupamento": "cardume",
        "cardume_minimo": 5,
        "nivel_natacao": "meio",
        "morde_barbatana": False,
        "barbatana_longa": False,
        "come_plantas": False,
        "come_invertebrados": True,
        "alimentacao": "carnivoro",
        "nivel_dificuldade": "dificil",
        "expectativa_vida_anos": 12,
        "observacoes": "Exige água mole, quente e trocas frequentes. Não é para iniciantes.",
    },
    {
        "nome_comum": "Molinésia",
        "nome_cientifico": "Poecilia sphenops",
        "familia": "Poeciliidae",
        "tipo_agua": "doce",
        "origem": "América Central",
        "temp_min": 24, "temp_max": 28,
        "ph_min": 7.0, "ph_max": 8.5,
        "dgh_min": 10, "dgh_max": 25,
        "tamanho_adulto_cm": 8,
        "volume_minimo_l": 60,
        "comportamento": "pacifico",
        "agressivo_coespecificos": False,
        "agrupamento": "harem",
        "cardume_minimo": 3,
        "nivel_natacao": "todos",
        "morde_barbatana": False,
        "barbatana_longa": False,
        "come_plantas": True,
        "come_invertebrados": False,
        "alimentacao": "onivoro",
        "nivel_dificuldade": "facil",
        "expectativa_vida_anos": 4,
        "observacoes": "Prefere água dura e alcalina. Tolera água levemente salobra.",
    },
    {
        "nome_comum": "Palhaço",
        "nome_cientifico": "Amphiprion ocellaris",
        "familia": "Pomacentridae",
        "tipo_agua": "marinho",
        "origem": "Indo-Pacífico",
        "temp_min": 24, "temp_max": 27,
        "ph_min": 8.0, "ph_max": 8.4,
        "dgh_min": None, "dgh_max": None,
        "tamanho_adulto_cm": 8,
        "volume_minimo_l": 100,
        "comportamento": "semi_agressivo",
        "agressivo_coespecificos": True,
        "agrupamento": "par",
        "cardume_minimo": None,
        "nivel_natacao": "meio",
        "morde_barbatana": False,
        "barbatana_longa": False,
        "come_plantas": False,
        "come_invertebrados": False,
        "reef_safe": "sim",
        "alimentacao": "onivoro",
        "nivel_dificuldade": "medio",
        "expectativa_vida_anos": 10,
        "observacoes": "Territorial perto da anêmona. Casal estabelecido não aceita terceiros.",
    },
]


def executar():
    db = SessionLocal()
    criadas = ignoradas = 0

    try:
        for dados in ESPECIES:
            existe = (
                db.query(Especie)
                .filter(Especie.nome_cientifico == dados["nome_cientifico"])
                .first()
            )
            if existe:
                ignoradas += 1
                print(f"  ja existe  · {dados['nome_comum']}")
                continue

            db.add(Especie(**dados))
            criadas += 1
            print(f"  cadastrada · {dados['nome_comum']}")

        db.commit()
        print(f"\n{criadas} espécie(s) cadastrada(s), {ignoradas} ignorada(s).")

    except Exception as erro:
        db.rollback()
        print(f"\nErro: {erro}")
    finally:
        db.close()


if __name__ == "__main__":
    executar()