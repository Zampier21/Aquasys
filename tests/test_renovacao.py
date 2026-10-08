"""Sessão que se renova sem pedir senha de novo.

O token de acesso vale uma hora, de propósito. Sem renovação, isso
jogava o usuário na tela de login a cada hora — foi o que o teste com
usuários mostrou. O par de tokens resolve, mas acrescenta superfície:
um segredo de longa duração passa a existir no aparelho.

Os casos abaixo cobrem exatamente essa superfície. O mais importante do
arquivo é `test_reuso_derruba_todas_as_sessoes`: sem ele, um token de
renovação copiado serviria para sempre, em paralelo com o do dono, e
nada no sistema notaria.
"""

from datetime import datetime, timedelta

import pytest

from app.core.security import hash_do_refresh
from tests.conftest import SENHA
from app.models.sessao import Sessao


def entrar(client, documento, senha):
    return client.post(
        "/auth/login", json={"cpf_cnpj": documento, "senha": senha}
    )


@pytest.fixture
def entrada(client, loja):
    """Um login feito, com o par de tokens em mãos."""
    r = entrar(client, loja.cpf_cnpj, SENHA)
    assert r.status_code == 200, r.text
    return r.json()


# ═══════════════════════════════════════════════════════
# O par de tokens
# ═══════════════════════════════════════════════════════
class TestLogin:
    def test_login_devolve_os_dois_tokens(self, entrada):
        assert entrada["access_token"]
        assert entrada["refresh_token"]
        assert entrada["access_token"] != entrada["refresh_token"]

    def test_o_token_de_renovacao_nao_e_guardado_em_texto(
        self, entrada, db
    ):
        """Se este banco vazar, o que está nele não abre sessão nenhuma."""
        guardado = db.query(Sessao).one()
        assert guardado.hash != entrada["refresh_token"]
        assert guardado.hash == hash_do_refresh(entrada["refresh_token"])

    def test_cada_login_abre_uma_sessao(self, client, loja, db):
        entrar(client, loja.cpf_cnpj, SENHA)
        entrar(client, loja.cpf_cnpj, SENHA)
        # Dois aparelhos, duas sessões: entrar no celular não derruba
        # o tablet.
        assert db.query(Sessao).count() == 2


# ═══════════════════════════════════════════════════════
# Renovação
# ═══════════════════════════════════════════════════════
class TestRenovar:
    def test_devolve_acesso_novo(self, client, entrada):
        r = client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["access_token"]

    def test_o_acesso_novo_funciona(self, client, entrada):
        novo = client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        ).json()

        r = client.get(
            "/perfil/",
            headers={"Authorization": f"Bearer {novo['access_token']}"},
        )
        assert r.status_code == 200

    def test_rotaciona_o_token_de_renovacao(self, client, entrada):
        novo = client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        ).json()
        assert novo["refresh_token"] != entrada["refresh_token"]

    def test_o_antigo_para_de_valer(self, client, entrada):
        client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        )
        r = client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        )
        assert r.status_code == 401

    def test_token_desconhecido(self, client):
        r = client.post(
            "/auth/renovar", json={"refresh_token": "nao-existe"}
        )
        assert r.status_code == 401

    def test_token_vencido(self, client, entrada, db):
        sessao = db.query(Sessao).one()
        sessao.expira_em = datetime.utcnow() - timedelta(seconds=1)
        db.flush()

        r = client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        )
        assert r.status_code == 401

    def test_conta_desativada_nao_renova(self, client, entrada, db, loja):
        """Desativar a loja tem de valer já, não só no próximo login."""
        loja.ativo = False
        db.flush()

        r = client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        )
        assert r.status_code == 401

    def test_campo_a_mais_e_recusado(self, client, entrada):
        r = client.post(
            "/auth/renovar",
            json={
                "refresh_token": entrada["refresh_token"],
                "tipo_usuario": "dono",
            },
        )
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════
# Reúso: a razão de a rotação existir
# ═══════════════════════════════════════════════════════
class TestReuso:
    def test_reuso_derruba_todas_as_sessoes(
        self, client, loja, db
    ):
        """Token repetido significa duas cópias em circulação.

        Não há como saber qual é a do dono, então as duas caem. O
        usuário legítimo refaz o login; quem copiou fica sem nada.
        """
        celular = entrar(client, loja.cpf_cnpj, SENHA).json()
        tablet = entrar(client, loja.cpf_cnpj, SENHA).json()

        # O celular renova normalmente.
        client.post(
            "/auth/renovar", json={"refresh_token": celular["refresh_token"]}
        )

        # Alguém apresenta de novo o token já gasto do celular.
        r = client.post(
            "/auth/renovar", json={"refresh_token": celular["refresh_token"]}
        )
        assert r.status_code == 401

        # O tablet, que não tinha nada a ver, também perde a sessão.
        r = client.post(
            "/auth/renovar", json={"refresh_token": tablet["refresh_token"]}
        )
        assert r.status_code == 401

        assert db.query(Sessao).filter(
            Sessao.revogado_em.is_(None)
        ).count() == 0


# ═══════════════════════════════════════════════════════
# Saída
# ═══════════════════════════════════════════════════════
class TestSair:
    def test_sair_revoga(self, client, entrada, db):
        r = client.post(
            "/auth/sair", json={"refresh_token": entrada["refresh_token"]}
        )
        assert r.status_code == 204
        assert db.query(Sessao).one().revogado_em is not None

    def test_depois_de_sair_nao_renova(self, client, entrada):
        client.post(
            "/auth/sair", json={"refresh_token": entrada["refresh_token"]}
        )
        r = client.post(
            "/auth/renovar",
            json={"refresh_token": entrada["refresh_token"]},
        )
        assert r.status_code == 401

    def test_sair_nao_derruba_o_outro_aparelho(
        self, client, loja
    ):
        celular = entrar(client, loja.cpf_cnpj, SENHA).json()
        tablet = entrar(client, loja.cpf_cnpj, SENHA).json()

        client.post(
            "/auth/sair", json={"refresh_token": celular["refresh_token"]}
        )

        r = client.post(
            "/auth/renovar", json={"refresh_token": tablet["refresh_token"]}
        )
        assert r.status_code == 200

    def test_sair_com_token_desconhecido_nao_entrega_nada(self, client):
        """204 também para token que não existe.

        Responder 404 diria a quem sonda que o outro token existe.
        """
        r = client.post("/auth/sair", json={"refresh_token": "nao-existe"})
        assert r.status_code == 204
