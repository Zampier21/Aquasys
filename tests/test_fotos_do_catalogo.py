"""Busca de fotos para as espécies que a loja importou.

A importação criava espécie sem foto nenhuma, e um catálogo de peixe
sem foto não serve para escolher peixe. A máquina de imagens já
existia, mas só era alcançável pelo script `baixar_imagens.py`, que
roda na máquina do desenvolvedor.

Nenhum caso aqui vai à rede: a busca real leva cerca de 3,5 segundos
por espécie, e a suíte não é lugar de medir o Wikimedia Commons. O que
se prova é o recorte (de quem são as espécies), o lote, e a regra que
mais importa: uma foto que falha não pode levar junto as que já deram
certo.
"""

import pytest

from app.models.especie import Especie, EspecieImagem
from app.services import imagens as svc_imagens


def pronta(tamanho: int = 64):
    """Um resultado de preparo, sem passar pelo Pillow."""
    return svc_imagens.ImagemPronta(
        completa=b"\xff\xd8\xff" + b"c" * tamanho,
        miniatura=b"\xff\xd8\xff" + b"m" * (tamanho // 4),
        largura=900,
        altura=600,
        hash="a" * 64,
    )


def achado(autor="Fulano", licenca="CC BY-SA 4.0"):
    return svc_imagens.FotoEncontrada(
        url="https://upload.wikimedia.org/exemplo.jpg",
        fonte="https://commons.wikimedia.org/wiki/File:exemplo.jpg",
        autor=autor,
        licenca=licenca,
        licenca_url="https://creativecommons.org/licenses/by-sa/4.0/",
    )


@pytest.fixture
def sem_rede(monkeypatch):
    """Toda espécie acha foto, sem sair da máquina."""
    monkeypatch.setattr(svc_imagens, "_cliente", lambda: _ClienteFalso())
    monkeypatch.setattr(
        svc_imagens, "obter",
        lambda cientifico, comum=None, cliente=None: (pronta(), achado()),
    )


class _ClienteFalso:
    def close(self):
        pass


@pytest.fixture
def importadas(db, loja):
    """Três espécies da loja, como a importação as deixa: sem foto."""
    especies = [
        Especie(nome_comum="Barbo Sumatra",
                nome_cientifico="Puntigrus tetrazona",
                dono_id=loja.id, revisada=False, ativo=True),
        Especie(nome_comum="Guppy", nome_cientifico="Poecilia reticulata",
                dono_id=loja.id, revisada=False, ativo=True),
        Especie(nome_comum="Molinesia", nome_cientifico="Poecilia sphenops",
                dono_id=loja.id, revisada=False, ativo=True),
    ]
    for e in especies:
        db.add(e)
    db.flush()
    return especies


def buscar(client, cabecalho, **params):
    return client.post("/peixes/fotos/buscar", headers=cabecalho, params=params)


# ═══════════════════════════════════════════════════════
# O LOTE
# ═══════════════════════════════════════════════════════
class TestRodada:
    def test_baixa_e_grava(self, client, cab_loja, importadas, db, sem_rede):
        corpo = buscar(client, cab_loja).json()

        assert corpo["tentadas"] == 3
        assert corpo["baixadas"] == 3
        assert corpo["restantes"] == 0
        assert db.query(EspecieImagem).count() == 3

    def test_respeita_o_limite_da_rodada(
        self, client, cab_loja, importadas, db, sem_rede
    ):
        """Cada foto leva uns 3,5 s; a rodada tem que caber na requisição."""
        corpo = buscar(client, cab_loja, limite=2).json()

        assert corpo["tentadas"] == 2
        assert corpo["baixadas"] == 2
        assert corpo["restantes"] == 1
        assert db.query(EspecieImagem).count() == 2

    def test_a_rodada_seguinte_pega_o_que_sobrou(
        self, client, cab_loja, importadas, db, sem_rede
    ):
        buscar(client, cab_loja, limite=2)
        corpo = buscar(client, cab_loja, limite=2).json()

        assert corpo["baixadas"] == 1
        assert corpo["restantes"] == 0
        assert db.query(EspecieImagem).count() == 3

    def test_nao_rebaixa_quem_ja_tem(
        self, client, cab_loja, importadas, db, sem_rede
    ):
        buscar(client, cab_loja)
        corpo = buscar(client, cab_loja).json()

        assert corpo["tentadas"] == 0
        assert corpo["restantes"] == 0

    def test_limite_fora_da_faixa_e_recusado(
        self, client, cab_loja, importadas, sem_rede
    ):
        assert buscar(client, cab_loja, limite=0).status_code == 422
        assert buscar(client, cab_loja, limite=99).status_code == 422


# ═══════════════════════════════════════════════════════
# QUANDO NÃO ACHA
# ═══════════════════════════════════════════════════════
class TestSemFoto:
    def test_diz_quais_nao_foram_encontradas(
        self, client, cab_loja, importadas, db, monkeypatch
    ):
        monkeypatch.setattr(svc_imagens, "_cliente", lambda: _ClienteFalso())
        monkeypatch.setattr(
            svc_imagens, "obter",
            lambda cientifico, comum=None, cliente=None: None,
        )
        corpo = buscar(client, cab_loja).json()

        assert corpo["baixadas"] == 0
        assert corpo["restantes"] == 3
        assert set(corpo["nao_encontradas"]) == {
            "Barbo Sumatra", "Guppy", "Molinesia"
        }
        assert db.query(EspecieImagem).count() == 0

    def test_uma_falha_nao_leva_as_que_deram_certo(
        self, client, cab_loja, importadas, db, monkeypatch
    ):
        """A regra central deste arquivo.

        Sem commit por espécie, a exceção na terceira desfaria as duas
        primeiras, e a loja repetiria a rodada inteira sem entender por
        que nada avança.
        """
        monkeypatch.setattr(svc_imagens, "_cliente", lambda: _ClienteFalso())

        def as_vezes(cientifico, comum=None, cliente=None):
            if cientifico == "Poecilia sphenops":
                raise RuntimeError("o Commons devolveu lixo")
            return pronta(), achado()

        monkeypatch.setattr(svc_imagens, "obter", as_vezes)
        corpo = buscar(client, cab_loja).json()

        assert corpo["baixadas"] == 2
        assert corpo["restantes"] == 1
        assert db.query(EspecieImagem).count() == 2

    def test_a_rota_nao_estoura_com_erro_da_fonte(
        self, client, cab_loja, importadas, monkeypatch
    ):
        """Dado de terceiro quebrado não é erro 500 do AquaSys."""
        monkeypatch.setattr(svc_imagens, "_cliente", lambda: _ClienteFalso())

        def cair(cientifico, comum=None, cliente=None):
            raise RuntimeError("fora do ar")

        monkeypatch.setattr(svc_imagens, "obter", cair)
        assert buscar(client, cab_loja).status_code == 200


# ═══════════════════════════════════════════════════════
# DE QUEM SÃO AS ESPÉCIES
# ═══════════════════════════════════════════════════════
class TestRecorte:
    def test_nao_mexe_no_catalogo_curado(
        self, client, cab_loja, db, sem_rede
    ):
        """As curadas já têm foto, e não seriam da loja para alterar."""
        curada = Especie(nome_comum="Neon Tetra",
                         nome_cientifico="Paracheirodon innesi",
                         ativo=True, revisada=True)
        db.add(curada)
        db.flush()

        corpo = buscar(client, cab_loja).json()

        assert corpo["tentadas"] == 0
        assert db.query(EspecieImagem).count() == 0

    def test_nao_mexe_na_especie_de_outra_loja(
        self, client, cab_outra_loja, importadas, db, sem_rede
    ):
        corpo = buscar(client, cab_outra_loja).json()

        assert corpo["tentadas"] == 0
        assert db.query(EspecieImagem).count() == 0

    def test_ignora_variedade(self, client, cab_loja, db, loja, sem_rede):
        """Variedade herda a foto da base; buscar outra duplicaria."""
        base = Especie(nome_comum="Acará", dono_id=loja.id, ativo=True)
        db.add(base)
        db.flush()
        db.add(Especie(nome_comum="Acará Leopardo", dono_id=loja.id,
                       ativo=True, variante_de_id=base.id))
        db.flush()

        corpo = buscar(client, cab_loja).json()
        assert corpo["tentadas"] == 1

    def test_o_cliente_nao_busca_foto(self, client, cab_cliente, importadas):
        assert buscar(client, cab_cliente).status_code == 403


# ═══════════════════════════════════════════════════════
# CRÉDITO
# ═══════════════════════════════════════════════════════
class TestCredito:
    def test_grava_autor_licenca_e_fonte(
        self, client, cab_loja, importadas, db, sem_rede
    ):
        """As fotos do Commons exigem atribuição; sem isto não dá para dar."""
        buscar(client, cab_loja, limite=1)

        linha = db.query(EspecieImagem).first()
        assert linha.autor == "Fulano"
        assert linha.licenca == "CC BY-SA 4.0"
        assert linha.fonte.startswith("https://commons.wikimedia.org/")
        assert linha.credito == "Fulano (CC BY-SA 4.0)"

    def test_grava_as_duas_versoes_e_as_medidas(
        self, client, cab_loja, importadas, db, sem_rede
    ):
        buscar(client, cab_loja, limite=1)

        linha = db.query(EspecieImagem).first()
        assert linha.miniatura and linha.completa
        assert linha.bytes_miniatura == len(linha.miniatura)
        assert linha.bytes_completa == len(linha.completa)
        assert (linha.largura, linha.altura) == (900, 600)


# ═══════════════════════════════════════════════════════
# A FOTO CHEGA NO APLICATIVO
# ═══════════════════════════════════════════════════════
class TestNaRespostaDoCatalogo:
    def test_a_especie_passa_a_ter_miniatura_na_listagem(
        self, client, cab_loja, importadas, sem_rede
    ):
        antes = client.get("/peixes/", headers=cab_loja).json()
        assert all(e["imagem_miniatura"] is None for e in antes)

        buscar(client, cab_loja)

        depois = client.get("/peixes/", headers=cab_loja).json()
        assert all(e["imagem_miniatura"] is not None for e in depois)

    def test_o_credito_sai_junto(self, client, cab_loja, importadas, sem_rede):
        buscar(client, cab_loja, limite=1)

        catalogo = client.get("/peixes/", headers=cab_loja).json()
        com_foto = [e for e in catalogo if e["imagem_miniatura"]]
        assert com_foto[0]["imagem_credito"] == "Fulano (CC BY-SA 4.0)"
