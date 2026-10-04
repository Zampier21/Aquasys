"""Revisão da ficha que a importação deixou pela metade.

A importação cria a espécie e a FishBase preenche as medidas, mas
temperamento, agrupamento e a faixa de temperatura ficam vazios. Até
aqui não havia onde preenchê-los: as rotas de espécie eram listar,
detalhar e criar. Esta é a parte que fecha o ciclo.

O caso mais importante do arquivo é
`test_nao_marca_conferida_com_campo_faltando`. Sem essa trava, marcar a
caixa de conferida faria o motor de compatibilidade parar de avisar e
passar a afirmar com convicção o que ninguém verificou.
"""

import pytest

from app.models.especie import Especie
from app.services import fishbase


FICHA_COMPLETA = {
    "tipo_agua": "doce",
    "temp_min": 22.0,
    "temp_max": 28.0,
    "ph_min": 6.0,
    "ph_max": 7.5,
    "tamanho_adulto_cm": 5.0,
    "volume_minimo_l": 60,
    "comportamento": "pacifico",
    "agrupamento": "cardume",
    "cardume_minimo": 6,
    "nivel_natacao": "meio",
    "alimentacao": "onivoro",
}


@pytest.fixture
def rascunho(db, loja):
    """Espécie como a importação a deixa: nome, e pouco mais."""
    especie = Especie(
        nome_comum="Tetra Importado",
        nome_cientifico="Hyphessobrycon exemplo",
        dono_id=loja.id,
        revisada=False,
        ativo=True,
        tipo_agua="doce",
        tamanho_adulto_cm=4.0,
        ph_min=6.0,
        ph_max=7.5,
        clima="tropical",
        fonte_dados=fishbase.ATRIBUICAO,
    )
    db.add(especie)
    db.flush()
    return especie


@pytest.fixture
def curada(db):
    especie = Especie(nome_comum="Neon Tetra", ativo=True, revisada=True)
    db.add(especie)
    db.flush()
    return especie


# ═══════════════════════════════════════════════════════
# A FILA DE TRABALHO
# ═══════════════════════════════════════════════════════
class TestListaDeIncompletas:
    def test_lista_o_rascunho_e_o_que_falta_nele(
        self, client, cab_loja, rascunho
    ):
        corpo = client.get("/peixes/incompletas", headers=cab_loja).json()

        assert len(corpo) == 1
        item = corpo[0]
        assert item["nome_comum"] == "Tetra Importado"
        assert item["clima"] == "tropical"
        # O que a FishBase preencheu não aparece na lista de pendências.
        assert "tipo de água" not in item["faltam"]
        assert "temperatura mínima" in item["faltam"]
        assert "temperamento" in item["faltam"]

    def test_nao_lista_o_catalogo_curado(self, client, cab_loja, curada):
        """O catálogo do AquaSys não é da loja para revisar."""
        assert client.get("/peixes/incompletas", headers=cab_loja).json() == []

    def test_nao_lista_o_que_ja_foi_conferido(
        self, client, cab_loja, rascunho, db
    ):
        rascunho.revisada = True
        db.flush()
        assert client.get("/peixes/incompletas", headers=cab_loja).json() == []

    def test_a_outra_loja_nao_ve_a_fila_alheia(
        self, client, cab_outra_loja, rascunho
    ):
        assert client.get(
            "/peixes/incompletas", headers=cab_outra_loja
        ).json() == []

    def test_o_cliente_nao_revisa_ficha(self, client, cab_cliente, rascunho):
        assert client.get(
            "/peixes/incompletas", headers=cab_cliente
        ).status_code == 403

    def test_a_rota_nao_e_confundida_com_identificador(
        self, client, cab_loja, rascunho
    ):
        """`/incompletas` é declarada antes de `/{especie_id}`.

        Na ordem inversa, o FastAPI tentaria ler "incompletas" como UUID
        e responderia 422.
        """
        assert client.get(
            "/peixes/incompletas", headers=cab_loja
        ).status_code == 200


# ═══════════════════════════════════════════════════════
# EDIÇÃO
# ═══════════════════════════════════════════════════════
class TestEdicao:
    def test_preenche_o_que_faltava(self, client, cab_loja, rascunho, db):
        r = client.put(
            f"/peixes/{rascunho.id}",
            json={"comportamento": "pacifico", "cardume_minimo": 8},
            headers=cab_loja,
        )

        assert r.status_code == 200
        db.refresh(rascunho)
        assert rascunho.comportamento == "pacifico"
        assert rascunho.cardume_minimo == 8

    def test_corrigir_so_o_que_veio_no_corpo(self, client, cab_loja, rascunho, db):
        """Campo ausente não é campo apagado."""
        client.put(
            f"/peixes/{rascunho.id}",
            json={"comportamento": "pacifico"},
            headers=cab_loja,
        )
        db.refresh(rascunho)
        assert rascunho.nome_cientifico == "Hyphessobrycon exemplo"
        assert rascunho.tamanho_adulto_cm == 4.0

    def test_campo_que_nao_existe_no_contrato_e_recusado(
        self, client, cab_loja, rascunho
    ):
        r = client.put(
            f"/peixes/{rascunho.id}",
            json={"dono_id": None, "ativo": False},
            headers=cab_loja,
        )
        assert r.status_code == 422

    def test_nome_nulo_nao_derruba_a_rota(self, client, cab_loja, rascunho, db):
        """O nome é NOT NULL na tabela: nulo chegaria lá como erro 500."""
        r = client.put(
            f"/peixes/{rascunho.id}",
            json={"nome_comum": None, "comportamento": "pacifico"},
            headers=cab_loja,
        )

        assert r.status_code == 200
        db.refresh(rascunho)
        assert rascunho.nome_comum == "Tetra Importado"
        assert rascunho.comportamento == "pacifico"


class TestValidacao:
    @pytest.mark.parametrize("campo,valor", [
        ("comportamento", "bravo"),
        ("agrupamento", "bando"),
        ("nivel_natacao", "diagonal"),
        ("tipo_agua", "destilada"),
        ("reef_safe", "talvez"),
        ("nivel_dificuldade", "impossivel"),
    ])
    def test_valor_fora_do_enumerado_volta_422_e_nao_500(
        self, client, cab_loja, rascunho, campo, valor
    ):
        """A tabela tem CHECK para cada um destes.

        Sem validação no contrato, o valor chegaria ao PostgreSQL,
        estouraria lá e o usuário veria erro interno em vez de aviso.
        """
        r = client.put(
            f"/peixes/{rascunho.id}", json={campo: valor}, headers=cab_loja
        )
        assert r.status_code == 422

    @pytest.mark.parametrize("menor,maior,campo", [
        ("temp_min", "temp_max", "temperatura"),
        ("ph_min", "ph_max", "pH"),
        ("dgh_min", "dgh_max", "dureza"),
    ])
    def test_minimo_acima_do_maximo_e_recusado(
        self, client, cab_loja, rascunho, menor, maior, campo
    ):
        """Faixa invertida deixaria a espécie incompatível com tudo."""
        r = client.put(
            f"/peixes/{rascunho.id}",
            json={menor: 8.0, maior: 6.0},
            headers=cab_loja,
        )
        assert r.status_code == 422

    def test_ph_fora_da_escala_e_recusado(self, client, cab_loja, rascunho):
        assert client.put(
            f"/peixes/{rascunho.id}", json={"ph_min": 20}, headers=cab_loja
        ).status_code == 422

    def test_tamanho_negativo_e_recusado(self, client, cab_loja, rascunho):
        assert client.put(
            f"/peixes/{rascunho.id}",
            json={"tamanho_adulto_cm": -3},
            headers=cab_loja,
        ).status_code == 422


# ═══════════════════════════════════════════════════════
# FECHAR A REVISÃO
# ═══════════════════════════════════════════════════════
class TestMarcarConferida:
    def test_nao_marca_conferida_com_campo_faltando(
        self, client, cab_loja, rascunho, db
    ):
        """A trava central deste arquivo.

        Sem ela, marcar a caixa calaria o aviso do motor e o sistema
        passaria a afirmar com convicção o que ninguém verificou.
        """
        r = client.put(
            f"/peixes/{rascunho.id}", json={"revisada": True}, headers=cab_loja
        )

        assert r.status_code == 422
        assert "preencha antes" in r.json()["detail"]
        assert "temperamento" in r.json()["detail"]

        db.refresh(rascunho)
        assert rascunho.revisada is False

    def test_a_recusa_nao_grava_as_outras_mudancas(
        self, client, cab_loja, rascunho, db
    ):
        """Ou fecha a ficha inteira, ou não mexe em nada.

        Gravar metade e recusar o resto deixaria a loja sem saber o que
        entrou.
        """
        client.put(
            f"/peixes/{rascunho.id}",
            json={"comportamento": "agressivo", "revisada": True},
            headers=cab_loja,
        )
        db.refresh(rascunho)
        assert rascunho.comportamento is None

    def test_marca_conferida_quando_a_ficha_fecha(
        self, client, cab_loja, rascunho, db
    ):
        r = client.put(
            f"/peixes/{rascunho.id}",
            json={**FICHA_COMPLETA, "revisada": True},
            headers=cab_loja,
        )

        assert r.status_code == 200
        db.refresh(rascunho)
        assert rascunho.revisada is True

    def test_cardume_minimo_so_e_exigido_de_quem_vive_em_cardume(
        self, client, cab_loja, rascunho, db
    ):
        """Pedir o número para peixe solitário faria a ficha nunca fechar."""
        sozinho = {**FICHA_COMPLETA, "agrupamento": "solitario"}
        sozinho.pop("cardume_minimo")

        r = client.put(
            f"/peixes/{rascunho.id}",
            json={**sozinho, "revisada": True},
            headers=cab_loja,
        )

        assert r.status_code == 200
        db.refresh(rascunho)
        assert rascunho.revisada is True

    def test_da_para_reabrir_a_revisao(self, client, cab_loja, rascunho, db):
        client.put(
            f"/peixes/{rascunho.id}",
            json={**FICHA_COMPLETA, "revisada": True},
            headers=cab_loja,
        )
        client.put(
            f"/peixes/{rascunho.id}", json={"revisada": False}, headers=cab_loja
        )
        db.refresh(rascunho)
        assert rascunho.revisada is False


# ═══════════════════════════════════════════════════════
# EFEITO NO MOTOR
# ═══════════════════════════════════════════════════════
class TestOMotorPassaAConfiar:
    def criar_aquario(self, client, cabecalho):
        return client.post(
            "/aquarios/",
            json={"nome": "Teste", "volume_litros": 200, "temperatura": 25,
                  "ph": 7.0, "tipo": "comunitario"},
            headers=cabecalho,
        ).json()["id"]

    def test_antes_da_revisao_o_aviso_diz_o_que_falta(
        self, client, cab_loja, rascunho
    ):
        aquario = self.criar_aquario(client, cab_loja)
        analise = client.get(
            f"/peixes/{rascunho.id}/aquario/{aquario}", headers=cab_loja
        ).json()

        aviso = next(a for a in analise["avisos"]
                     if a["motivo"] == "ficha_incompleta")
        assert "temperamento" in aviso["mensagem"]
        assert analise["decisao"] == "requer_confirmacao"

    def test_depois_da_revisao_o_aviso_sai(self, client, cab_loja, rascunho):
        aquario = self.criar_aquario(client, cab_loja)
        client.put(
            f"/peixes/{rascunho.id}",
            json={**FICHA_COMPLETA, "revisada": True},
            headers=cab_loja,
        )

        analise = client.get(
            f"/peixes/{rascunho.id}/aquario/{aquario}", headers=cab_loja
        ).json()
        assert not any(a["motivo"] == "ficha_incompleta"
                       for a in analise["avisos"])


# ═══════════════════════════════════════════════════════
# QUEM PODE MEXER
# ═══════════════════════════════════════════════════════
class TestPermissao:
    def test_a_outra_loja_recebe_404_e_nao_403(
        self, client, cab_outra_loja, rascunho
    ):
        """403 confirmaria que a espécie existe, o que entrega o catálogo."""
        r = client.put(
            f"/peixes/{rascunho.id}",
            json={"comportamento": "pacifico"},
            headers=cab_outra_loja,
        )
        assert r.status_code == 404

    def test_ninguem_edita_o_catalogo_curado(self, client, cab_loja, curada):
        """Uma loja mexendo ali mudaria a ficha para todas as outras."""
        r = client.put(
            f"/peixes/{curada.id}",
            json={"comportamento": "agressivo"},
            headers=cab_loja,
        )

        assert r.status_code == 403
        assert "catálogo do AquaSys" in r.json()["detail"]

    def test_o_cliente_nao_edita(self, client, cab_cliente, rascunho):
        assert client.put(
            f"/peixes/{rascunho.id}",
            json={"comportamento": "pacifico"},
            headers=cab_cliente,
        ).status_code == 403

    def test_especie_que_nao_existe_volta_404(self, client, cab_loja):
        import uuid
        assert client.put(
            f"/peixes/{uuid.uuid4()}",
            json={"comportamento": "pacifico"},
            headers=cab_loja,
        ).status_code == 404


# ═══════════════════════════════════════════════════════
# CRÉDITO DA FONTE
# ═══════════════════════════════════════════════════════
class TestCreditoDepoisDoAjuste:
    def test_mexer_em_medida_da_fishbase_marca_o_credito(
        self, client, cab_loja, rascunho, db
    ):
        """O crédito deixa de descrever a ficha inteira, e passa a dizer isso."""
        client.put(
            f"/peixes/{rascunho.id}",
            json={"tamanho_adulto_cm": 4.5},
            headers=cab_loja,
        )
        db.refresh(rascunho)

        assert rascunho.fonte_dados.startswith(fishbase.ATRIBUICAO)
        assert "ajustes da loja" in rascunho.fonte_dados

    def test_preencher_campo_que_a_fishbase_nao_traz_nao_marca(
        self, client, cab_loja, rascunho, db
    ):
        """Temperamento nunca veio de lá, então o crédito segue exato."""
        client.put(
            f"/peixes/{rascunho.id}",
            json={"comportamento": "pacifico"},
            headers=cab_loja,
        )
        db.refresh(rascunho)
        assert rascunho.fonte_dados == fishbase.ATRIBUICAO

    def test_regravar_o_mesmo_valor_nao_marca(
        self, client, cab_loja, rascunho, db
    ):
        """Mandar o valor que já estava lá não é ajuste."""
        client.put(
            f"/peixes/{rascunho.id}",
            json={"tamanho_adulto_cm": 4.0},
            headers=cab_loja,
        )
        db.refresh(rascunho)
        assert rascunho.fonte_dados == fishbase.ATRIBUICAO

    def test_a_marca_nao_e_repetida(self, client, cab_loja, rascunho, db):
        for valor in (4.5, 5.0):
            client.put(
                f"/peixes/{rascunho.id}",
                json={"tamanho_adulto_cm": valor},
                headers=cab_loja,
            )
        db.refresh(rascunho)
        assert rascunho.fonte_dados.count("ajustes da loja") == 1

    def test_ficha_sem_fonte_nao_ganha_credito_do_nada(
        self, client, cab_loja, db, loja
    ):
        """Espécie digitada à mão nunca teve fonte externa."""
        manual = Especie(nome_comum="Digitada", dono_id=loja.id,
                         revisada=False, ativo=True)
        db.add(manual)
        db.flush()

        client.put(
            f"/peixes/{manual.id}",
            json={"tamanho_adulto_cm": 7.0},
            headers=cab_loja,
        )
        db.refresh(manual)
        assert manual.fonte_dados is None
