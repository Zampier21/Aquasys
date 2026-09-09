"""
Testes de unidade do reconhecimento de CPF e CNPJ.

É a regra que decide se quem está entrando é loja ou cliente, então erra
aqui e o login inteiro erra junto.
"""

from app.core.documento import (
    documento_valido,
    formatar_documento,
    somente_digitos,
    tipo_documento,
    validar_cnpj,
    validar_cpf,
)


class TestReconhecimento:
    def test_onze_digitos_e_cpf(self):
        assert tipo_documento("123.456.789-09") == "cpf"
        assert tipo_documento("12345678909") == "cpf"

    def test_quatorze_digitos_e_cnpj(self):
        assert tipo_documento("11.222.333/0001-81") == "cnpj"
        assert tipo_documento("11222333000181") == "cnpj"

    def test_tamanho_intermediario_nao_e_documento(self):
        assert tipo_documento("123456") is None
        assert tipo_documento("123456789012") is None
        assert tipo_documento("") is None

    def test_pontuacao_nao_conta(self):
        # É o que faz o login achar o usuário tanto com máscara quanto sem.
        assert somente_digitos("000.000.000-00") == "00000000000"
        assert somente_digitos("11.222.333/0001-81") == "11222333000181"


class TestDigitosVerificadores:
    def test_cpf_valido(self):
        assert validar_cpf("123.456.789-09")

    def test_cpf_com_digito_errado(self):
        assert not validar_cpf("123.456.789-00")

    def test_cpf_de_digitos_repetidos_e_recusado(self):
        # Passa na conta matemática, mas não existe na vida real.
        for repetido in ["111.111.111-11", "000.000.000-00", "999.999.999-99"]:
            assert not validar_cpf(repetido), repetido

    def test_cnpj_valido(self):
        assert validar_cnpj("11.222.333/0001-81")

    def test_cnpj_com_digito_errado(self):
        assert not validar_cnpj("11.222.333/0001-00")

    def test_cnpj_de_digitos_repetidos_e_recusado(self):
        assert not validar_cnpj("11.111.111/1111-11")

    def test_documento_valido_escolhe_a_regra_pelo_tamanho(self):
        assert documento_valido("123.456.789-09")
        assert documento_valido("11.222.333/0001-81")
        assert not documento_valido("123456")


class TestFormatacao:
    def test_aplica_mascara_de_cpf(self):
        assert formatar_documento("12345678909") == "123.456.789-09"

    def test_aplica_mascara_de_cnpj(self):
        assert formatar_documento("11222333000181") == "11.222.333/0001-81"

    def test_tamanho_invalido_volta_so_os_digitos(self):
        assert formatar_documento("123") == "123"

    def test_formatar_e_idempotente(self):
        uma_vez = formatar_documento("12345678909")
        assert formatar_documento(uma_vez) == uma_vez
