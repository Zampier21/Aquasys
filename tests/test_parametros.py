import pytest

from app.services import parametros


class AquarioFalso:
    """O avaliador só lê nome e tipo — não precisa do banco."""

    def __init__(self, tipo=None, ph=7.0, temperatura=26.0, nome="Teste"):
        self.nome = nome
        self.tipo = tipo
        self.ph = ph
        self.temperatura = temperatura


class MedicaoFalsa:
    def __init__(self, amonia=0.0, nitrito=0.0, nitrato=10.0):
        self.amonia_ppm = amonia
        self.nitrito_ppm = nitrito
        self.nitrato_ppm = nitrato


def chaves(problemas):
    return {p["parametro"] for p in problemas}


class TestFaixaPorTipo:
    def test_marinho_a_ph_8_esta_saudavel(self):
        # O caso que já apareceu quebrado no app.
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="marinho", ph=8.0), MedicaoFalsa()
        )
        assert "ph" not in chaves(problemas)

    def test_comunitario_a_ph_8_esta_fora(self):
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=8.0), MedicaoFalsa()
        )
        assert "ph" in chaves(problemas)

    def test_marinho_a_ph_7_esta_fora(self):
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="marinho", ph=7.0), MedicaoFalsa()
        )
        assert "ph" in chaves(problemas)

    def test_plantado_aceita_ph_mais_acido_que_o_comunitario(self):
        acido = 6.2
        plantado, _ = parametros.avaliar(
            AquarioFalso(tipo="plantado", ph=acido), MedicaoFalsa()
        )
        comunitario, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=acido), MedicaoFalsa()
        )
        assert "ph" not in chaves(plantado)
        assert "ph" in chaves(comunitario)

    def test_sem_tipo_cai_no_comunitario(self):
        sem_tipo, _ = parametros.avaliar(
            AquarioFalso(tipo=None, ph=8.0), MedicaoFalsa()
        )
        assert "ph" in chaves(sem_tipo)

    def test_tipo_desconhecido_nao_quebra(self):
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="inventado", ph=6.8), MedicaoFalsa()
        )
        assert isinstance(problemas, list)


class TestToxicos:
    @pytest.mark.parametrize("tipo", ["comunitario", "marinho", "plantado"])
    def test_amonia_acima_de_zero_e_problema_em_qualquer_tipo(self, tipo):
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo=tipo), MedicaoFalsa(amonia=0.25)
        )
        assert "amonia" in chaves(problemas)

    @pytest.mark.parametrize("tipo", ["comunitario", "marinho", "plantado"])
    def test_nitrito_acima_de_zero_e_problema_em_qualquer_tipo(self, tipo):
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo=tipo), MedicaoFalsa(nitrito=0.1)
        )
        assert "nitrito" in chaves(problemas)

    def test_marinho_tolera_menos_nitrato_que_agua_doce(self):
        nitrato = 30.0
        marinho, _ = parametros.avaliar(
            AquarioFalso(tipo="marinho", ph=8.2, temperatura=26),
            MedicaoFalsa(nitrato=nitrato),
        )
        doce, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=6.8), MedicaoFalsa(nitrato=nitrato)
        )
        assert "nitrato" in chaves(marinho)
        assert "nitrato" not in chaves(doce)


class TestMensagem:
    def test_diz_o_quanto_esta_fora(self):
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=7.3, nome="Comunitário"),
            MedicaoFalsa(),
        )
        mensagem = next(p["mensagem"] for p in problemas if p["parametro"] == "ph")
        # É o texto que vai para o alerta e para a notificação do celular.
        assert "0.3 acima do ideal" in mensagem
        assert "Comunitário" in mensagem

    def test_sem_medicao_o_parametro_nao_e_avaliado(self):
        # Nem aprovado nem reprovado: fica fora da conta da saúde geral.
        problemas, avaliados = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=6.8), None
        )
        assert avaliados == 2  # só temperatura e pH vêm do aquário
        assert problemas == []


class TestFaixaEmTexto:
    def test_texto_muda_conforme_o_tipo(self):
        marinho = parametros.faixas_em_texto(AquarioFalso(tipo="marinho"))
        comunitario = parametros.faixas_em_texto(AquarioFalso(tipo="comunitario"))
        assert marinho["ph"] == "8.0 – 8.4"
        assert comunitario["ph"] == "6.5 – 7.0"

    def test_toxico_tem_texto_proprio(self):
        faixas = parametros.faixas_em_texto(AquarioFalso(tipo="comunitario"))
        assert faixas["amonia"] == "0 ppm — sempre zero"
        assert faixas["nitrato"].startswith("Abaixo de")


class EspecieFalsa:
    """Só os campos que o cálculo da faixa lê do catálogo."""

    def __init__(self, nome, ph=(6.0, 7.5), temp=(24.0, 28.0)):
        self.nome_comum = nome
        self.ph_min, self.ph_max = ph
        self.temp_min, self.temp_max = temp


class TestFaixaSegueOsPeixes:
    ALCALINOS = [
        EspecieFalsa("Molinésia", ph=(7.0, 8.5)),
        EspecieFalsa("Platy", ph=(7.0, 8.3)),
    ]

    def test_comunitario_de_peixes_alcalinos_nao_gera_alerta(self):
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=8.2), MedicaoFalsa(), self.ALCALINOS
        )
        assert "ph" not in chaves(problemas)

    def test_o_mesmo_aquario_vazio_volta_a_seguir_o_tipo(self):
        # Sem peixe não há o que respeitar: vale a faixa do comunitário.
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=8.2), MedicaoFalsa()
        )
        assert "ph" in chaves(problemas)

    def test_faixa_e_a_intersecao_das_tolerancias(self):
        # A mesma água serve os dois ao mesmo tempo: 7.0 – 8.3.
        faixas = parametros.faixas_em_texto(
            AquarioFalso(tipo="comunitario"), self.ALCALINOS
        )
        assert faixas["ph"] == "7.0 – 8.3"

    def test_peixe_acido_no_comunitario_continua_sendo_apontado(self):
        # A regra vale nos dois sentidos: não é só afrouxar.
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=7.3),
            MedicaoFalsa(),
            [EspecieFalsa("Neon Tetra", ph=(5.5, 7.0))],
        )
        assert "ph" in chaves(problemas)

    def test_especie_sem_dado_no_catalogo_nao_apaga_a_faixa(self):
        sem_ph = EspecieFalsa("Misteriosa")
        sem_ph.ph_min = sem_ph.ph_max = None

        faixas = parametros.faixas_em_texto(AquarioFalso(tipo="marinho"), [sem_ph])
        assert faixas["ph"] == "8.0 – 8.4"

    def test_exigencias_que_nao_se_cruzam_nao_viram_alerta_de_parametro(self):
        # Neon (ácido) com Molinésia (alcalina): não existe pH que sirva
        # aos dois. O problema é a combinação, e quem aponta isso é a aba
        # Peixes — errado seria acusar a água do cliente.
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario", ph=7.0),
            MedicaoFalsa(),
            [EspecieFalsa("Neon Tetra", ph=(5.5, 7.0)),
             EspecieFalsa("Molinésia", ph=(7.5, 8.5))],
        )
        assert "ph" not in chaves(problemas)

    def test_amonia_nao_depende_de_quem_mora_no_aquario(self):
        # Veneno é veneno para qualquer peixe: continua vindo do tipo.
        problemas, _ = parametros.avaliar(
            AquarioFalso(tipo="comunitario"),
            MedicaoFalsa(amonia=0.25),
            self.ALCALINOS,
        )
        assert "amonia" in chaves(problemas)


class TestEscalaDePh:
    """O cliente pediu para entender a escala, não decorar um intervalo."""

    @pytest.mark.parametrize(
        "valor,esperado",
        [
            (0.0, "ácida"), (6.5, "ácida"), (6.8, "ácida"),
            (6.9, "neutra"), (7.0, "neutra"), (7.1, "neutra"),
            (7.2, "alcalina"), (8.2, "alcalina"), (14.0, "alcalina"),
        ],
    )
    def test_classifica_o_valor_medido(self, valor, esperado):
        assert parametros.classificar_ph(valor) == esperado

    def test_ph_sempre_mostra_a_casa_decimal(self):
        faixas = parametros.faixas_em_texto(
            AquarioFalso(tipo="comunitario"),
            [EspecieFalsa("Platy", ph=(7.0, 8.0))],
        )
        assert faixas["ph"] == "7.0 – 8.0"


class TestExplicacao:
    """A frase que a tela mostra no lugar do intervalo cru."""

    def test_erro_cita_o_peixe_e_o_motivo(self):
        textos = parametros.explicar(
            AquarioFalso(tipo="comunitario", ph=7.3),
            MedicaoFalsa(),
            [EspecieFalsa("Neon Tetra", ph=(5.5, 7.0))],
        )
        assert "Neon Tetra" in textos["ph"]
        assert "mais ácida" in textos["ph"]
        assert "7.3" in textos["ph"] and "alcalina" in textos["ph"]

    def test_parametro_certo_confirma_em_vez_de_acusar(self):
        textos = parametros.explicar(
            AquarioFalso(tipo="comunitario", ph=6.8),
            MedicaoFalsa(),
            [EspecieFalsa("Neon Tetra", ph=(5.5, 7.0))],
        )
        assert "errado" not in textos["ph"]
        assert "ácida" in textos["ph"]

    def test_sem_peixes_a_explicacao_fala_do_tipo(self):
        textos = parametros.explicar(
            AquarioFalso(tipo="comunitario", ph=8.2), MedicaoFalsa()
        )
        assert "tipo de aquário" in textos["ph"]

    def test_todo_parametro_medido_ganha_uma_frase(self):
        textos = parametros.explicar(AquarioFalso(tipo="doce"), MedicaoFalsa())
        assert set(textos) == {
            "temperatura", "ph", "amonia", "nitrito", "nitrato",
        }
