AQUARIO = {
    "nome": "Aquário da Loja A",
    "volume_litros": 100,
    "temperatura": 26,
    "ph": 6.8,
    "tipo": "comunitario",
}


def criar_aquario(client, cabecalho, nome="Aquário"):
    r = client.post("/aquarios/", json={**AQUARIO, "nome": nome}, headers=cabecalho)
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestAquarios:
    def test_a_lista_so_traz_os_proprios(self, client, cab_loja, cab_outra_loja):
        criar_aquario(client, cab_loja, "Da Loja A")
        criar_aquario(client, cab_outra_loja, "Da Loja B")

        da_a = client.get("/aquarios/", headers=cab_loja).json()
        da_b = client.get("/aquarios/", headers=cab_outra_loja).json()

        assert [a["nome"] for a in da_a] == ["Da Loja A"]
        assert [a["nome"] for a in da_b] == ["Da Loja B"]

    def test_nao_le_aquario_de_outra_loja(self, client, cab_loja, cab_outra_loja):
        alheio = criar_aquario(client, cab_loja)
        r = client.get(f"/aquarios/{alheio}", headers=cab_outra_loja)
        assert r.status_code == 404

    def test_nao_edita_aquario_de_outra_loja(self, client, cab_loja, cab_outra_loja):
        alheio = criar_aquario(client, cab_loja)
        r = client.put(
            f"/aquarios/{alheio}", json={"nome": "Invadido"}, headers=cab_outra_loja
        )
        assert r.status_code == 404

    def test_nao_apaga_aquario_de_outra_loja(self, client, cab_loja, cab_outra_loja):
        alheio = criar_aquario(client, cab_loja)
        assert (
            client.delete(f"/aquarios/{alheio}", headers=cab_outra_loja).status_code
            == 404
        )
        # E continua lá para o dono.
        assert client.get(f"/aquarios/{alheio}", headers=cab_loja).status_code == 200

    def test_cliente_nao_ve_aquario_da_loja_dele(
        self, client, cab_loja, cab_cliente
    ):
        # A loja não gerencia os aquários do cliente, e vice-versa.
        alheio = criar_aquario(client, cab_loja)
        assert client.get("/aquarios/", headers=cab_cliente).json() == []
        assert client.get(f"/aquarios/{alheio}", headers=cab_cliente).status_code == 404


class TestClientes:
    def test_uma_loja_nao_lista_clientes_da_outra(
        self, client, cab_loja, cab_outra_loja, cliente
    ):
        da_a = client.get("/clientes/", headers=cab_loja).json()
        da_b = client.get("/clientes/", headers=cab_outra_loja).json()

        assert len(da_a) == 1
        assert da_b == []

    def test_uma_loja_nao_alcanca_cliente_da_outra(
        self, client, cab_outra_loja, cliente
    ):
        r = client.get(f"/clientes/{cliente.id}", headers=cab_outra_loja)
        assert r.status_code == 404

    def test_cliente_nao_gerencia_clientes(self, client, cab_cliente):
        assert client.get("/clientes/", headers=cab_cliente).status_code == 403


class TestFichas:
    def criar_ficha(self, client, cabecalho, nome="Fulano"):
        r = client.post("/fichas/", json={"nome_cliente": nome}, headers=cabecalho)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_uma_loja_nao_ve_ficha_da_outra(self, client, cab_loja, cab_outra_loja):
        alheia = self.criar_ficha(client, cab_loja)

        assert client.get("/fichas/", headers=cab_outra_loja).json() == []
        assert client.get(f"/fichas/{alheia}", headers=cab_outra_loja).status_code == 404

    def test_uma_loja_nao_apaga_ficha_da_outra(
        self, client, cab_loja, cab_outra_loja
    ):
        alheia = self.criar_ficha(client, cab_loja)
        assert (
            client.delete(f"/fichas/{alheia}", headers=cab_outra_loja).status_code
            == 404
        )

    def test_cliente_de_manutencao_nao_vaza_entre_lojas(
        self, client, cab_loja, cab_outra_loja
    ):
        r = client.post(
            "/fichas/clientes", json={"nome": "Dona Marta"}, headers=cab_loja
        )
        assert r.status_code == 201
        alheio = r.json()["id"]

        assert client.get("/fichas/clientes", headers=cab_outra_loja).json() == []
        assert (
            client.put(
                f"/fichas/clientes/{alheio}",
                json={"telefone": "invadido"},
                headers=cab_outra_loja,
            ).status_code
            == 404
        )

    def test_o_mesmo_nome_pode_existir_em_lojas_diferentes(
        self, client, cab_loja, cab_outra_loja
    ):
        # A unicidade é por loja, não global.
        corpo = {"nome": "Dona Marta"}
        assert (
            client.post("/fichas/clientes", json=corpo, headers=cab_loja).status_code
            == 201
        )
        assert (
            client.post(
                "/fichas/clientes", json=corpo, headers=cab_outra_loja
            ).status_code
            == 201
        )


class TestPainel:
    def test_o_painel_conta_so_o_que_e_do_usuario(
        self, client, cab_loja, cab_outra_loja
    ):
        criar_aquario(client, cab_loja, "Um")
        criar_aquario(client, cab_loja, "Dois")
        criar_aquario(client, cab_outra_loja, "Da outra")

        assert client.get("/painel/", headers=cab_loja).json()["total_aquarios"] == 2
        assert (
            client.get("/painel/", headers=cab_outra_loja).json()["total_aquarios"] == 1
        )
