from app.models.alerta import Alerta
from app.models.especie import AquarioEspecie, Especie

COMUNITARIO = {
    "nome": "Comunitário",
    "volume_litros": 100,
    "temperatura": 26,
    "tipo": "comunitario",
}


def criar(client, cabecalho, **campos):
    r = client.post("/aquarios/", json={**COMUNITARIO, **campos}, headers=cabecalho)
    assert r.status_code == 201, r.text
    return r.json()


class TestCicloDoAlerta:
    def test_parametro_fora_da_faixa_gera_alerta(self, client, cab_loja, db):
        criar(client, cab_loja, ph=7.3)

        painel = client.get("/painel/", headers=cab_loja).json()
        assert len(painel["alertas"]) == 1
        assert "0.3 acima do ideal" in painel["alertas"][0]["mensagem"]

    def test_parametro_dentro_da_faixa_nao_gera_alerta(self, client, cab_loja):
        criar(client, cab_loja, ph=6.8)
        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []

    def test_corrigir_o_parametro_apaga_o_alerta(self, client, cab_loja):
        aquario = criar(client, cab_loja, ph=7.3)
        assert len(client.get("/painel/", headers=cab_loja).json()["alertas"]) == 1

        client.put(f"/aquarios/{aquario['id']}", json={"ph": 6.8}, headers=cab_loja)
        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []

    def test_valor_novo_substitui_o_alerta_anterior(self, client, cab_loja, db):
        # Sem histórico, por decisão de produto: só o estado atual importa.
        aquario = criar(client, cab_loja, ph=7.3)
        client.put(f"/aquarios/{aquario['id']}", json={"ph": 7.5}, headers=cab_loja)

        gravados = db.query(Alerta).filter(
            Alerta.aquario_id == aquario["id"]
        ).all()
        assert len(gravados) == 1
        assert "0.5 acima" in gravados[0].mensagem

    def test_marcar_como_lido_tira_do_painel(self, client, cab_loja):
        criar(client, cab_loja, ph=7.3)
        alerta = client.get("/painel/", headers=cab_loja).json()["alertas"][0]

        r = client.patch(f"/painel/alertas/{alerta['id']}/lido", headers=cab_loja)
        assert r.status_code == 204
        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []

    def test_dispensado_volta_na_proxima_medicao_fora(self, client, cab_loja):
        # É o que impede o lembrete de sumir para sempre com um toque.
        aquario = criar(client, cab_loja, ph=7.3)
        alerta = client.get("/painel/", headers=cab_loja).json()["alertas"][0]
        client.patch(f"/painel/alertas/{alerta['id']}/lido", headers=cab_loja)

        client.put(f"/aquarios/{aquario['id']}", json={"ph": 7.4}, headers=cab_loja)
        assert len(client.get("/painel/", headers=cab_loja).json()["alertas"]) == 1

    def test_apagar_o_aquario_leva_os_alertas(self, client, cab_loja, db):
        aquario = criar(client, cab_loja, ph=7.3)
        client.delete(f"/aquarios/{aquario['id']}", headers=cab_loja)

        assert db.query(Alerta).filter(
            Alerta.aquario_id == aquario["id"]
        ).count() == 0


class TestAlertaRespeitaOTipo:
    def test_marinho_a_ph_8_nao_gera_alerta(self, client, cab_loja):
        # O caso que já apareceu quebrado: pH 8 é saudável em marinho.
        criar(client, cab_loja, nome="Marinho", tipo="marinho", ph=8.2)
        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []

    def test_comunitario_a_ph_8_gera_alerta(self, client, cab_loja):
        criar(client, cab_loja, ph=8.2)
        assert len(client.get("/painel/", headers=cab_loja).json()["alertas"]) == 1

    def test_mudar_o_tipo_recalcula_o_alerta(self, client, cab_loja):
        aquario = criar(client, cab_loja, nome="Era comunitário", ph=8.2)
        assert len(client.get("/painel/", headers=cab_loja).json()["alertas"]) == 1

        client.put(
            f"/aquarios/{aquario['id']}", json={"tipo": "marinho"}, headers=cab_loja
        )
        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []


class TestPainel:
    def test_painel_vazio_nao_inventa_saude(self, client, cab_loja):
        painel = client.get("/painel/", headers=cab_loja).json()
        assert painel["total_aquarios"] == 0
        assert painel["saude_geral"] is None  # "—" na tela, não 100%

    def test_saude_e_o_percentual_de_checagens_aprovadas(self, client, cab_loja):
        # 1 aquário × 5 parâmetros, 1 fora = 80%
        criar(client, cab_loja, ph=7.3)
        assert client.get("/painel/", headers=cab_loja).json()["saude_geral"] == 80

    def test_tudo_certo_da_cem_por_cento(self, client, cab_loja):
        criar(client, cab_loja, ph=6.8)
        assert client.get("/painel/", headers=cab_loja).json()["saude_geral"] == 100

    def test_o_aquario_carrega_a_faixa_do_proprio_tipo(self, client, cab_loja):
        criar(client, cab_loja, nome="Marinho", tipo="marinho", ph=8.2)
        criar(client, cab_loja, nome="Comum", ph=6.8)

        por_nome = {
            a["nome"]: a for a in client.get("/aquarios/", headers=cab_loja).json()
        }
        assert por_nome["Marinho"]["faixas"]["ph"] == "8.0 – 8.4"
        assert por_nome["Comum"]["faixas"]["ph"] == "6.5 – 7.0"

    def test_o_aquario_diz_quais_parametros_estao_fora(self, client, cab_loja):
        criar(client, cab_loja, ph=7.3)
        aquario = client.get("/aquarios/", headers=cab_loja).json()[0]
        # O app não recalcula nada: pinta o que vem aqui.
        assert aquario["problemas"] == ["ph"]


class TestOsPeixesMandamNaFaixa:
    def povoar(self, db, aquario_id, especie):
        db.add(especie)
        db.flush()
        db.add(
            AquarioEspecie(
                aquario_id=aquario_id, especie_id=especie.id, quantidade=6
            )
        )
        db.flush()

    def test_peixe_alcalino_derruba_o_alerta_do_tipo(self, client, cab_loja, db):
        aquario = criar(client, cab_loja, ph=8.2)
        assert len(client.get("/painel/", headers=cab_loja).json()["alertas"]) == 1

        self.povoar(db, aquario["id"], Especie(
            nome_comum="Molinésia", ph_min=7.0, ph_max=8.5,
            temp_min=24, temp_max=28, ativo=True,
        ))
        # Regrava os alertas com o aquário já povoado.
        client.put(f"/aquarios/{aquario['id']}", json={"ph": 8.2}, headers=cab_loja)

        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []

    def test_a_faixa_devolvida_passa_a_ser_a_dos_peixes(self, client, cab_loja, db):
        aquario = criar(client, cab_loja, ph=8.2)
        self.povoar(db, aquario["id"], Especie(
            nome_comum="Molinésia", ph_min=7.0, ph_max=8.5,
            temp_min=24, temp_max=28, ativo=True,
        ))

        resposta = client.get(f"/aquarios/{aquario['id']}", headers=cab_loja).json()
        assert resposta["faixas"]["ph"] == "7.0 – 8.5"
        assert resposta["problemas"] == []

    def test_a_explicacao_cita_o_peixe_quando_o_ph_nao_serve(
        self, client, cab_loja, db
    ):
        aquario = criar(client, cab_loja, ph=7.6)
        self.povoar(db, aquario["id"], Especie(
            nome_comum="Neon Tetra", ph_min=5.5, ph_max=7.0,
            temp_min=24, temp_max=28, ativo=True,
        ))

        resposta = client.get(f"/aquarios/{aquario['id']}", headers=cab_loja).json()
        assert "Neon Tetra" in resposta["explicacoes"]["ph"]
        assert resposta["problemas"] == ["ph"]

    def test_a_escala_do_ph_viaja_para_o_app(self, client, cab_loja):
        aquario = criar(client, cab_loja, ph=6.8)
        resposta = client.get(f"/aquarios/{aquario['id']}", headers=cab_loja).json()
        # O app não guarda texto de conteúdo: quem explica é a API.
        assert "ácida" in resposta["escala_ph"]
        assert "alcalina" in resposta["escala_ph"]


class TestDicasDaHome:
    def test_sem_aquario_a_dica_convida_a_cadastrar(self, client, cab_loja):
        dicas = client.get("/painel/", headers=cab_loja).json()["dicas"]
        assert "Cadastre seu primeiro aquário" in dicas[0]["conteudo"]

    def test_parametro_fora_vira_a_primeira_dica(self, client, cab_loja):
        criar(client, cab_loja, nome="Meu tanque", ph=7.3)
        dicas = client.get("/painel/", headers=cab_loja).json()["dicas"]
        assert "Meu tanque" in dicas[0]["conteudo"]

    def test_aquario_sem_peixe_e_lembrado(self, client, cab_loja):
        criar(client, cab_loja, nome="Vazio", ph=6.8)
        conteudos = " ".join(
            d["conteudo"]
            for d in client.get("/painel/", headers=cab_loja).json()["dicas"]
        )
        assert "ainda está sem peixes" in conteudos

    def test_cardume_incompleto_vira_dica(self, client, cab_loja, db):
        aquario = criar(client, cab_loja, nome="Comunitário", ph=6.8)
        especie = Especie(
            nome_comum="Neon Tetra", ph_min=5.5, ph_max=7.0,
            temp_min=24, temp_max=28, agrupamento="cardume",
            cardume_minimo=10, ativo=True,
        )
        db.add(especie)
        db.flush()
        db.add(AquarioEspecie(
            aquario_id=aquario["id"], especie_id=especie.id, quantidade=4
        ))
        db.flush()

        conteudos = " ".join(
            d["conteudo"]
            for d in client.get("/painel/", headers=cab_loja).json()["dicas"]
        )
        assert "Faltam 6 peixes" in conteudos

    def test_a_home_nunca_fica_com_menos_de_uma_dica(self, client, cab_loja):
        criar(client, cab_loja, ph=6.8)
        assert client.get("/painel/", headers=cab_loja).json()["dicas"]


class TestPovoarRecalculaOAlerta:
    def especie_alcalina(self, db):
        especie = Especie(
            nome_comum="Molinésia", ph_min=7.0, ph_max=8.5,
            temp_min=24, temp_max=28, tipo_agua="doce",
            comportamento="pacifico", tamanho_adulto_cm=6,
            volume_minimo_l=40, agrupamento="cardume", cardume_minimo=3,
            ativo=True,
        )
        db.add(especie)
        db.flush()
        return especie

    def test_adicionar_peixe_alcalino_derruba_o_alerta(self, client, cab_loja, db):
        aquario = criar(client, cab_loja, volume_litros=200, ph=8.2)
        especie = self.especie_alcalina(db)
        assert len(client.get("/painel/", headers=cab_loja).json()["alertas"]) == 1

        r = client.post(
            f"/peixes/aquario/{aquario['id']}?confirmar=true",
            json={"especie_id": str(especie.id), "quantidade": 3},
            headers=cab_loja,
        )
        assert r.status_code == 201, r.text
        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []

    def test_remover_o_peixe_traz_o_alerta_de_volta(self, client, cab_loja, db):
        aquario = criar(client, cab_loja, volume_litros=200, ph=8.2)
        especie = self.especie_alcalina(db)

        criado = client.post(
            f"/peixes/aquario/{aquario['id']}?confirmar=true",
            json={"especie_id": str(especie.id), "quantidade": 3},
            headers=cab_loja,
        ).json()
        assert client.get("/painel/", headers=cab_loja).json()["alertas"] == []

        client.delete(
            f"/peixes/aquario/{aquario['id']}/{criado['id']}", headers=cab_loja
        )
        # Sem peixes, volta a valer a faixa do comunitário.
        assert len(client.get("/painel/", headers=cab_loja).json()["alertas"]) == 1
