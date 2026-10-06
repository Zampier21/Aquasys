"""Foto que a própria loja tira do peixe que vende.

A busca no acervo livre resolve o volume, mas não resolve o essencial:
o guppy do Wikimedia é um peixe selvagem acinzentado, e o que a loja
vende é uma variedade de cauda colorida. Quem compra quer ver o que vai
levar.

Por isso a foto da loja tem precedência e não é substituída pela busca
automática, que só olha espécie sem foto nenhuma.
"""

import io

import pytest
from PIL import Image

from app.models.especie import Especie, EspecieImagem
from app.services import imagens as svc_imagens


def foto(largura=1200, altura=800, cor=(20, 120, 180)) -> bytes:
    """Um JPEG de verdade, para o Pillow ter o que abrir."""
    buffer = io.BytesIO()
    Image.new("RGB", (largura, altura), cor).save(buffer, "JPEG", quality=85)
    return buffer.getvalue()


@pytest.fixture
def minha(db, loja):
    especie = Especie(nome_comum="Guppy", nome_cientifico="Poecilia reticulata",
                      dono_id=loja.id, revisada=False, ativo=True)
    db.add(especie)
    db.flush()
    return especie


@pytest.fixture
def curada(db):
    especie = Especie(nome_comum="Neon Tetra", ativo=True, revisada=True)
    db.add(especie)
    db.flush()
    return especie


def enviar(client, cabecalho, especie_id, conteudo):
    return client.post(
        f"/peixes/{especie_id}/imagem",
        content=conteudo,
        headers={**cabecalho, "Content-Type": "image/jpeg"},
    )


# ═══════════════════════════════════════════════════════
# ENVIO
# ═══════════════════════════════════════════════════════
class TestEnvio:
    def test_grava_as_duas_versoes(self, client, cab_loja, minha, db):
        r = enviar(client, cab_loja, minha.id, foto())

        assert r.status_code == 200
        linha = db.query(EspecieImagem).filter(
            EspecieImagem.especie_id == minha.id
        ).one()
        assert linha.miniatura and linha.completa
        # A completa é reduzida para o maior lado que o catálogo usa.
        assert linha.largura <= svc_imagens.MAIOR_LADO_COMPLETA

    def test_o_credito_e_da_loja(self, client, cab_loja, minha, db, loja):
        """Foto própria não vem de acervo com exigência de atribuição."""
        enviar(client, cab_loja, minha.id, foto())

        linha = db.query(EspecieImagem).one()
        assert linha.autor == loja.nome
        assert linha.fonte == "Foto da loja"
        assert linha.licenca is None

    def test_a_foto_aparece_no_catalogo(self, client, cab_loja, minha):
        enviar(client, cab_loja, minha.id, foto())

        catalogo = client.get("/peixes/", headers=cab_loja).json()
        guppy = next(e for e in catalogo if e["nome_comum"] == "Guppy")
        assert guppy["imagem_miniatura"] is not None

    def test_da_para_trocar_a_foto(self, client, cab_loja, minha, db):
        enviar(client, cab_loja, minha.id, foto(cor=(10, 10, 10)))
        primeiro = db.query(EspecieImagem).one().hash

        enviar(client, cab_loja, minha.id, foto(cor=(240, 80, 20)))
        db.expire_all()

        assert db.query(EspecieImagem).count() == 1
        assert db.query(EspecieImagem).one().hash != primeiro

    def test_trocar_a_foto_muda_o_endereco(self, client, cab_loja, minha):
        """Senão a loja troca a foto e continua vendo a antiga.

        A resposta da imagem é guardada por trinta dias, e o aplicativo
        guarda em disco também. O endereço carrega a identidade da foto
        justamente para mudar junto com ela.
        """
        def endereco():
            catalogo = client.get("/peixes/", headers=cab_loja).json()
            peixe = next(e for e in catalogo if e["nome_comum"] == "Guppy")
            return peixe["imagem_miniatura"]

        enviar(client, cab_loja, minha.id, foto(cor=(10, 10, 10)))
        primeiro = endereco()

        enviar(client, cab_loja, minha.id, foto(cor=(240, 80, 20)))
        assert endereco() != primeiro

    def test_a_rota_de_baixar_devolve_o_que_foi_enviado(
        self, client, cab_loja, minha
    ):
        enviar(client, cab_loja, minha.id, foto())

        r = client.get(f"/peixes/{minha.id}/imagem?tamanho=miniatura",
                       headers=cab_loja)
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/jpeg"
        assert Image.open(io.BytesIO(r.content)).size[0] > 0


class TestRecusas:
    def test_corpo_vazio(self, client, cab_loja, minha):
        assert enviar(client, cab_loja, minha.id, b"").status_code == 422

    def test_arquivo_que_nao_e_imagem(self, client, cab_loja, minha):
        r = enviar(client, cab_loja, minha.id, b"isto aqui nao e uma foto")

        assert r.status_code == 422
        assert "não pôde ser lida" in r.json()["detail"]

    def test_nao_envia_para_o_catalogo_curado(self, client, cab_loja, curada):
        """Mudaria a foto para todas as lojas."""
        r = enviar(client, cab_loja, curada.id, foto())
        assert r.status_code == 403

    def test_nao_envia_para_especie_de_outra_loja(
        self, client, cab_outra_loja, minha
    ):
        assert enviar(client, cab_outra_loja, minha.id, foto()).status_code == 404

    def test_o_cliente_nao_envia(self, client, cab_cliente, minha):
        assert enviar(client, cab_cliente, minha.id, foto()).status_code == 403


# ═══════════════════════════════════════════════════════
# CONVIVÊNCIA COM A BUSCA AUTOMÁTICA
# ═══════════════════════════════════════════════════════
class TestPrecedencia:
    @pytest.fixture
    def busca_que_sempre_acha(self, monkeypatch):
        class Falso:
            def close(self):
                pass

        monkeypatch.setattr(svc_imagens, "_cliente", lambda: Falso())
        monkeypatch.setattr(
            svc_imagens, "obter",
            lambda c, n=None, cliente=None: (
                svc_imagens.preparar(foto(cor=(250, 250, 250))),
                svc_imagens.FotoEncontrada(
                    url="x", fonte="commons", autor="Alguem",
                    licenca="CC BY-SA 4.0", licenca_url="y",
                ),
            ),
        )

    def test_a_busca_nao_passa_por_cima_da_foto_da_loja(
        self, client, cab_loja, minha, db, busca_que_sempre_acha
    ):
        enviar(client, cab_loja, minha.id, foto())

        corpo = client.post("/peixes/fotos/buscar", headers=cab_loja).json()

        assert corpo["tentadas"] == 0
        assert db.query(EspecieImagem).one().fonte == "Foto da loja"

    def test_depois_de_apagar_a_busca_volta_a_considerar(
        self, client, cab_loja, minha, db, busca_que_sempre_acha
    ):
        enviar(client, cab_loja, minha.id, foto())
        assert client.delete(
            f"/peixes/{minha.id}/imagem", headers=cab_loja
        ).status_code == 204
        assert db.query(EspecieImagem).count() == 0

        corpo = client.post("/peixes/fotos/buscar", headers=cab_loja).json()
        assert corpo["baixadas"] == 1
        assert db.query(EspecieImagem).one().fonte == "commons"


class TestRemocao:
    def test_remove(self, client, cab_loja, minha, db):
        enviar(client, cab_loja, minha.id, foto())
        client.delete(f"/peixes/{minha.id}/imagem", headers=cab_loja)
        assert db.query(EspecieImagem).count() == 0

    def test_remover_sem_foto_nao_estoura(self, client, cab_loja, minha):
        assert client.delete(
            f"/peixes/{minha.id}/imagem", headers=cab_loja
        ).status_code == 204

    def test_nao_remove_do_catalogo_curado(self, client, cab_loja, curada):
        assert client.delete(
            f"/peixes/{curada.id}/imagem", headers=cab_loja
        ).status_code == 403
