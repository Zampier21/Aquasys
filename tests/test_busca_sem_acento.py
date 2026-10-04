"""Busca do catálogo comparando sem acento.

A comparação saiu da extensão `unaccent` para a função embutida
`translate`. A extensão tratava todo o Unicode; o `translate` trata o
mapa que está escrito em `app/routers/peixes.py`. A troca só se
justifica se continuar acertando os nomes que existem de fato, que são
nome popular em português e nome científico em latim, e é isso que os
casos abaixo fixam.

Sem estes testes, uma letra esquecida no mapa viraria um peixe que não
aparece na busca, e ninguém descobriria até um cliente reclamar.
"""

import pytest

from app.models.especie import Especie


@pytest.fixture
def catalogo(db):
    especies = [
        Especie(nome_comum="Acará Bandeira",
                nome_cientifico="Pterophyllum scalare",
                nomes_alternativos="escalar", tipo_agua="doce",
                ativo=True, revisada=True),
        Especie(nome_comum="Molinésia", nome_cientifico="Poecilia sphenops",
                tipo_agua="doce", ativo=True, revisada=True),
        Especie(nome_comum="Peixe-palhaço", nome_cientifico="Amphiprion ocellaris",
                tipo_agua="marinho", ativo=True, revisada=True),
        Especie(nome_comum="Coridora Panda",
                nome_cientifico="Corydoras panda",
                nomes_alternativos="coridóra-panda", tipo_agua="doce",
                ativo=True, revisada=True),
        Especie(nome_comum="Botia Palhaço",
                nome_cientifico="Chromobotia macracanthus",
                tipo_agua="doce", ativo=True, revisada=True),
    ]
    for e in especies:
        db.add(e)
    db.flush()
    return especies


def nomes(client, cabecalho, **params):
    r = client.get("/peixes/", headers=cabecalho, params=params)
    assert r.status_code == 200, r.text
    return [e["nome_comum"] for e in r.json()]


class TestTermoSemAcento:
    def test_digitar_sem_acento_acha_o_acentuado(self, client, cab_loja, catalogo):
        """O caso comum: ninguém digita acento numa caixa de busca."""
        assert "Acará Bandeira" in nomes(client, cab_loja, busca="acara")

    def test_til_tambem(self, client, cab_loja, catalogo):
        assert "Peixe-palhaço" in nomes(client, cab_loja, busca="palhaco")

    def test_acento_agudo_no_meio(self, client, cab_loja, catalogo):
        assert "Molinésia" in nomes(client, cab_loja, busca="molinesia")


class TestTermoComAcento:
    def test_digitar_com_acento_tambem_acha(self, client, cab_loja, catalogo):
        assert "Acará Bandeira" in nomes(client, cab_loja, busca="acará")

    def test_acento_no_termo_acha_o_campo_sem_acento(
        self, client, cab_loja, catalogo
    ):
        """Buscar "coridóra" tem que achar "Coridora Panda"."""
        assert "Coridora Panda" in nomes(client, cab_loja, busca="coridóra")

    def test_cedilha_nos_dois_lados(self, client, cab_loja, catalogo):
        achados = nomes(client, cab_loja, busca="palhaço")
        assert "Peixe-palhaço" in achados
        assert "Botia Palhaço" in achados


class TestMaiusculas:
    def test_caixa_alta_no_termo(self, client, cab_loja, catalogo):
        assert "Acará Bandeira" in nomes(client, cab_loja, busca="ACARÁ")

    def test_caixa_misturada(self, client, cab_loja, catalogo):
        assert "Molinésia" in nomes(client, cab_loja, busca="MoLiNéSiA")


class TestNomeCientifico:
    def test_acha_pelo_genero(self, client, cab_loja, catalogo):
        assert "Acará Bandeira" in nomes(client, cab_loja, busca="pterophyllum")

    def test_acha_pelo_epiteto(self, client, cab_loja, catalogo):
        assert "Peixe-palhaço" in nomes(client, cab_loja, busca="ocellaris")

    def test_acha_pelo_nome_alternativo(self, client, cab_loja, catalogo):
        assert "Acará Bandeira" in nomes(client, cab_loja, busca="escalar")

    def test_dois_termos_exigem_os_dois(self, client, cab_loja, catalogo):
        achados = nomes(client, cab_loja, busca="acara bandeira")
        assert achados == ["Acará Bandeira"]

    def test_termo_que_nao_existe_nao_traz_nada(self, client, cab_loja, catalogo):
        assert nomes(client, cab_loja, busca="tubarao branco") == []


class TestFiltroDeAgua:
    def test_filtra_por_tipo_de_agua(self, client, cab_loja, catalogo):
        doces = nomes(client, cab_loja, tipo_agua="doce")

        assert "Molinésia" in doces
        assert "Peixe-palhaço" not in doces

    def test_o_filtro_ignora_caixa_e_acento(self, client, cab_loja, catalogo):
        """O valor chega da tela, e a tela pode mandar de qualquer jeito."""
        assert nomes(client, cab_loja, tipo_agua="MARINHO") == ["Peixe-palhaço"]

    def test_busca_e_filtro_juntos(self, client, cab_loja, catalogo):
        achados = nomes(client, cab_loja, busca="palhaco", tipo_agua="doce")
        assert achados == ["Botia Palhaço"]


class TestOMapaDeAcentos:
    def test_as_duas_listas_tem_o_mesmo_tamanho(self):
        """`translate` casa caractere com caractere pela posição.

        Se as duas cadeias tiverem tamanhos diferentes, o PostgreSQL
        simplesmente apaga as letras sobrando, e a busca passaria a
        errar em silêncio.
        """
        from app.routers.peixes import _COM_ACENTO, _SEM_ACENTO

        assert len(_COM_ACENTO) == len(_SEM_ACENTO)

    def test_cobre_todo_acento_do_portugues(self):
        """Nenhuma letra acentuada do português pode ficar de fora."""
        from app.routers.peixes import _COM_ACENTO

        for letra in "áàâãéêíóôõúüç":
            assert letra in _COM_ACENTO, letra
            assert letra.upper() in _COM_ACENTO, letra.upper()
