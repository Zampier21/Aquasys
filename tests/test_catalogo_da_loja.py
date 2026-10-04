"""Catálogo por loja: o que a importação grava e quem enxerga.

A importação deixou de ser só conferência. O que casa entra no estoque
da loja; o que falta vira espécie dela, marcada como não revisada. Duas
coisas precisam continuar valendo depois disso: o rascunho de uma loja
não pode vazar para outra, e o motor de compatibilidade não pode tratar
ficha não conferida como se fosse boa.
"""

import pytest

from app.models.especie import Especie, LojaEspecie
from app.services import importacao


def subir(client, cabecalho, texto, **params):
    return client.post(
        "/peixes/importar",
        content=texto.encode("utf-8"),
        headers={**cabecalho, "Content-Type": "text/csv"},
        params={"buscar": False, **params},
    )


@pytest.fixture
def catalogo(db):
    """Duas espécies curadas, sem dono, como as do seed."""
    especies = [
        Especie(nome_comum="Neon Tetra", nome_cientifico="Paracheirodon innesi",
                nomes_alternativos="tetra neon", ativo=True, revisada=True),
        Especie(nome_comum="Acará Bandeira",
                nome_cientifico="Pterophyllum scalare",
                nomes_alternativos="escalar", ativo=True, revisada=True),
        Especie(nome_comum="Acará Disco",
                nome_cientifico="Symphysodon aequifasciatus",
                ativo=True, revisada=True),
    ]
    for e in especies:
        db.add(e)
    db.flush()
    return especies


class TestGravacao:
    def test_conferir_nao_grava_nada(self, client, cab_loja, catalogo, db):
        antes = db.query(Especie).count()
        r = subir(client, cab_loja, "Neon Tetra\nKinguio\n")

        assert r.json()["aplicado"] is False
        assert r.json()["gravacao"] is None
        assert db.query(Especie).count() == antes
        assert db.query(LojaEspecie).count() == 0

    def test_aplicar_vincula_o_que_ja_existia(self, client, cab_loja, catalogo, db):
        r = subir(client, cab_loja, "Neon Tetra\nescalar\n", aplicar=True)
        corpo = r.json()

        assert corpo["aplicado"] is True
        assert corpo["gravacao"]["vinculados"] == 2
        assert corpo["gravacao"]["criados"] == 0
        assert db.query(LojaEspecie).count() == 2

    def test_aplicar_cria_rascunho_do_que_faltava(self, client, cab_loja, catalogo, db):
        corpo = subir(client, cab_loja, "Kinguio\n", aplicar=True).json()

        assert corpo["gravacao"]["criados"] == 1
        assert corpo["itens"][0]["situacao"] == "criado"

        criada = db.query(Especie).filter(Especie.nome_comum == "Kinguio").one()
        assert criada.revisada is False
        assert criada.dono_id is not None
        assert criada.nome_cientifico is None      # busca desligada no teste

    def test_o_ambiguo_fica_de_fora(self, client, cab_loja, catalogo, db):
        """Escolher entre bandeira e disco poria no estoque o peixe errado."""
        corpo = subir(client, cab_loja, "Acará\n", aplicar=True).json()

        assert corpo["gravacao"]["ignorados"] == 1
        assert corpo["gravacao"]["criados"] == 0
        assert db.query(LojaEspecie).count() == 0

    def test_importar_duas_vezes_nao_duplica(self, client, cab_loja, catalogo, db):
        lista = "Neon Tetra\nKinguio\n"
        subir(client, cab_loja, lista, aplicar=True)
        segunda = subir(client, cab_loja, lista, aplicar=True).json()

        assert segunda["gravacao"]["ja_estavam"] == 2
        assert segunda["gravacao"]["criados"] == 0
        assert db.query(LojaEspecie).count() == 2
        assert db.query(Especie).filter(Especie.nome_comum == "Kinguio").count() == 1

    def test_a_sugestao_liga_ao_catalogo_em_vez_de_duplicar(
        self, client, cab_loja, catalogo, db, monkeypatch
    ):
        """Nome popular diferente, mesma espécie: vincula, não cria outra."""
        from app.services import enriquecimento

        monkeypatch.setattr(
            enriquecimento, "sugerir",
            lambda nome: enriquecimento.Sugestao(
                nome_cientifico="Paracheirodon innesi",
                titulo="Tetra-néon", qid="Q1",
            ),
        )
        corpo = subir(client, cab_loja, "Cardinal Azul\n",
                      aplicar=True, buscar=True).json()

        assert corpo["gravacao"]["criados"] == 0
        assert corpo["gravacao"]["vinculados"] == 1
        assert db.query(Especie).filter(
            Especie.nome_comum == "Cardinal Azul"
        ).count() == 0

    def test_a_rede_fora_do_ar_nao_derruba_a_importacao(
        self, client, cab_loja, catalogo, db, monkeypatch
    ):
        from app.services import enriquecimento

        def cair(nome):
            raise enriquecimento.Indisponivel("sem rede")

        monkeypatch.setattr(enriquecimento, "sugerir", cair)
        corpo = subir(client, cab_loja, "Kinguio\n",
                      aplicar=True, buscar=True).json()

        assert corpo["gravacao"]["sem_busca"] is True
        assert corpo["gravacao"]["criados"] == 1


class TestQuemEnxerga:
    def test_a_outra_loja_nao_ve_o_rascunho(
        self, client, cab_loja, cab_outra_loja, catalogo
    ):
        subir(client, cab_loja, "Kinguio\n", aplicar=True)

        minhas = [e["nome_comum"] for e in
                  client.get("/peixes/", headers=cab_loja).json()]
        alheias = [e["nome_comum"] for e in
                   client.get("/peixes/", headers=cab_outra_loja).json()]

        assert "Kinguio" in minhas
        assert "Kinguio" not in alheias

    def test_o_cliente_da_loja_ve_o_rascunho_dela(
        self, client, cab_loja, cab_cliente, catalogo
    ):
        """É o ponto de a loja importar: o aquarista ver o que ela tem."""
        subir(client, cab_loja, "Kinguio\n", aplicar=True)

        do_cliente = [e["nome_comum"] for e in
                      client.get("/peixes/", headers=cab_cliente).json()]
        assert "Kinguio" in do_cliente

    def test_o_catalogo_curado_continua_visivel_a_todos(
        self, client, cab_outra_loja, catalogo
    ):
        nomes = [e["nome_comum"] for e in
                 client.get("/peixes/", headers=cab_outra_loja).json()]
        assert "Neon Tetra" in nomes

    def test_duas_lojas_importam_o_mesmo_peixe(
        self, client, cab_loja, cab_outra_loja, catalogo, db
    ):
        """Cada uma fica com o seu rascunho, sem esbarrar na outra."""
        assert subir(client, cab_loja, "Kinguio\n", aplicar=True).status_code == 200
        assert subir(
            client, cab_outra_loja, "Kinguio\n", aplicar=True
        ).status_code == 200
        assert db.query(Especie).filter(Especie.nome_comum == "Kinguio").count() == 2

    def test_a_conferencia_da_loja_nao_enxerga_o_rascunho_alheio(
        self, client, cab_loja, cab_outra_loja, catalogo
    ):
        subir(client, cab_loja, "Kinguio\n", aplicar=True)
        corpo = subir(client, cab_outra_loja, "Kinguio\n").json()
        assert corpo["nao_encontrados"] == 1


class TestMotorNaoConfiaEmFichaCrua:
    def test_especie_nao_revisada_nunca_sai_liberada(
        self, client, cab_loja, catalogo, db
    ):
        subir(client, cab_loja, "Kinguio\n", aplicar=True)
        criada = db.query(Especie).filter(Especie.nome_comum == "Kinguio").one()

        aquario = client.post(
            "/aquarios/",
            json={"nome": "Teste", "volume_litros": 200, "temperatura": 25,
                  "ph": 7.0, "tipo": "comunitario"},
            headers=cab_loja,
        ).json()

        analise = client.get(
            f"/peixes/{criada.id}/aquario/{aquario['id']}", headers=cab_loja
        ).json()

        assert analise["decisao"] == "requer_confirmacao"
        assert any(a["motivo"] == "ficha_incompleta" for a in analise["avisos"])

    def test_o_aviso_explica_o_que_falta(self, client, cab_loja, catalogo, db):
        subir(client, cab_loja, "Kinguio\n", aplicar=True)
        criada = db.query(Especie).filter(Especie.nome_comum == "Kinguio").one()

        aquario = client.post(
            "/aquarios/",
            json={"nome": "Teste", "volume_litros": 200, "temperatura": 25,
                  "ph": 7.0, "tipo": "comunitario"},
            headers=cab_loja,
        ).json()
        analise = client.get(
            f"/peixes/{criada.id}/aquario/{aquario['id']}", headers=cab_loja
        ).json()

        aviso = next(a for a in analise["avisos"]
                     if a["motivo"] == "ficha_incompleta")
        assert "não foi conferida" in aviso["mensagem"]

    def test_especie_curada_continua_podendo_ser_liberada(
        self, client, cab_loja, catalogo, db
    ):
        """A trava é da ficha crua, e não de todo mundo."""
        neon = catalogo[0]
        neon.temp_min, neon.temp_max = 20.0, 28.0
        neon.ph_min, neon.ph_max = 6.0, 7.5
        neon.tamanho_adulto_cm = 4.0
        neon.tipo_agua = "doce"
        db.flush()

        aquario = client.post(
            "/aquarios/",
            json={"nome": "Teste", "volume_litros": 200, "temperatura": 25,
                  "ph": 7.0, "tipo": "comunitario"},
            headers=cab_loja,
        ).json()
        analise = client.get(
            f"/peixes/{neon.id}/aquario/{aquario['id']}", headers=cab_loja
        ).json()

        assert not any(a["motivo"] == "ficha_incompleta"
                       for a in analise["avisos"])


class TestServicoIsolado:
    def test_o_catalogo_visivel_respeita_o_dono(self, db, loja, outra_loja):
        curada = Especie(nome_comum="Curada", ativo=True)
        minha = Especie(nome_comum="Minha", ativo=True, dono_id=loja.id)
        alheia = Especie(nome_comum="Alheia", ativo=True, dono_id=outra_loja.id)
        for e in (curada, minha, alheia):
            db.add(e)
        db.flush()

        nomes = {e.nome_comum
                 for e in importacao._catalogo_visivel(db, loja)}
        assert nomes == {"Curada", "Minha"}
