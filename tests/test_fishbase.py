"""Preenchimento da ficha pela FishBase.

Nenhum caso aqui toca a rede, tirando o último, que está marcado como
`rede` e fica fora da suíte normal. O snapshot da FishBase tem nove
megabytes, e baixá-lo a cada execução transformaria a suíte num teste
de banda.

O que se prova aqui é o que pode quebrar em silêncio: a tradução dos
sinalizadores de água, a escolha entre vários estoques da mesma
espécie, o arredondamento, e a regra de nunca sobrescrever o que uma
pessoa digitou.
"""

import pytest

from app.models.especie import Especie
from app.services import fishbase


@pytest.fixture(autouse=True)
def sem_indice_herdado():
    """Cada caso monta o seu índice, e nenhum herda o do anterior."""
    fishbase.esquecer()
    yield
    fishbase.esquecer()


def ficha(**campos) -> fishbase.Ficha:
    base = dict(spec_code=1, nome_cientifico="Teste exemplo")
    base.update(campos)
    return fishbase.Ficha(**base)


# ═══════════════════════════════════════════════════════
# TRADUÇÃO DO TIPO DE ÁGUA
# ═══════════════════════════════════════════════════════
class TestTipoDeAgua:
    def test_doce(self):
        assert fishbase._agua(-1, 0, 0) == "doce"

    def test_salobra(self):
        assert fishbase._agua(0, -1, 0) == "salobra"

    def test_marinho(self):
        assert fishbase._agua(0, 0, -1) == "marinho"

    def test_doce_ganha_de_salobra(self):
        """O kinguio é marcado nos dois, e para o aquarismo é de doce."""
        assert fishbase._agua(-1, -1, 0) == "doce"

    def test_sem_sinalizador_nenhum_fica_nulo(self):
        assert fishbase._agua(0, 0, 0) is None


# ═══════════════════════════════════════════════════════
# ESCOLHA DO ESTOQUE
# ═══════════════════════════════════════════════════════
class TestMelhorEstoque:
    def test_prefere_a_linha_da_especie_em_geral(self):
        """O caso do kinguio: quatro estoques, três de subespécie."""
        linhas = [
            {"Level": "subspecies", "pHMin": None},
            {"Level": "species in general", "pHMin": 6.0},
            {"Level": "subspecies", "pHMin": None},
        ]
        assert fishbase._melhor_estoque(linhas)["pHMin"] == 6.0

    def test_sem_a_linha_geral_usa_a_primeira(self):
        linhas = [{"Level": "subspecies", "pHMin": 7.0}]
        assert fishbase._melhor_estoque(linhas)["pHMin"] == 7.0

    def test_lista_vazia_devolve_dicionario_vazio(self):
        assert fishbase._melhor_estoque([]) == {}

    def test_o_rotulo_e_comparado_sem_depender_de_caixa(self):
        linhas = [
            {"Level": "subspecies", "pHMin": None},
            {"Level": "Species In General", "pHMin": 6.5},
        ]
        assert fishbase._melhor_estoque(linhas)["pHMin"] == 6.5


# ═══════════════════════════════════════════════════════
# ARREDONDAMENTO
# ═══════════════════════════════════════════════════════
class TestArredondamento:
    def test_corta_o_ruido_do_float_de_32_bits(self):
        """O pH da molinésia chegava como 8.19999980926514."""
        assert fishbase._arredondar(8.19999980926514) == 8.2

    def test_nulo_continua_nulo(self):
        assert fishbase._arredondar(None) is None

    def test_inteiro_vira_float(self):
        assert fishbase._arredondar(7) == 7.0


# ═══════════════════════════════════════════════════════
# CONSULTA
# ═══════════════════════════════════════════════════════
class TestConsulta:
    @pytest.fixture
    def indice(self, monkeypatch):
        dados = {
            "paracheirodon innesi": ficha(
                spec_code=4714, nome_cientifico="Paracheirodon innesi",
                tamanho_adulto_cm=2.22, tipo_agua="doce",
                ph_min=5.0, ph_max=7.0, dgh_min=1.0, dgh_max=2.0,
                clima="tropical",
            ),
        }
        monkeypatch.setattr(fishbase, "_indice", dados)
        return dados

    def test_acha_pelo_nome_cientifico(self, indice):
        assert fishbase.consultar("Paracheirodon innesi").spec_code == 4714

    def test_nao_depende_de_caixa_nem_de_espaco_sobrando(self, indice):
        assert fishbase.consultar("  PARACHEIRODON   innesi ") is not None

    def test_nome_que_nao_existe_devolve_nulo(self, indice):
        assert fishbase.consultar("Inventus fictus") is None

    def test_nome_nulo_devolve_nulo_sem_consultar(self, indice):
        assert fishbase.consultar(None) is None
        assert fishbase.consultar("   ") is None

    def test_nao_faz_busca_aproximada(self, indice):
        """Nome científico errado por uma letra costuma ser outro peixe."""
        assert fishbase.consultar("Paracheirodon innesii") is None

    def test_a_pagina_de_credito_aponta_para_a_especie(self, indice):
        f = fishbase.consultar("Paracheirodon innesi")
        assert f.pagina.endswith("/4714.html")
        assert "CC BY-NC" in f.fonte


# ═══════════════════════════════════════════════════════
# PREENCHIMENTO
# ═══════════════════════════════════════════════════════
class TestPreencher:
    def test_preenche_o_que_estava_vazio(self):
        especie = Especie(nome_comum="Neon")
        campos = ficha(tamanho_adulto_cm=2.2, tipo_agua="doce",
                       ph_min=5.0, ph_max=7.0,
                       clima="tropical").preencher(especie)

        assert especie.tamanho_adulto_cm == 2.2
        assert especie.tipo_agua == "doce"
        assert especie.clima == "tropical"
        assert set(campos) == {"tamanho_adulto_cm", "tipo_agua",
                               "ph_min", "ph_max", "clima"}

    def test_nao_sobrescreve_o_que_a_pessoa_digitou(self):
        """O que a loja mediu vale mais do que o que veio de fora."""
        especie = Especie(nome_comum="Neon", tamanho_adulto_cm=4.0)
        campos = ficha(tamanho_adulto_cm=2.2, ph_min=5.0).preencher(especie)

        assert especie.tamanho_adulto_cm == 4.0
        assert "tamanho_adulto_cm" not in campos
        assert especie.ph_min == 5.0

    def test_grava_o_credito_quando_preencheu_algo(self):
        especie = Especie(nome_comum="Neon")
        ficha(ph_min=5.0).preencher(especie)
        assert especie.fonte_dados == fishbase.ATRIBUICAO

    def test_nao_grava_credito_quando_nao_preencheu_nada(self):
        """Sem dado nosso na ficha, não há o que atribuir."""
        especie = Especie(nome_comum="Neon", ph_min=6.0)
        campos = ficha(ph_min=5.0).preencher(especie)

        assert campos == []
        assert especie.fonte_dados is None

    def test_a_temperatura_nunca_e_preenchida(self):
        """A faixa da FishBase é de sobrevivência, não de aquário.

        Para o kinguio ela vai de 0 a 41 graus, e gravada como faixa de
        aquário aprovaria peixe de água fria num aquário de disco. Nem
        a Ficha carrega esses campos.
        """
        especie = Especie(nome_comum="Kinguio")
        ficha(clima="subtropical", tamanho_adulto_cm=48.0).preencher(especie)

        assert especie.temp_min is None
        assert especie.temp_max is None
        assert especie.clima == "subtropical"
        assert not hasattr(fishbase.Ficha, "temp_min")


# ═══════════════════════════════════════════════════════
# DENTRO DA IMPORTAÇÃO
# ═══════════════════════════════════════════════════════
def subir(client, cabecalho, texto, **params):
    return client.post(
        "/peixes/importar",
        content=texto.encode("utf-8"),
        headers={**cabecalho, "Content-Type": "text/csv"},
        params={"buscar": False, **params},
    )


class TestNaImportacao:
    @pytest.fixture
    def com_cientifico(self, monkeypatch):
        """A busca resolve o nome, e a FishBase preenche a ficha."""
        from app.services import enriquecimento

        monkeypatch.setattr(
            enriquecimento, "sugerir",
            lambda nome: enriquecimento.Sugestao(
                nome_cientifico="Puntigrus tetrazona",
                titulo="Barbo-sumatra", qid="Q2",
            ),
        )
        monkeypatch.setattr(
            fishbase, "consultar",
            lambda c: ficha(
                spec_code=4772, nome_cientifico=c,
                tamanho_adulto_cm=7.0, tipo_agua="doce",
                ph_min=6.0, ph_max=8.0, clima="tropical",
            ),
        )

    def test_a_especie_criada_ja_vem_com_as_medidas(
        self, client, cab_loja, db, com_cientifico
    ):
        corpo = subir(client, cab_loja, "Barbo Tigre\n",
                      aplicar=True, buscar=True).json()

        assert corpo["gravacao"]["criados"] == 1
        assert corpo["gravacao"]["com_ficha"] == 1

        criada = db.query(Especie).filter(
            Especie.nome_comum == "Barbo Tigre"
        ).one()
        assert criada.tamanho_adulto_cm == 7.0
        assert criada.tipo_agua == "doce"
        assert criada.clima == "tropical"
        assert criada.fonte_dados == fishbase.ATRIBUICAO

    def test_continua_nao_revisada_mesmo_com_a_ficha(
        self, client, cab_loja, db, com_cientifico
    ):
        """Faltam temperamento, cardume e a faixa em graus."""
        subir(client, cab_loja, "Barbo Tigre\n", aplicar=True, buscar=True)

        criada = db.query(Especie).filter(
            Especie.nome_comum == "Barbo Tigre"
        ).one()
        assert criada.revisada is False
        assert criada.comportamento is None
        assert criada.cardume_minimo is None

    def test_sem_nome_cientifico_nao_consulta(self, client, cab_loja, db):
        """Sem o nome científico não há como procurar na FishBase."""
        corpo = subir(client, cab_loja, "Peixe Inventado\n",
                      aplicar=True).json()

        assert corpo["gravacao"]["criados"] == 1
        assert corpo["gravacao"]["com_ficha"] == 0

        criada = db.query(Especie).filter(
            Especie.nome_comum == "Peixe Inventado"
        ).one()
        assert criada.fonte_dados is None

    def test_fishbase_fora_do_ar_nao_derruba_a_importacao(
        self, client, cab_loja, db, monkeypatch
    ):
        from app.services import enriquecimento

        monkeypatch.setattr(
            enriquecimento, "sugerir",
            lambda nome: enriquecimento.Sugestao(
                nome_cientifico="Puntigrus tetrazona",
                titulo="Barbo", qid="Q2",
            ),
        )

        def cair(cientifico):
            raise fishbase.Indisponivel("sem rede")

        monkeypatch.setattr(fishbase, "consultar", cair)
        corpo = subir(client, cab_loja, "Barbo Tigre\n",
                      aplicar=True, buscar=True).json()

        assert corpo["gravacao"]["sem_fishbase"] is True
        assert corpo["gravacao"]["criados"] == 1
        assert corpo["gravacao"]["com_ficha"] == 0

    def test_a_queda_e_tentada_uma_vez_so(
        self, client, cab_loja, monkeypatch
    ):
        """A primeira consulta baixa o snapshot inteiro.

        Insistir a cada nome tentaria baixar nove megabytes por peixe
        numa lista que pode ter centenas.
        """
        from app.services import enriquecimento

        monkeypatch.setattr(
            enriquecimento, "sugerir",
            lambda nome: enriquecimento.Sugestao(
                nome_cientifico="Especie " + nome.lower(),
                titulo=nome, qid="Q3",
            ),
        )

        tentativas = []

        def cair(cientifico):
            tentativas.append(cientifico)
            raise fishbase.Indisponivel("sem rede")

        monkeypatch.setattr(fishbase, "consultar", cair)
        subir(client, cab_loja, "Um\nDois\nTres\n",
              aplicar=True, buscar=True)

        assert len(tentativas) == 1

    def test_a_especie_que_nao_esta_na_fishbase_e_criada_igual(
        self, client, cab_loja, db, monkeypatch
    ):
        from app.services import enriquecimento

        monkeypatch.setattr(
            enriquecimento, "sugerir",
            lambda nome: enriquecimento.Sugestao(
                nome_cientifico="Inventus fictus", titulo="x", qid="Q4",
            ),
        )
        monkeypatch.setattr(fishbase, "consultar", lambda c: None)

        corpo = subir(client, cab_loja, "Peixe Novo\n",
                      aplicar=True, buscar=True).json()

        assert corpo["gravacao"]["criados"] == 1
        assert corpo["gravacao"]["com_ficha"] == 0
        assert corpo["gravacao"]["sem_fishbase"] is False


# ═══════════════════════════════════════════════════════
# CONTRA A FISHBASE DE VERDADE
# ═══════════════════════════════════════════════════════
@pytest.mark.rede
class TestContraOServicoReal:
    """Fora da suíte normal. Rode com: python -m pytest -m rede

    Serve para descobrir, antes do usuário, que o endereço mudou, que a
    versão do snapshot saiu do ar ou que renomearam uma coluna.
    """

    def test_o_snapshot_responde_e_tem_as_colunas(self):
        indice = fishbase.carregar()
        assert len(indice) > 30000

    def test_o_neon_vem_com_a_ficha_esperada(self):
        f = fishbase.consultar("Paracheirodon innesi")

        assert f is not None
        assert f.tipo_agua == "doce"
        assert f.clima == "tropical"
        assert 1.5 < f.tamanho_adulto_cm < 5.0
        assert 4.0 <= f.ph_min <= 6.5

    def test_o_kinguio_vem_subtropical_e_nao_tropical(self):
        """É o caso que motivou não importar a temperatura."""
        f = fishbase.consultar("Carassius auratus")

        assert f is not None
        assert f.clima == "subtropical"
        assert f.tipo_agua == "doce"
