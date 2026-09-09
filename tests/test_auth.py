"""
Testes do login.

O login é a única porta pública do sistema junto com o health check, e é
onde se decide se quem entrou é loja ou cliente.
"""

from tests.conftest import SENHA


class TestLogin:
    def test_entra_com_mascara(self, client, loja):
        r = client.post(
            "/auth/login",
            json={"cpf_cnpj": "11.222.333/0001-81", "senha": SENHA},
        )
        assert r.status_code == 200
        assert r.json()["tipo_usuario"] == "dono"
        assert r.json()["documento"] == "cnpj"

    def test_entra_sem_mascara(self, client, loja):
        # O app manda só os dígitos; o banco guarda com máscara.
        r = client.post(
            "/auth/login", json={"cpf_cnpj": "11222333000181", "senha": SENHA}
        )
        assert r.status_code == 200

    def test_cliente_entra_pelo_mesmo_endereco(self, client, cliente):
        r = client.post(
            "/auth/login", json={"cpf_cnpj": cliente.cpf_cnpj, "senha": SENHA}
        )
        assert r.status_code == 200
        assert r.json()["tipo_usuario"] == "cliente"
        assert r.json()["documento"] == "cpf"

    def test_senha_errada(self, client, loja):
        r = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "outra"}
        )
        assert r.status_code == 401

    def test_documento_inexistente(self, client):
        r = client.post(
            "/auth/login", json={"cpf_cnpj": "99999999999", "senha": SENHA}
        )
        assert r.status_code == 401

    def test_tamanho_invalido_nem_consulta_o_banco(self, client):
        r = client.post("/auth/login", json={"cpf_cnpj": "123", "senha": SENHA})
        assert r.status_code == 400
        assert "11 dígitos" in r.json()["detail"]

    def test_conta_desativada_nao_entra(self, client, db, loja):
        # É assim que um assinante que parou de pagar perde o acesso.
        loja.ativo = False
        db.flush()

        r = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": SENHA}
        )
        assert r.status_code == 401

    def test_a_resposta_nao_devolve_a_senha(self, client, loja):
        corpo = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": SENHA}
        ).json()
        assert "senha" not in corpo
        assert "senha_hash" not in corpo


class TestProtecao:
    def test_rota_sem_token_e_recusada(self, client):
        # 401: falta credencial. (403 seria "tem credencial, mas não pode".)
        assert client.get("/aquarios/").status_code == 401

    def test_token_invalido_e_recusado(self, client):
        r = client.get(
            "/aquarios/", headers={"Authorization": "Bearer nao-e-um-token"}
        )
        assert r.status_code == 401

    def test_health_check_e_publico(self, client):
        assert client.get("/").status_code == 200
