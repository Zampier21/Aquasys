"""
Teto de acessos por plano.

O que se verifica aqui não é uma funcionalidade, e sim a regra que
sustenta o modelo comercial: a loja compra uma quantidade de acessos, e
o servidor é quem a faz valer. Uma checagem que existisse apenas na tela
seria contornável por qualquer requisição montada fora do aplicativo.
"""

import itertools

import pytest

from app.core import planos
from app.models.usuario import Usuario

# O documento é único no banco. Um contador que não reinicia permite
# chamar `encher` mais de uma vez no mesmo teste sem colidir — que foi
# o que aconteceu no teste de reativação.
_sequencia = itertools.count(1)

# Hash constante em vez de hash_senha(): o bcrypt é deliberadamente lento,
# e encher um plano de quinze vagas custaria segundos por teste. Nenhum
# destes clientes precisa fazer login.
HASH_QUALQUER = "$2b$12$abcdefghijklmnopqrstuv"


def encher(db, loja, quantos: int, ativos: bool = True) -> list:
    """Cria acessos direto no banco, sem passar pela API."""
    criados = []
    for _ in range(quantos):
        i = next(_sequencia)
        c = Usuario(
            nome=f"Cliente {i}",
            cpf_cnpj=f"000.{i // 1000:03d}.{i % 1000:03d}-00",
            senha_hash=HASH_QUALQUER,
            tipo="cliente",
            dono_id=loja.id,
            ativo=ativos,
        )
        db.add(c)
        criados.append(c)
    db.flush()
    return criados


NOVO = {
    "nome": "Cliente Novo",
    "cpf_cnpj": "987.654.321-00",
    "senha_inicial": "senha123",
}


# ═══════════════════════════════════════════════════════
# A RÉGUA, SEM BANCO
# ═══════════════════════════════════════════════════════
class TestRegua:
    def test_o_padrao_tem_teto(self):
        assert planos.limite(planos.PLANO_PADRAO) is not None

    def test_ilimitado_nao_tem_teto(self):
        assert planos.limite("ilimitado") is None
        assert planos.cabe_mais_um("ilimitado", 10_000) is True
        assert planos.restantes("ilimitado", 10_000) is None

    @pytest.mark.parametrize("plano", [None, "", "inexistente", "PRO"])
    def test_plano_desconhecido_cai_no_padrao(self, plano):
        """Conta gravada antes desta regra não pode deixar de funcionar."""
        assert planos.limite(plano) == planos.limite(planos.PLANO_PADRAO)

    def test_restantes_nunca_fica_negativo(self):
        teto = planos.limite("basico")
        assert planos.restantes("basico", teto + 5) == 0

    def test_a_vaga_acaba_exatamente_no_teto(self):
        teto = planos.limite("basico")
        assert planos.cabe_mais_um("basico", teto - 1) is True
        assert planos.cabe_mais_um("basico", teto) is False


# ═══════════════════════════════════════════════════════
# O TETO VALENDO NA API
# ═══════════════════════════════════════════════════════
class TestTeto:
    def test_loja_sem_plano_gravado_usa_o_padrao(self, client, cab_loja):
        r = client.get("/clientes/plano", headers=cab_loja)
        assert r.status_code == 200, r.text
        corpo = r.json()
        assert corpo["plano"] == planos.PLANO_PADRAO
        assert corpo["limite"] == planos.limite(planos.PLANO_PADRAO)
        assert corpo["ativos"] == 0
        assert corpo["ilimitado"] is False

    def test_consumo_reflete_os_acessos_ativos(self, client, db, loja, cab_loja):
        encher(db, loja, 4)
        corpo = client.get("/clientes/plano", headers=cab_loja).json()
        assert corpo["ativos"] == 4
        assert corpo["restantes"] == planos.limite("basico") - 4

    def test_cria_ate_a_ultima_vaga(self, client, db, loja, cab_loja):
        encher(db, loja, planos.limite("basico") - 1)
        r = client.post("/clientes/", json=NOVO, headers=cab_loja)
        assert r.status_code == 201, r.text

    def test_barra_quando_o_plano_esta_cheio(self, client, db, loja, cab_loja):
        encher(db, loja, planos.limite("basico"))
        r = client.post("/clientes/", json=NOVO, headers=cab_loja)
        assert r.status_code == 409
        assert "plano" in r.json()["detail"].lower()

    def test_inativo_nao_ocupa_vaga(self, client, db, loja, cab_loja):
        """Desativar quem saiu de carteira devolve a vaga."""
        encher(db, loja, planos.limite("basico"), ativos=False)
        assert client.get("/clientes/plano", headers=cab_loja).json()["ativos"] == 0
        assert client.post("/clientes/", json=NOVO, headers=cab_loja).status_code == 201

    def test_reativar_com_plano_cheio_e_barrado(self, client, db, loja, cab_loja):
        """Sem isto o teto seria burlável: desativa, cria outro, reativa."""
        desativado = encher(db, loja, 1, ativos=False)[0]
        encher(db, loja, planos.limite("basico"))

        r = client.put(
            f"/clientes/{desativado.id}", json={"ativo": True}, headers=cab_loja
        )
        assert r.status_code == 409

    def test_editar_sem_mexer_no_ativo_passa_com_plano_cheio(
        self, client, db, loja, cab_loja
    ):
        """Corrigir o nome de um cliente não pode esbarrar no teto."""
        clientes = encher(db, loja, planos.limite("basico"))
        r = client.put(
            f"/clientes/{clientes[0].id}", json={"nome": "Nome Corrigido"},
            headers=cab_loja,
        )
        assert r.status_code == 200, r.text
        assert r.json()["nome"] == "Nome Corrigido"

    def test_plano_ilimitado_nao_esbarra(self, client, db, loja, cab_loja):
        loja.plano = "ilimitado"
        db.flush()
        encher(db, loja, planos.limite("basico") + 10)

        r = client.post("/clientes/", json=NOVO, headers=cab_loja)
        assert r.status_code == 201, r.text
        assert client.get("/clientes/plano", headers=cab_loja).json()["ilimitado"] is True

    def test_o_teto_e_por_loja(self, client, db, loja, outra_loja, cab_outra_loja):
        """A lotação de uma loja não pode barrar a outra."""
        encher(db, loja, planos.limite("basico"))
        r = client.post("/clientes/", json=NOVO, headers=cab_outra_loja)
        assert r.status_code == 201, r.text

    def test_cliente_nao_consulta_o_plano(self, client, cab_cliente):
        assert client.get("/clientes/plano", headers=cab_cliente).status_code == 403

    def test_plano_exige_autenticacao(self, client):
        assert client.get("/clientes/plano").status_code in (401, 403)
