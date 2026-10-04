"""Provas das proteções de borda da API.

Cada caso aqui existe porque a proteção correspondente é invisível no
uso normal: ninguém percebe que o cabeçalho de segurança sumiu, que o
limite de login parou de contar ou que um campo a mais passou a ser
aceito no corpo. São exatamente as coisas que voltam sozinhas numa
refatoração distraída, e por isso precisam de teste.
"""

import base64
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import limitador
from app.core.config import Settings, settings
from app.core.deps import get_usuario_atual
from app.core.security import criar_token, hash_senha, verificar_senha
from app.core.seguranca_http import ExigirHTTPS
from app.main import app as api


@pytest.fixture
def limite_ligado():
    """Religa o limitador só para o caso que o está testando."""
    settings.RATE_LIMIT_ATIVO = True
    limitador.zerar_tudo()
    yield
    settings.RATE_LIMIT_ATIVO = False
    limitador.zerar_tudo()


# ═══════════════════════════════════════════════════════
# CABEÇALHOS DE SEGURANÇA
# ═══════════════════════════════════════════════════════
class TestCabecalhos:
    def test_a_resposta_traz_os_cabecalhos(self, client):
        cabecalhos = client.get("/").headers

        assert cabecalhos["X-Content-Type-Options"] == "nosniff"
        assert cabecalhos["X-Frame-Options"] == "DENY"
        assert cabecalhos["Referrer-Policy"] == "no-referrer"
        assert "Content-Security-Policy" in cabecalhos
        assert "Permissions-Policy" in cabecalhos

    def test_a_politica_da_api_nao_permite_nada(self, client):
        """JSON não executa script nem precisa ser embutido em moldura."""
        politica = client.get("/").headers["Content-Security-Policy"]

        assert "default-src 'none'" in politica
        assert "frame-ancestors 'none'" in politica

    def test_resposta_autenticada_nao_vai_para_cache(self, client, cab_loja):
        resposta = client.get("/aquarios/", headers=cab_loja)
        assert resposta.headers["Cache-Control"] == "no-store"

    def test_a_recusa_tambem_sai_protegida(self, client):
        """O 401 passa pelo mesmo caminho: se não passasse, faltaria."""
        resposta = client.get("/aquarios/")
        assert resposta.status_code == 401  # sem cabeçalho Authorization
        assert resposta.headers["X-Content-Type-Options"] == "nosniff"

    def test_sem_hsts_quando_https_nao_e_exigido(self, client):
        """Prometer HSTS sem certificado tranca o próprio dono do lado de fora."""
        if not settings.FORCAR_HTTPS:
            assert "Strict-Transport-Security" not in client.get("/").headers


# ═══════════════════════════════════════════════════════
# O QUE A ROTA ABERTA CONTA
# ═══════════════════════════════════════════════════════
class TestSuperficieAberta:
    def test_a_raiz_nao_anuncia_versao(self, client):
        """Versão em rota aberta é atalho para quem procura falha conhecida."""
        corpo = client.get("/").json()

        assert corpo == {"status": "online"}
        assert "versao" not in corpo
        assert "docs" not in corpo

    def test_a_documentacao_segue_a_configuracao(self, client):
        esperado = 200 if settings.DOCS_PUBLICOS else 404
        assert client.get("/openapi.json").status_code == esperado

    def test_toda_rota_exige_token_menos_login_e_status(self):
        """Varre o aplicativo em vez de confiar na leitura de cada arquivo.

        Uma rota nova que esqueça o `Depends(get_usuario_atual)` fica
        aberta a qualquer um, e nada no resto da suíte perceberia.
        """
        abertas = {"/", "/health", "/auth/login",
                   "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
        desprotegidas = []

        for rota in api.routes:
            caminho = getattr(rota, "path", None)
            if caminho is None or caminho in abertas:
                continue

            dependencias = getattr(rota, "dependant", None)
            if dependencias is None:
                continue

            usa = any(
                sub.call is get_usuario_atual
                for sub in dependencias.dependencies
            )
            if not usa:
                desprotegidas.append(f"{list(rota.methods)} {caminho}")

        assert desprotegidas == []


# ═══════════════════════════════════════════════════════
# LIMITE DE REQUISIÇÕES
# ═══════════════════════════════════════════════════════
class TestLimiteDeLogin:
    def test_a_enxurrada_de_senhas_erradas_e_barrada(
        self, client, loja, limite_ligado
    ):
        erradas = {"cpf_cnpj": loja.cpf_cnpj, "senha": "chute"}

        for _ in range(settings.RATE_LIMIT_LOGIN):
            assert client.post("/auth/login", json=erradas).status_code == 401

        excedente = client.post("/auth/login", json=erradas)
        assert excedente.status_code == 429
        assert "Retry-After" in excedente.headers

    def test_a_senha_certa_tambem_e_barrada_depois_do_teto(
        self, client, loja, limite_ligado
    ):
        """Senão bastaria chutar até acertar, que é o que se quer impedir."""
        for _ in range(settings.RATE_LIMIT_LOGIN):
            client.post(
                "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "x"}
            )

        certa = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "senha123"}
        )
        assert certa.status_code == 429

    def test_entrar_zera_a_contagem(self, client, loja, limite_ligado):
        """Quem erra a senha de manhã e acerta não fica de castigo."""
        for _ in range(settings.RATE_LIMIT_LOGIN - 1):
            client.post(
                "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "x"}
            )

        certa = {"cpf_cnpj": loja.cpf_cnpj, "senha": "senha123"}
        assert client.post("/auth/login", json=certa).status_code == 200
        assert client.post("/auth/login", json=certa).status_code == 200

    def test_a_contagem_e_por_documento_tambem(
        self, client, loja, outra_loja, limite_ligado
    ):
        """Muitos endereços contra uma conta é o outro ataque, e conta igual."""
        for _ in range(settings.RATE_LIMIT_LOGIN):
            limitador.login.esquecer("ip:testclient")
            client.post(
                "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "x"}
            )

        limitador.login.esquecer("ip:testclient")
        resposta = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "x"}
        )
        assert resposta.status_code == 429

    def test_documento_sem_forma_tambem_gasta_tentativa(
        self, client, limite_ligado
    ):
        for _ in range(settings.RATE_LIMIT_LOGIN):
            client.post("/auth/login", json={"cpf_cnpj": "000", "senha": "x"})

        assert client.post(
            "/auth/login", json={"cpf_cnpj": "000", "senha": "x"}
        ).status_code == 429


class TestLimiteGeral:
    def test_o_teto_por_minuto_responde_429(
        self, client, cab_loja, limite_ligado, monkeypatch
    ):
        monkeypatch.setattr(settings, "RATE_LIMIT_POR_MINUTO", 3)
        limitador.zerar_tudo()

        codigos = [client.get("/health").status_code for _ in range(5)]

        assert codigos[:3] == [200, 200, 200]
        assert codigos[3:] == [429, 429]

    def test_desligado_na_configuracao_nao_barra_nada(self, client, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_ATIVO", False)
        monkeypatch.setattr(settings, "RATE_LIMIT_POR_MINUTO", 1)
        limitador.zerar_tudo()

        for _ in range(5):
            assert client.get("/health").status_code == 200


class TestJanelaDeslizante:
    def test_a_vaga_volta_quando_a_janela_passa(self):
        janela = limitador.JanelaDeslizante()

        assert janela.registrar("a", teto=1, janela=0.2)[0] is True
        assert janela.registrar("a", teto=1, janela=0.2)[0] is False

        time.sleep(0.25)
        assert janela.registrar("a", teto=1, janela=0.2)[0] is True

    def test_uma_chave_nao_gasta_a_vaga_da_outra(self):
        janela = limitador.JanelaDeslizante()

        assert janela.registrar("a", teto=1, janela=60)[0] is True
        assert janela.registrar("b", teto=1, janela=60)[0] is True

    def test_a_faxina_descarta_o_que_venceu(self):
        janela = limitador.JanelaDeslizante()
        janela.registrar("a", teto=5, janela=0.1)

        time.sleep(0.15)
        janela.faxinar(0.1)

        assert janela._marcas == {}

    def test_o_proxy_so_e_obedecido_quando_configurado(self, monkeypatch):
        class Falso:
            headers = {"x-forwarded-for": "1.2.3.4, 10.0.0.1"}
            client = type("C", (), {"host": "192.168.0.9"})()

        monkeypatch.setattr(settings, "CONFIAR_NO_PROXY", False)
        assert limitador.endereco(Falso()) == "192.168.0.9"

        monkeypatch.setattr(settings, "CONFIAR_NO_PROXY", True)
        assert limitador.endereco(Falso()) == "1.2.3.4"


# ═══════════════════════════════════════════════════════
# TAMANHO DO CORPO
# ═══════════════════════════════════════════════════════
class TestTamanhoDoCorpo:
    def test_envio_gigante_e_recusado_antes_da_rota(self, client, cab_loja):
        """O CSV já tem teto de 512 KB, mas só depois de estar na memória."""
        enorme = b"x" * (settings.TAMANHO_MAXIMO_CORPO + 1024)

        resposta = client.post(
            "/peixes/importar",
            content=enorme,
            headers={**cab_loja, "Content-Type": "text/csv"},
        )

        assert resposta.status_code == 413
        assert "limite" in resposta.json()["detail"].lower()

    def test_envio_dentro_do_teto_chega_na_rota(self, client, cab_loja):
        resposta = client.post(
            "/peixes/importar",
            content="Neon Tetra\n".encode("utf-8"),
            headers={**cab_loja, "Content-Type": "text/csv"},
            params={"buscar": False},
        )
        assert resposta.status_code == 200


# ═══════════════════════════════════════════════════════
# ATRIBUIÇÃO EM MASSA
# ═══════════════════════════════════════════════════════
class TestCampoNaoDeclarado:
    def test_o_perfil_recusa_campo_que_nao_pediu(self, client, cab_loja):
        """`tipo` e `plano` existem no modelo, e não no contrato da rota."""
        resposta = client.patch(
            "/perfil/",
            json={"nome": "Aqualife", "tipo": "dono", "plano": "ilimitado"},
            headers=cab_loja,
        )
        assert resposta.status_code == 422

    def test_a_loja_nao_promove_o_cliente_a_dono(
        self, client, cab_loja, cliente
    ):
        resposta = client.put(
            f"/clientes/{cliente.id}",
            json={"nome": "Cliente", "tipo": "dono", "dono_id": str(uuid.uuid4())},
            headers=cab_loja,
        )
        assert resposta.status_code == 422

    def test_o_aquario_recusa_dono_escolhido_pelo_cliente(
        self, client, cab_loja, outra_loja
    ):
        resposta = client.post(
            "/aquarios/",
            json={
                "nome": "Invasor", "volume_litros": 100, "temperatura": 25,
                "ph": 7.0, "tipo": "comunitario",
                "usuario_id": str(outra_loja.id),
            },
            headers=cab_loja,
        )
        assert resposta.status_code == 422

    def test_a_ficha_recusa_campo_extra(self, client, cab_loja):
        resposta = client.post(
            "/fichas/",
            json={"nome_cliente": "Fulano", "dono_id": str(uuid.uuid4())},
            headers=cab_loja,
        )
        assert resposta.status_code == 422

    def test_o_campo_legitimo_continua_passando(self, client, cab_loja):
        """A trava não pode ter fechado a porta da frente junto."""
        resposta = client.patch(
            "/perfil/", json={"nome": "Aqualife Ecossistemas"}, headers=cab_loja
        )
        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Aqualife Ecossistemas"


# ═══════════════════════════════════════════════════════
# O QUE O LOGIN CONTA DE FORA
# ═══════════════════════════════════════════════════════
class TestLoginNaoEntregaNada:
    def test_conta_inexistente_e_senha_errada_dizem_o_mesmo(self, client, loja):
        """Mensagens diferentes viram lista de clientes da loja."""
        inexistente = client.post(
            "/auth/login",
            json={"cpf_cnpj": "529.982.247-25", "senha": "qualquer"},
        )
        errada = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "errada"}
        )

        assert inexistente.status_code == errada.status_code == 401
        assert inexistente.json() == errada.json()

    def test_a_senha_e_sempre_conferida(self, client):
        """Prova indireta do tempo igual: a rota não sai antes do bcrypt.

        Comparar relógio em teste é receita de falha intermitente. O que
        dá para afirmar sem flutuação é que a resposta da conta que não
        existe leva um tempo de mesma ordem — não microssegundos.
        """
        inicio = time.perf_counter()
        client.post(
            "/auth/login",
            json={"cpf_cnpj": "529.982.247-25", "senha": "qualquer"},
        )
        gasto = time.perf_counter() - inicio

        # Um bcrypt de custo 12 leva dezenas de milissegundos. Sem a
        # conferência de descarte, isto voltaria em menos de um.
        assert gasto > 0.005

    def test_o_token_nao_carrega_a_senha(self, client, loja):
        resposta = client.post(
            "/auth/login", json={"cpf_cnpj": loja.cpf_cnpj, "senha": "senha123"}
        )
        corpo = resposta.json()
        assert "senha" not in corpo and "senha_hash" not in corpo

        miolo = corpo["access_token"].split(".")[1]
        dados = json.loads(base64.urlsafe_b64decode(miolo + "=="))
        assert set(dados) == {"sub", "tipo", "iat", "exp"}


# ═══════════════════════════════════════════════════════
# TOKEN
# ═══════════════════════════════════════════════════════
class TestToken:
    def test_assinatura_de_outra_chave_e_recusada(self, client):
        forjado = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "tipo": "dono",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "chave-que-nao-e-a-nossa",
            algorithm="HS256",
        )
        resposta = client.get(
            "/aquarios/", headers={"Authorization": f"Bearer {forjado}"}
        )
        assert resposta.status_code == 401

    def test_token_sem_assinatura_e_recusado(self, client, loja):
        """A falha clássica de JWT: aceitar `alg: none`."""
        def pedaco(dado: dict) -> str:
            cru = json.dumps(dado, separators=(",", ":")).encode()
            return base64.urlsafe_b64encode(cru).decode().rstrip("=")

        vencimento = int(
            (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        )
        sem_assinatura = "{}.{}.".format(
            pedaco({"alg": "none", "typ": "JWT"}),
            pedaco({"sub": str(loja.id), "tipo": "dono", "exp": vencimento}),
        )

        resposta = client.get(
            "/aquarios/", headers={"Authorization": f"Bearer {sem_assinatura}"}
        )
        assert resposta.status_code == 401

    def test_token_vencido_e_recusado(self, client, loja, monkeypatch):
        monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
        vencido = criar_token({"sub": str(loja.id), "tipo": "dono"})

        resposta = client.get(
            "/aquarios/", headers={"Authorization": f"Bearer {vencido}"}
        )
        assert resposta.status_code == 401

    def test_token_sem_validade_e_recusado(self, client, loja):
        """Token eterno é token que vazou e nunca mais expira."""
        eterno = jwt.encode(
            {"sub": str(loja.id), "tipo": "dono"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        resposta = client.get(
            "/aquarios/", headers={"Authorization": f"Bearer {eterno}"}
        )
        assert resposta.status_code == 401

    def test_o_token_bom_continua_entrando(self, client, cab_loja):
        assert client.get("/aquarios/", headers=cab_loja).status_code == 200


# ═══════════════════════════════════════════════════════
# SENHA
# ═══════════════════════════════════════════════════════
class TestSenha:
    def test_o_hash_nao_guarda_a_senha(self):
        guardado = hash_senha("senha123")

        assert "senha123" not in guardado
        assert guardado.startswith("$2")          # bcrypt
        assert verificar_senha("senha123", guardado)

    def test_duas_contas_com_a_mesma_senha_tem_hashes_diferentes(self):
        """É o sal: sem ele, uma tabela pronta quebraria as duas de uma vez."""
        assert hash_senha("senha123") != hash_senha("senha123")

    def test_hash_estragado_responde_falso_em_vez_de_estourar(self):
        assert verificar_senha("senha123", "isto-nao-e-um-hash") is False


# ═══════════════════════════════════════════════════════
# HTTPS
# ═══════════════════════════════════════════════════════
class TestExigirHTTPS:
    @pytest.fixture
    def app_https(self):
        aplicacao = FastAPI()
        aplicacao.add_middleware(ExigirHTTPS)

        @aplicacao.get("/eco")
        def eco():
            return {"ok": True}

        @aplicacao.post("/eco")
        def eco_post():
            return {"ok": True}

        return TestClient(aplicacao, base_url="http://teste")

    def test_get_em_claro_e_redirecionado(self, app_https):
        resposta = app_https.get("/eco", follow_redirects=False)

        assert resposta.status_code == 307
        assert resposta.headers["location"].startswith("https://")

    def test_post_em_claro_e_recusado(self, app_https):
        """Redirecionar um POST faria o corpo viajar duas vezes, a primeira em claro."""
        assert app_https.post("/eco").status_code == 400

    def test_o_proxy_que_terminou_o_tls_e_aceito(self, app_https):
        resposta = app_https.post(
            "/eco", headers={"X-Forwarded-Proto": "https"}
        )
        assert resposta.status_code == 200

    def test_a_cadeia_de_proxies_e_lida_pelo_primeiro(self, app_https):
        resposta = app_https.post(
            "/eco", headers={"X-Forwarded-Proto": "https, http"}
        )
        assert resposta.status_code == 200


# ═══════════════════════════════════════════════════════
# CONFIGURAÇÃO PARA PRODUÇÃO
# ═══════════════════════════════════════════════════════
class TestConferenciaDeProducao:
    def montar(self, **campos) -> Settings:
        base = dict(
            DATABASE_URL="postgresql://u:s@servidor:5432/aqua?sslmode=require",
            SECRET_KEY="k" * 64,
            AMBIENTE="producao",
            DEBUG=False,
            SQL_ECHO=False,
            FORCAR_HTTPS=True,
            CORS_ORIGENS=[],
        )
        base.update(campos)
        return Settings(**base)

    def test_configuracao_correta_nao_aponta_nada(self):
        assert self.montar().conferir_para_producao() == []

    def test_chave_de_exemplo_e_apontada(self):
        problemas = self.montar(
            SECRET_KEY="troque-por-uma-chave-aleatoria-longa"
        ).conferir_para_producao()
        assert any("SECRET_KEY" in p for p in problemas)

    def test_chave_curta_e_apontada(self):
        problemas = self.montar(SECRET_KEY="curta").conferir_para_producao()
        assert any("mínimo" in p for p in problemas)

    def test_debug_ligado_e_apontado(self):
        problemas = self.montar(DEBUG=True).conferir_para_producao()
        assert any("DEBUG" in p for p in problemas)

    def test_cors_aberto_e_apontado(self):
        problemas = self.montar(CORS_ORIGENS=["*"]).conferir_para_producao()
        assert any("CORS" in p for p in problemas)

    def test_http_em_claro_e_apontado(self):
        problemas = self.montar(FORCAR_HTTPS=False).conferir_para_producao()
        assert any("HTTPS" in p for p in problemas)

    def test_banco_remoto_sem_tls_e_apontado(self):
        problemas = self.montar(
            DATABASE_URL="postgresql://u:s@servidor:5432/aqua"
        ).conferir_para_producao()
        assert any("sslmode" in p for p in problemas)

    def test_banco_local_nao_precisa_de_tls(self):
        problemas = self.montar(
            DATABASE_URL="postgresql://u:s@localhost:5432/aqua"
        ).conferir_para_producao()
        assert not any("sslmode" in p for p in problemas)

    def test_a_lista_de_origens_aceita_virgula(self):
        montado = Settings(
            DATABASE_URL="postgresql://u:s@localhost/a",
            SECRET_KEY="k" * 64,
            CORS_ORIGENS="https://a.com, https://b.com",
        )
        assert montado.CORS_ORIGENS == ["https://a.com", "https://b.com"]


# ═══════════════════════════════════════════════════════
# ESCRITA QUE ATRAVESSA A LOJA
# ═══════════════════════════════════════════════════════
class TestCadastroManualDeEspecie:
    """A rota de cadastro gravava no catálogo global de todas as lojas.

    Antes da migração 012 isso era o comportamento pretendido, porque
    catálogo só havia um. Depois dela, uma loja cadastrando uma espécie
    escrevia dentro do catálogo que as concorrentes enxergam.
    """

    NOVA = {
        "nome_comum": "Peixe da Loja A",
        "nome_cientifico": "Inventus fictus",
        "tipo_agua": "doce",
    }

    def test_a_especie_cadastrada_nasce_com_dono(self, client, cab_loja, loja, db):
        from app.models.especie import Especie

        criada = client.post("/peixes/", json=self.NOVA, headers=cab_loja)
        assert criada.status_code == 201

        gravada = db.query(Especie).filter(
            Especie.nome_comum == self.NOVA["nome_comum"]
        ).one()
        assert gravada.dono_id == loja.id

    def test_a_outra_loja_nao_enxerga(self, client, cab_loja, cab_outra_loja):
        client.post("/peixes/", json=self.NOVA, headers=cab_loja)

        alheias = [e["nome_comum"] for e in
                   client.get("/peixes/", headers=cab_outra_loja).json()]
        assert self.NOVA["nome_comum"] not in alheias

    def test_a_propria_loja_enxerga(self, client, cab_loja):
        client.post("/peixes/", json=self.NOVA, headers=cab_loja)

        minhas = [e["nome_comum"] for e in
                  client.get("/peixes/", headers=cab_loja).json()]
        assert self.NOVA["nome_comum"] in minhas

    def test_o_cadastro_recusa_campo_a_mais(self, client, cab_loja):
        """`Especie(**dados.model_dump())` é o que torna isto perigoso."""
        resposta = client.post(
            "/peixes/",
            json={**self.NOVA, "dono_id": None, "revisada": True},
            headers=cab_loja,
        )
        assert resposta.status_code == 422

    def test_o_cliente_nao_cadastra_especie(self, client, cab_cliente):
        assert client.post(
            "/peixes/", json=self.NOVA, headers=cab_cliente
        ).status_code == 403


# ═══════════════════════════════════════════════════════
# O CAMPO QUE A TELA MANDAVA E O SERVIDOR JOGAVA FORA
# ═══════════════════════════════════════════════════════
class TestClienteDaFichaNaEdicao:
    """Encontrado ao fechar a porta do campo não declarado.

    A tela de edição de ficha manda `cliente_id`, e `FichaUpdate` não o
    declarava: o Pydantic descartava em silêncio, e trocar o cliente de
    uma ficha nunca salvou. Declarar o campo consertou o recurso e, de
    quebra, exigiu conferir de quem é o cliente.
    """

    def criar_cliente(self, client, cabecalho, nome):
        return client.post(
            "/fichas/clientes", json={"nome": nome}, headers=cabecalho
        ).json()["id"]

    def criar_ficha(self, client, cabecalho, cliente_id):
        return client.post(
            "/fichas/", json={"cliente_id": cliente_id}, headers=cabecalho
        ).json()["id"]

    def test_trocar_o_cliente_da_ficha_agora_salva(self, client, cab_loja):
        primeiro = self.criar_cliente(client, cab_loja, "Cliente Um")
        segundo = self.criar_cliente(client, cab_loja, "Cliente Dois")
        ficha = self.criar_ficha(client, cab_loja, primeiro)

        resposta = client.put(
            f"/fichas/{ficha}", json={"cliente_id": segundo}, headers=cab_loja
        )

        assert resposta.status_code == 200
        assert resposta.json()["cliente_id"] == segundo

    def test_nao_religa_a_ficha_a_cliente_de_outra_loja(
        self, client, cab_loja, cab_outra_loja
    ):
        meu = self.criar_cliente(client, cab_loja, "Meu Cliente")
        alheio = self.criar_cliente(client, cab_outra_loja, "Cliente da Outra")
        ficha = self.criar_ficha(client, cab_loja, meu)

        resposta = client.put(
            f"/fichas/{ficha}", json={"cliente_id": alheio}, headers=cab_loja
        )

        assert resposta.status_code == 404
