"""
Testes da ficha de manutenção.

A regra central: o cliente de manutenção é cadastrado uma vez e
reaproveitado. Na segunda visita, o que não for informado tem de vir
do cadastro — é isso que evita redigitar tudo.
"""

CLIENTE = {
    "nome": "Seu João do Lago",
    "telefone": "(41) 99999-1234",
    "endereco": "Rua das Palmeiras, 120",
    "tipo_instalacao": "lago",
    "volume_litros": 5000,
    "agua_doce": True,
}


def criar_cliente(client, cabecalho, **extra):
    r = client.post("/fichas/clientes", json={**CLIENTE, **extra}, headers=cabecalho)
    assert r.status_code == 201, r.text
    return r.json()


class TestCadastroDeCliente:
    def test_cria_e_lista(self, client, cab_loja):
        criado = criar_cliente(client, cab_loja)
        assert criado["total_fichas"] == 0
        assert criado["ultima_visita"] is None

        lista = client.get("/fichas/clientes", headers=cab_loja).json()
        assert [c["nome"] for c in lista] == ["Seu João do Lago"]

    def test_nome_repetido_na_mesma_loja_e_recusado(self, client, cab_loja):
        criar_cliente(client, cab_loja)
        r = client.post(
            "/fichas/clientes", json={"nome": "Seu João do Lago"}, headers=cab_loja
        )
        assert r.status_code == 409

    def test_repetido_ignora_maiuscula(self, client, cab_loja):
        criar_cliente(client, cab_loja)
        r = client.post(
            "/fichas/clientes", json={"nome": "seu joão do lago"}, headers=cab_loja
        )
        assert r.status_code == 409

    def test_editar_nao_mexe_no_que_nao_foi_enviado(self, client, cab_loja):
        criado = criar_cliente(client, cab_loja)
        r = client.put(
            f"/fichas/clientes/{criado['id']}",
            json={"telefone": "(41) 98888-7777"},
            headers=cab_loja,
        )
        assert r.status_code == 200
        assert r.json()["telefone"] == "(41) 98888-7777"
        assert r.json()["nome"] == CLIENTE["nome"]
        assert r.json()["volume_litros"] == CLIENTE["volume_litros"]

    def test_volume_precisa_ser_positivo(self, client, cab_loja):
        r = client.post(
            "/fichas/clientes",
            json={"nome": "Zerado", "volume_litros": 0},
            headers=cab_loja,
        )
        assert r.status_code == 422

    def test_cliente_do_app_nao_gerencia_manutencao(self, client, cab_cliente):
        assert client.get("/fichas/clientes", headers=cab_cliente).status_code == 403


class TestPreenchimentoAutomatico:
    def test_a_ficha_herda_os_dados_do_cadastro(self, client, cab_loja):
        cadastro = criar_cliente(client, cab_loja)

        r = client.post(
            "/fichas/",
            json={"cliente_id": cadastro["id"], "data_atendimento": "2026-09-01"},
            headers=cab_loja,
        )
        assert r.status_code == 201
        ficha = r.json()

        # Nada disso foi enviado: veio do cadastro.
        assert ficha["nome_cliente"] == CLIENTE["nome"]
        assert ficha["tipo_instalacao"] == CLIENTE["tipo_instalacao"]
        assert ficha["volume_litros"] == CLIENTE["volume_litros"]
        assert ficha["agua_doce"] == CLIENTE["agua_doce"]

    def test_o_que_a_ficha_informa_vence_o_cadastro(self, client, cab_loja):
        # O cliente trocou de tanque e o cadastro ainda não foi atualizado.
        cadastro = criar_cliente(client, cab_loja)

        r = client.post(
            "/fichas/",
            json={"cliente_id": cadastro["id"], "volume_litros": 8000},
            headers=cab_loja,
        )
        assert r.json()["volume_litros"] == 8000

        # O cadastro segue como estava.
        atual = client.get("/fichas/clientes", headers=cab_loja).json()[0]
        assert atual["volume_litros"] == CLIENTE["volume_litros"]

    def test_ficha_sem_cliente_e_sem_nome_e_recusada(self, client, cab_loja):
        r = client.post(
            "/fichas/", json={"data_atendimento": "2026-09-01"}, headers=cab_loja
        )
        assert r.status_code == 422

    def test_nome_livre_ainda_funciona(self, client, cab_loja):
        # Atendimento de uma vez só, sem cadastrar ninguém.
        r = client.post(
            "/fichas/", json={"nome_cliente": "Avulso da Esquina"}, headers=cab_loja
        )
        assert r.status_code == 201
        assert r.json()["cliente_id"] is None


class TestHistorico:
    def test_as_visitas_aparecem_no_cadastro(self, client, cab_loja):
        cadastro = criar_cliente(client, cab_loja)

        for data in ("2026-09-01", "2026-10-01"):
            client.post(
                "/fichas/",
                json={"cliente_id": cadastro["id"], "data_atendimento": data},
                headers=cab_loja,
            )

        atual = client.get("/fichas/clientes", headers=cab_loja).json()[0]
        assert atual["total_fichas"] == 2
        assert atual["ultima_visita"] == "2026-10-01"

    def test_remover_o_cadastro_preserva_as_fichas(self, client, cab_loja):
        cadastro = criar_cliente(client, cab_loja)
        client.post(
            "/fichas/", json={"cliente_id": cadastro["id"]}, headers=cab_loja
        )

        client.delete(f"/fichas/clientes/{cadastro['id']}", headers=cab_loja)

        assert client.get("/fichas/clientes", headers=cab_loja).json() == []
        fichas = client.get("/fichas/", headers=cab_loja).json()
        assert len(fichas) == 1
        # A ficha guarda o nome do dia do atendimento.
        assert fichas[0]["nome_cliente"] == CLIENTE["nome"]


class TestConteudoDaFicha:
    def test_grava_checklist_testes_e_descricao(self, client, cab_loja):
        r = client.post(
            "/fichas/",
            json={
                "nome_cliente": "Fulano",
                "equipamentos": [
                    {"equipamento": "Filtro", "presente": True},
                    {"equipamento": "Chiller", "presente": False},
                ],
                "testes": [{"parametro": "pH", "valor": 7.2, "unidade": ""}],
                "descricao": {"conferido_2x": True, "descricao_livre": "Troca de 30%"},
            },
            headers=cab_loja,
        )
        assert r.status_code == 201
        ficha = r.json()
        assert len(ficha["equipamentos"]) == 2
        assert len(ficha["testes"]) == 1
        assert ficha["descricao"]["conferido_2x"] is True

    def test_editar_so_o_checklist_preserva_o_resto(self, client, cab_loja):
        criada = client.post(
            "/fichas/",
            json={
                "nome_cliente": "Fulano",
                "testes": [{"parametro": "pH", "valor": 7.2}],
                "descricao": {"descricao_livre": "Original"},
            },
            headers=cab_loja,
        ).json()

        r = client.put(
            f"/fichas/{criada['id']}",
            json={"equipamentos": [{"equipamento": "Filtro", "presente": True}]},
            headers=cab_loja,
        )
        assert r.status_code == 200
        assert len(r.json()["equipamentos"]) == 1
        assert len(r.json()["testes"]) == 1          # não sumiu
        assert r.json()["nome_cliente"] == "Fulano"  # não sumiu

    def test_catalogos_trazem_codigo_e_rotulo(self, client, cab_loja):
        r = client.get("/fichas/catalogos", headers=cab_loja)
        assert r.status_code == 200
        assert "Filtro" in r.json()["maquinarios"]

        ph = next(t for t in r.json()["testes"] if t["parametro"] == "pH")
        # O banco guarda o código curto; o rótulo longo é da tela.
        assert ph["rotulo"] == "PH"
