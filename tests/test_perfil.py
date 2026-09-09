"""
Testes do perfil — a tela de Configurações.

Duas coisas importam aqui e são testadas com insistência: ninguém alcança
a conta de outra pessoa (todas as rotas agem só sobre o token), e trocar
senha exige a senha atual mesmo com token válido.
"""

import base64


from app.core.security import verificar_senha

# 1x1 pixel, o menor PNG válido que existe — serve para testar o caminho
# feliz sem carregar arquivo nenhum.
PNG_MINIMO = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae"
        "426082"
    )
).decode()


class TestLeitura:
    def test_devolve_os_dados_da_conta_logada(self, client, cab_loja, loja):
        perfil = client.get("/perfil/", headers=cab_loja).json()
        assert perfil["nome"] == loja.nome
        assert perfil["tipo"] == "dono"
        assert perfil["documento_tipo"] == "cnpj"

    def test_documento_vem_com_mascara_para_exibir(self, client, cab_cliente):
        perfil = client.get("/perfil/", headers=cab_cliente).json()
        assert perfil["documento_tipo"] == "cpf"
        assert "." in perfil["documento"] and "-" in perfil["documento"]

    def test_sem_token_nao_ha_perfil(self, client):
        assert client.get("/perfil/").status_code == 401


class TestNomeEEmail:
    def test_muda_o_nome_exibido(self, client, cab_loja):
        r = client.patch("/perfil/", json={"nome": "Aquário Central"}, headers=cab_loja)
        assert r.status_code == 200
        assert r.json()["nome"] == "Aquário Central"
        assert client.get("/perfil/", headers=cab_loja).json()["nome"] == "Aquário Central"

    def test_nome_em_branco_e_recusado(self, client, cab_loja):
        # O nome aparece no topo de toda tela: vazio ali não é opção.
        r = client.patch("/perfil/", json={"nome": "   "}, headers=cab_loja)
        assert r.status_code == 400

    def test_nome_curto_demais_e_recusado(self, client, cab_loja):
        assert client.patch("/perfil/", json={"nome": "A"}, headers=cab_loja).status_code == 422

    def test_email_pode_ser_apagado(self, client, cab_loja):
        client.patch("/perfil/", json={"email": "loja@teste.com"}, headers=cab_loja)
        r = client.patch("/perfil/", json={"email": ""}, headers=cab_loja)
        assert r.json()["email"] is None

    def test_editar_um_campo_nao_apaga_o_outro(self, client, cab_loja):
        client.patch("/perfil/", json={"email": "loja@teste.com"}, headers=cab_loja)
        r = client.patch("/perfil/", json={"nome": "Outro nome"}, headers=cab_loja)
        assert r.json()["email"] == "loja@teste.com"

    def test_ninguem_muda_o_proprio_tipo_nem_o_documento(self, client, cab_cliente, db):
        # Campos desconhecidos são ignorados pelo schema — o cliente não
        # vira dono mandando JSON a mais.
        client.patch(
            "/perfil/",
            json={"nome": "Fulano", "tipo": "dono", "cpf_cnpj": "11222333000181"},
            headers=cab_cliente,
        )
        perfil = client.get("/perfil/", headers=cab_cliente).json()
        assert perfil["tipo"] == "cliente"
        assert perfil["documento_tipo"] == "cpf"


class TestSenha:
    def test_troca_com_a_senha_atual_correta(self, client, cab_cliente, cliente, db):
        r = client.put(
            "/perfil/senha",
            json={"senha_atual": "senha123", "senha_nova": "novasenha456"},
            headers=cab_cliente,
        )
        assert r.status_code == 204

        db.refresh(cliente)
        assert verificar_senha("novasenha456", cliente.senha_hash)

    def test_senha_atual_errada_nao_troca_nada(self, client, cab_cliente, cliente, db):
        # Token válido não basta: celular destrancado não pode virar
        # tomada de conta.
        r = client.put(
            "/perfil/senha",
            json={"senha_atual": "chutei", "senha_nova": "novasenha456"},
            headers=cab_cliente,
        )
        assert r.status_code == 400

        db.refresh(cliente)
        assert verificar_senha("senha123", cliente.senha_hash)

    def test_senha_nova_curta_e_recusada(self, client, cab_cliente):
        r = client.put(
            "/perfil/senha",
            json={"senha_atual": "senha123", "senha_nova": "123"},
            headers=cab_cliente,
        )
        assert r.status_code == 422

    def test_repetir_a_senha_atual_e_recusado(self, client, cab_cliente):
        r = client.put(
            "/perfil/senha",
            json={"senha_atual": "senha123", "senha_nova": "senha123"},
            headers=cab_cliente,
        )
        assert r.status_code == 400

    def test_a_senha_trocada_e_a_que_passa_a_valer_no_login(
        self, client, cab_cliente, cliente
    ):
        client.put(
            "/perfil/senha",
            json={"senha_atual": "senha123", "senha_nova": "novasenha456"},
            headers=cab_cliente,
        )

        antiga = client.post(
            "/auth/login",
            json={"cpf_cnpj": cliente.cpf_cnpj, "senha": "senha123"},
        )
        nova = client.post(
            "/auth/login",
            json={"cpf_cnpj": cliente.cpf_cnpj, "senha": "novasenha456"},
        )
        assert antiga.status_code == 401
        assert nova.status_code == 200

    def test_a_senha_de_um_nao_alcanca_a_conta_do_outro(
        self, client, cab_cliente, loja, db
    ):
        senha_da_loja = loja.senha_hash
        client.put(
            "/perfil/senha",
            json={"senha_atual": "senha123", "senha_nova": "novasenha456"},
            headers=cab_cliente,
        )
        db.refresh(loja)
        assert loja.senha_hash == senha_da_loja


class TestAvatar:
    def test_grava_e_devolve_a_imagem(self, client, cab_loja):
        r = client.put("/perfil/avatar", json={"imagem": PNG_MINIMO}, headers=cab_loja)
        assert r.status_code == 200
        assert r.json()["avatar"] == PNG_MINIMO

    def test_aceita_data_uri_colado(self, client, cab_loja):
        # É o formato que sai do navegador, e o jeito natural de testar
        # pelo /docs.
        r = client.put(
            "/perfil/avatar",
            json={"imagem": f"data:image/png;base64,{PNG_MINIMO}"},
            headers=cab_loja,
        )
        assert r.status_code == 200
        assert r.json()["avatar"] == PNG_MINIMO

    def test_base64_quebrado_e_recusado(self, client, cab_loja):
        r = client.put("/perfil/avatar", json={"imagem": "%%%"}, headers=cab_loja)
        assert r.status_code == 400

    def test_arquivo_que_nao_e_imagem_e_recusado(self, client, cab_loja):
        # Base64 perfeitamente válido, conteúdo que não é imagem: quem
        # confere é o servidor, não a extensão nem o que o app promete.
        texto = base64.b64encode(b"nao sou uma imagem, sou texto").decode()
        r = client.put("/perfil/avatar", json={"imagem": texto}, headers=cab_loja)
        assert r.status_code == 400

    def test_imagem_grande_demais_e_recusada(self, client, cab_loja):
        # PNG válido no começo, mas com meio mega de recheio.
        gordo = base64.b64decode(PNG_MINIMO) + b"\x00" * (500 * 1024)
        r = client.put(
            "/perfil/avatar",
            json={"imagem": base64.b64encode(gordo).decode()},
            headers=cab_loja,
        )
        assert r.status_code == 413

    def test_remover_volta_ao_icone_padrao(self, client, cab_loja):
        client.put("/perfil/avatar", json={"imagem": PNG_MINIMO}, headers=cab_loja)
        assert client.delete("/perfil/avatar", headers=cab_loja).status_code == 204
        assert client.get("/perfil/", headers=cab_loja).json()["avatar"] is None

    def test_a_foto_viaja_no_login(self, client, cab_loja, loja):
        client.put("/perfil/avatar", json={"imagem": PNG_MINIMO}, headers=cab_loja)

        entrada = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "senha123"}
        ).json()
        # Assim o cabeçalho já abre com a logo, sem uma segunda chamada.
        assert entrada["avatar"] == PNG_MINIMO

    def test_a_foto_de_um_nao_aparece_para_o_outro(
        self, client, cab_loja, cab_cliente
    ):
        client.put("/perfil/avatar", json={"imagem": PNG_MINIMO}, headers=cab_loja)
        assert client.get("/perfil/", headers=cab_cliente).json()["avatar"] is None
