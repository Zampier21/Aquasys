"""
Variedades de uma mesma espécie.

Duas coisas se verificam aqui. A primeira é de apresentação: o catálogo
lista só as bases, e as variedades aparecem dentro do card.

A segunda é a que importa de verdade. A herança dos campos de biologia é
MATERIALIZADA na linha da variedade, e não resolvida na leitura, porque
`_faixa_dos_habitantes` descarta quem tem o campo nulo — uma variedade
com `ph_min` em branco sumiria do cálculo da faixa ideal e o aquário
seria avaliado como se aquele peixe não estivesse lá. Os testes de
`TestHerancaChegaAosMotores` existem para que isso não volte a ser
possível sem alguém perceber.
"""

import pytest

from app.models.especie import Especie
from app.services import parametros as svc_parametros
from app.services import variedades as svc_variedades

BASE = dict(
    nome_comum="Acará Bandeira",
    nome_cientifico="Pterophyllum scalare",
    tipo_agua="doce",
    familia="Cichlidae",
    temp_min=24.0, temp_max=30.0,
    ph_min=6.0, ph_max=7.5,
    tamanho_adulto_cm=15.0,
    volume_minimo_l=120,
    comportamento="semi_agressivo",
    agrupamento="par",
    cardume_minimo=2,
    nivel_natacao="meio",
    nivel_dificuldade="medio",
    ativo=True,
)


@pytest.fixture
def acara(db) -> Especie:
    e = Especie(**BASE)
    db.add(e)
    db.flush()
    return e


def nova_variedade(db, base, nome, **diferencas) -> Especie:
    """Variedade como a loja a cadastraria: só o nome, e o resto herdado.

    Passa por `criar_variedade`, que copia a base ANTES de gravar. A
    versão anterior deste auxiliar gravava primeiro e sincronizava
    depois — e foi por isso que os testes não pegaram os booleanos
    ficando para trás: o próprio auxiliar reproduzia o defeito.
    """
    v = svc_variedades.criar_variedade(base, nome, **diferencas)
    db.add(v)
    db.flush()
    return v


# ═══════════════════════════════════════════════════════
# HERANÇA
# ═══════════════════════════════════════════════════════
class TestHeranca:
    def test_variedade_recebe_a_biologia_da_base(self, db, acara):
        v = nova_variedade(db, acara, "Acará Bandeira Leopardo Azul")

        assert v.ph_min == acara.ph_min
        assert v.ph_max == acara.ph_max
        assert v.temp_min == acara.temp_min
        assert v.tamanho_adulto_cm == acara.tamanho_adulto_cm
        assert v.cardume_minimo == acara.cardume_minimo
        assert v.nome_cientifico == acara.nome_cientifico

    def test_o_nome_da_variedade_nao_e_herdado(self, db, acara):
        v = nova_variedade(db, acara, "Acará Bandeira Marmorato")
        assert v.nome_comum == "Acará Bandeira Marmorato"

    def test_o_que_a_variedade_declara_prevalece(self, db, acara):
        """Um albino mais sensível mantém a faixa que declarou."""
        v = nova_variedade(db, acara, "Acará Bandeira Albino", ph_max=7.0)

        assert v.ph_max == 7.0          # o dela
        assert v.ph_min == acara.ph_min  # herdado

    def test_sincronizar_diz_o_que_preencheu(self, db, acara):
        v = Especie(nome_comum="Teste", variante_de_id=acara.id, ativo=True)
        db.add(v)
        db.flush()
        preenchidos = svc_variedades.sincronizar(v, acara)

        assert "ph_min" in preenchidos
        assert "nome_comum" not in preenchidos

    def test_propagar_completa_variedade_incompleta(self, db, acara):
        """Campo que a base ganhou depois desce para as variedades."""
        v = nova_variedade(db, acara, "Acará Bandeira Koi")
        v.expectativa_vida_anos = None
        acara.expectativa_vida_anos = 10
        db.flush()

        assert svc_variedades.propagar(acara, db) == 1
        assert v.expectativa_vida_anos == 10

    def test_propagar_nao_sobrescreve_o_que_ja_existe(self, db, acara):
        v = nova_variedade(db, acara, "Acará Bandeira Véu", tamanho_adulto_cm=12.0)
        acara.tamanho_adulto_cm = 15.0
        db.flush()
        svc_variedades.propagar(acara, db)

        assert v.tamanho_adulto_cm == 12.0


# ═══════════════════════════════════════════════════════
# A HERANÇA CHEGA AOS MOTORES
# ═══════════════════════════════════════════════════════
class TestHerancaChegaAosMotores:
    def test_variedade_entra_no_calculo_da_faixa(self, db, acara):
        """O motor descarta quem tem campo nulo. A variedade não pode ser
        descartada: ela é um peixe no aquário como qualquer outro."""
        v = nova_variedade(db, acara, "Acará Bandeira Leopardo Azul")

        campos = svc_parametros._CAMPOS_ESPECIE
        for chave, (campo_min, campo_max) in campos.items():
            assert getattr(v, campo_min) is not None, (
                f"{campo_min} nulo faria a variedade sumir do cálculo de {chave}"
            )
            assert getattr(v, campo_max) is not None

    def test_faixa_de_ph_com_variedade_e_igual_a_da_base(self, db, acara):
        v = nova_variedade(db, acara, "Acará Bandeira Marmorato")
        aquario = type("Aq", (), {"tipo": "comunitario", "ph": 7.0,
                                  "temperatura": 26.0, "volume_litros": 200})()

        so_base = svc_parametros.faixas_do_aquario(aquario, [acara])
        com_variedade = svc_parametros.faixas_do_aquario(aquario, [acara, v])

        ph_base = next(f for f in so_base if f.chave == "ph")
        ph_var = next(f for f in com_variedade if f.chave == "ph")
        assert (ph_base.minimo, ph_base.maximo) == (ph_var.minimo, ph_var.maximo)

    def test_variedade_mais_exigente_estreita_a_faixa(self, db, acara):
        """Se a variedade declara faixa própria, ela pesa na interseção."""
        v = nova_variedade(db, acara, "Acará Bandeira Albino", ph_max=6.8)
        aquario = type("Aq", (), {"tipo": "comunitario", "ph": 7.2,
                                  "temperatura": 26.0, "volume_litros": 200})()

        faixas = svc_parametros.faixas_do_aquario(aquario, [acara, v])
        ph = next(f for f in faixas if f.chave == "ph")
        assert ph.maximo == 6.8


# ═══════════════════════════════════════════════════════
# SEGURANÇA: O QUE A PRIMEIRA VERSÃO DEIXAVA PASSAR
# ═══════════════════════════════════════════════════════
BETTA = dict(
    nome_comum="Betta",
    nome_cientifico="Betta splendens",
    tipo_agua="doce",
    temp_min=24.0, temp_max=30.0,
    ph_min=6.0, ph_max=8.0,
    tamanho_adulto_cm=6.0,
    volume_minimo_l=20,
    comportamento="territorial",
    agressivo_coespecificos=True,
    barbatana_longa=True,
    agrupamento="solitario",
    nivel_natacao="superficie",
    ativo=True,
)


@pytest.fixture
def betta(db) -> Especie:
    e = Especie(**BETTA)
    db.add(e)
    db.flush()
    return e


class TestBooleanosHerdam:
    """Cinco colunas booleanas têm default=False no modelo.

    A primeira versão de `sincronizar` só copiava o que estava nulo. Se a
    variedade fosse gravada antes, o banco preenchia esses campos com
    False — e eles deixavam de ser nulos, e deixavam de ser herdados.
    Um Betta Halfmoon nasceria achando que convive com outros machos.
    """

    def test_briga_com_a_mesma_especie_e_herdada(self, db, betta):
        v = svc_variedades.criar_variedade(betta, "Betta Halfmoon")
        db.add(v)
        db.flush()
        assert v.agressivo_coespecificos is True

    def test_barbatana_longa_e_herdada(self, db, betta):
        v = svc_variedades.criar_variedade(betta, "Betta Crowntail")
        db.add(v)
        db.flush()
        assert v.barbatana_longa is True

    def test_booleano_declarado_pela_variedade_prevalece(self, db, betta):
        """O Plakat é justamente o Betta de nadadeira curta."""
        v = svc_variedades.criar_variedade(
            betta, "Betta Plakat", barbatana_longa=False
        )
        db.add(v)
        db.flush()
        assert v.barbatana_longa is False
        assert v.agressivo_coespecificos is True   # esse continua herdado

    @pytest.mark.parametrize("campo", [
        "agressivo_coespecificos", "morde_barbatana", "barbatana_longa",
        "come_plantas", "come_invertebrados",
    ])
    def test_nenhum_booleano_com_default_fica_para_tras(self, db, campo):
        """Vale para os cinco, e não só para os que o Betta usa."""
        base = Especie(nome_comum="Base", ativo=True, **{campo: True})
        db.add(base)
        db.flush()
        v = svc_variedades.criar_variedade(base, "Base Variedade")
        db.add(v)
        db.flush()
        assert getattr(v, campo) is True


class TestVariedadesSaoCoespecificas:
    """Duas variedades da mesma base são o mesmo animal.

    O motor barrava briga só entre indivíduos da mesma LINHA do catálogo.
    Sem variedades isso bastava, porque adicionar um segundo Betta caía em
    "edite a quantidade". Com variedades, Halfmoon e Crowntail são linhas
    diferentes — e dois machos iriam para o mesmo aquário.
    """

    def _avaliar(self, nova, habitantes, qtd=1):
        from app.services.compatibilidade import avaliar_adicao
        aquario = type("Aq", (), {"tipo": "comunitario", "ph": 7.0,
                                  "temperatura": 27.0, "volume_litros": 60})()
        return avaliar_adicao(nova=nova, quantidade=qtd, aquario=aquario,
                              habitantes=habitantes, excecoes={})

    def test_variedade_nova_em_aquario_com_outra_variedade(self, db, betta):
        halfmoon = svc_variedades.criar_variedade(betta, "Betta Halfmoon")
        crowntail = svc_variedades.criar_variedade(betta, "Betta Crowntail")
        db.add_all([halfmoon, crowntail])
        db.flush()

        r = self._avaliar(crowntail, habitantes=[(halfmoon, 1)])
        assert r["decisao"] == "bloqueado"
        assert any(a["motivo"] == "agressao" for a in r["avisos"])

    def test_variedade_em_aquario_com_a_propria_base(self, db, betta):
        halfmoon = svc_variedades.criar_variedade(betta, "Betta Halfmoon")
        db.add(halfmoon)
        db.flush()

        r = self._avaliar(halfmoon, habitantes=[(betta, 1)])
        assert r["decisao"] == "bloqueado"

    def test_base_em_aquario_com_uma_variedade(self, db, betta):
        halfmoon = svc_variedades.criar_variedade(betta, "Betta Halfmoon")
        db.add(halfmoon)
        db.flush()

        r = self._avaliar(betta, habitantes=[(halfmoon, 1)])
        assert r["decisao"] == "bloqueado"

    def test_especies_diferentes_nao_contam_como_a_mesma(self, db, betta, acara):
        """O conserto não pode transformar todo vizinho em coespecífico."""
        r = self._avaliar(betta, habitantes=[(acara, 1)])
        assert not any(
            "mesma espécie" in a["mensagem"] for a in r["avisos"]
        )

    def test_variedades_pacificas_convivem(self, db, acara):
        """Coespecífico só é problema para quem briga com a própria espécie."""
        marmorato = svc_variedades.criar_variedade(acara, "Acará Bandeira Marmorato")
        koi = svc_variedades.criar_variedade(acara, "Acará Bandeira Koi")
        db.add_all([marmorato, koi])
        db.flush()

        r = self._avaliar(koi, habitantes=[(marmorato, 2)], qtd=2)
        assert not any(a["motivo"] == "agressao" for a in r["avisos"])


# ═══════════════════════════════════════════════════════
# APRESENTAÇÃO
# ═══════════════════════════════════════════════════════
class TestNomeCurto:
    @pytest.mark.parametrize("nome,esperado", [
        ("Acará Bandeira Leopardo Azul", "Leopardo Azul"),
        ("Acará Bandeira Marmorato", "Marmorato"),
        ("acará bandeira koi", "koi"),
        ("Acará Bandeira — Véu", "Véu"),
        ("Platinum", "Platinum"),          # não começa pelo nome da base
        ("Acará Bandeira", "Acará Bandeira"),  # sobraria vazio: mantém
    ])
    def test_tira_o_nome_da_base(self, db, acara, nome, esperado):
        v = Especie(nome_comum=nome, variante_de_id=acara.id, ativo=True)
        assert svc_variedades.nome_curto(v, acara) == esperado


class TestCatalogo:
    def test_lista_so_as_bases(self, client, db, acara, cab_loja):
        nova_variedade(db, acara, "Acará Bandeira Leopardo Azul")
        nova_variedade(db, acara, "Acará Bandeira Marmorato")

        lista = client.get("/peixes/", headers=cab_loja).json()
        nomes = [e["nome_comum"] for e in lista]

        assert "Acará Bandeira" in nomes
        assert "Acará Bandeira Marmorato" not in nomes

    def test_as_variedades_vao_dentro_do_card(self, client, db, acara, cab_loja):
        nova_variedade(db, acara, "Acará Bandeira Leopardo Azul")
        nova_variedade(db, acara, "Acará Bandeira Marmorato")

        lista = client.get("/peixes/", headers=cab_loja).json()
        card = next(e for e in lista if e["nome_comum"] == "Acará Bandeira")

        assert len(card["variedades"]) == 2
        assert sorted(v["nome_curto"] for v in card["variedades"]) == [
            "Leopardo Azul", "Marmorato"
        ]

    def test_especie_sem_variedade_traz_lista_vazia(self, client, acara, cab_loja):
        lista = client.get("/peixes/", headers=cab_loja).json()
        card = next(e for e in lista if e["nome_comum"] == "Acará Bandeira")
        assert card["variedades"] == []

    def test_buscar_pela_variedade_acha_a_base(self, client, db, acara, cab_loja):
        """Procurar "marmorato" não pode devolver lista vazia só porque a
        variedade não aparece como item próprio."""
        nova_variedade(db, acara, "Acará Bandeira Marmorato")

        lista = client.get("/peixes/?busca=marmorato", headers=cab_loja).json()
        assert [e["nome_comum"] for e in lista] == ["Acará Bandeira"]
        assert lista[0]["variedades"][0]["nome_curto"] == "Marmorato"

    def test_variedade_nao_aparece_entre_as_compativeis(
        self, client, db, acara, cab_loja
    ):
        nova_variedade(db, acara, "Acará Bandeira Marmorato")
        aquario = client.post(
            "/aquarios/",
            json={"nome": "Teste", "volume_litros": 200, "temperatura": 26,
                  "ph": 7.0, "tipo": "comunitario"},
            headers=cab_loja,
        ).json()

        r = client.get(f"/peixes/compativeis/{aquario['id']}", headers=cab_loja)
        nomes = [c["nome_comum"] for c in r.json()]
        assert "Acará Bandeira" in nomes
        assert "Acará Bandeira Marmorato" not in nomes


# ═══════════════════════════════════════════════════════
# O ÍNDICE ÚNICO DE NOME CIENTÍFICO
# ═══════════════════════════════════════════════════════
class TestNomeCientificoUnico:
    """O banco real tinha um índice único em nome científico que nenhum
    arquivo do repositório declarava. O banco de teste, montado pelos
    modelos, não o tinha — e os testes de variedade passavam enquanto o
    banco real recusava o primeiro cadastro inteiro. Declarado no modelo,
    ele existe aqui também, e estes testes falhariam se sumisse de novo.
    """

    def test_varias_variedades_compartilham_o_cientifico(self, db, acara):
        for nome in ("Acará Bandeira Marmorato", "Acará Bandeira Koi",
                     "Acará Bandeira Albino"):
            nova_variedade(db, acara, nome)
        db.flush()   # não pode estourar

        mesmas = db.query(Especie).filter(
            Especie.nome_cientifico == acara.nome_cientifico
        ).count()
        assert mesmas == 4   # a base e as três variedades

    def test_duas_bases_com_o_mesmo_cientifico_sao_recusadas(self, db, acara):
        """A regra original continua valendo para quem ela se destinava."""
        from sqlalchemy.exc import IntegrityError

        repetida = Especie(nome_comum="Peixe Anjo", ativo=True,
                           nome_cientifico=acara.nome_cientifico.upper())
        # Savepoint, e não db.rollback(): o rollback da sessão desfaria a
        # transação externa que a fixture usa para isolar um teste do outro.
        ponto = db.begin_nested()
        db.add(repetida)
        with pytest.raises(IntegrityError):
            db.flush()
        ponto.rollback()
