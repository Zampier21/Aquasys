import io

import pytest
from PIL import Image

from app.models.especie import Especie, EspecieImagem
from app.services import imagens


# ═══════════════════════════════════════════════════════
# AJUDANTES
# ═══════════════════════════════════════════════════════
def imagem_teste(largura=1600, altura=1200, modo="RGB", cor=(20, 130, 200)) -> bytes:
    formato = "PNG" if modo == "RGBA" else "JPEG"
    fundo = cor + (255,) if modo == "RGBA" else cor

    saida = io.BytesIO()
    Image.new(modo, (largura, altura), fundo).save(saida, format=formato)
    return saida.getvalue()


def abrir(bruto: bytes) -> Image.Image:
    return Image.open(io.BytesIO(bruto))


@pytest.fixture
def especie_com_foto(db):
    especie = Especie(nome_comum="Peixe de Teste", ativo=True)
    db.add(especie)
    db.flush()

    pronta = imagens.preparar(imagem_teste())
    db.add(EspecieImagem(
        especie_id=especie.id,
        miniatura=pronta.miniatura,
        completa=pronta.completa,
        mime=imagens.MIME,
        hash=pronta.hash,
        largura=pronta.largura,
        altura=pronta.altura,
        bytes_miniatura=len(pronta.miniatura),
        bytes_completa=len(pronta.completa),
        fonte="https://commons.wikimedia.org/wiki/File:Teste.jpg",
        autor="Fulano de Tal",
        licenca="CC BY-SA 4.0",
    ))
    db.flush()
    return especie


# ═══════════════════════════════════════════════════════
# PREPARO DA IMAGEM
# ═══════════════════════════════════════════════════════
class TestPreparar:
    def test_gera_as_duas_versoes(self):
        pronta = imagens.preparar(imagem_teste())
        assert pronta.completa and pronta.miniatura

    def test_a_completa_cabe_no_limite_e_mantem_a_proporcao(self):
        pronta = imagens.preparar(imagem_teste(1600, 1200))
        img = abrir(pronta.completa)

        assert max(img.size) <= imagens.MAIOR_LADO_COMPLETA
        # 4:3 na entrada, 4:3 na saída — nada de peixe esticado.
        assert abs(img.width / img.height - 4 / 3) < 0.02

    def test_a_miniatura_e_quadrada(self):
        # O círculo da lista exige quadrado; espremer deformaria o peixe.
        img = abrir(imagens.preparar(imagem_teste(1600, 400)).miniatura)
        assert img.size == (imagens.LADO_MINIATURA, imagens.LADO_MINIATURA)

    def test_imagem_menor_que_o_limite_nao_e_esticada(self):
        img = abrir(imagens.preparar(imagem_teste(300, 200)).completa)
        assert img.size == (300, 200)

    def test_sai_sempre_em_jpeg(self):
        pronta = imagens.preparar(imagem_teste(modo="RGBA"))
        assert abrir(pronta.completa).format == "JPEG"
        assert abrir(pronta.miniatura).format == "JPEG"

    def test_transparencia_vira_fundo_branco(self):
        # Sem achatar antes, PNG transparente sairia com fundo preto.
        saida = io.BytesIO()
        Image.new("RGBA", (400, 400), (255, 0, 0, 0)).save(saida, format="PNG")

        img = abrir(imagens.preparar(saida.getvalue()).completa).convert("RGB")
        assert img.getpixel((200, 200)) == pytest.approx((255, 255, 255), abs=4)

    def test_a_miniatura_e_bem_mais_leve_que_a_completa(self):
        # É a razão de existirem duas: a lista não pode puxar a foto cheia.
        pronta = imagens.preparar(imagem_teste())
        assert len(pronta.miniatura) < len(pronta.completa)

    def test_o_hash_e_estavel_para_a_mesma_entrada(self):
        bruto = imagem_teste()
        assert imagens.preparar(bruto).hash == imagens.preparar(bruto).hash

    def test_entradas_diferentes_dao_hashes_diferentes(self):
        a = imagens.preparar(imagem_teste(cor=(10, 10, 10)))
        b = imagens.preparar(imagem_teste(cor=(240, 240, 240)))
        assert a.hash != b.hash

    def test_arquivo_que_nao_e_imagem_levanta_erro_claro(self):
        with pytest.raises(imagens.ImagemInvalida):
            imagens.preparar(b"isso aqui nao e imagem nenhuma")

    def test_arquivo_vazio_levanta_erro_claro(self):
        with pytest.raises(imagens.ImagemInvalida):
            imagens.preparar(b"")


class TestReconheceImagem:
    @pytest.mark.parametrize("url", [
        "https://upload.wikimedia.org/x/Betta.jpg",
        "https://upload.wikimedia.org/x/Betta.jpg?utm_source=commons&utm_content=original",
        "https://upload.wikimedia.org/x/Peixe.JPEG",
        "File:Neon tetra.png",
        "https://exemplo.com/foto.webp?v=2",
    ])
    def test_aceita_imagem_mesmo_com_parametros_na_url(self, url):
        assert imagens._e_imagem(url) is True

    @pytest.mark.parametrize("url", [
        "https://upload.wikimedia.org/x/Betta.ogg",
        "File:Diagrama.svg",
        "https://exemplo.com/pagina",
        "https://exemplo.com/video.webm?jpg=1",
    ])
    def test_recusa_o_que_nao_e_foto(self, url):
        assert imagens._e_imagem(url) is False


class TestLicenca:
    """Foto de licença não-livre não entra: o produto é para vender."""

    @pytest.mark.parametrize("licenca", [
        "CC BY-SA 4.0", "CC BY 2.0", "CC0", "Public domain", "PD-US",
    ])
    def test_aceita_licenca_livre(self, licenca):
        metadados = {"LicenseShortName": {"value": licenca}}
        assert imagens._extrair_credito(metadados, "File:X.jpg") is not None

    @pytest.mark.parametrize("licenca", ["Fair use", "All rights reserved"])
    def test_recusa_licenca_restrita(self, licenca):
        metadados = {"LicenseShortName": {"value": licenca}}
        assert imagens._extrair_credito(metadados, "File:X.jpg") is None

    def test_o_autor_vem_limpo_de_html(self):
        metadados = {
            "LicenseShortName": {"value": "CC BY-SA 4.0"},
            "Artist": {"value": '<a href="https://x.com/fulano">Fulano</a>'},
        }
        achado = imagens._extrair_credito(metadados, "File:X.jpg")
        assert achado.autor == "Fulano"


# ═══════════════════════════════════════════════════════
# ROTA
# ═══════════════════════════════════════════════════════
class TestRotaDaImagem:
    def test_entrega_a_imagem_completa(self, client, especie_com_foto):
        r = client.get(f"/peixes/{especie_com_foto.id}/imagem")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/jpeg"
        assert abrir(r.content).format == "JPEG"

    def test_entrega_a_miniatura_quadrada(self, client, especie_com_foto):
        r = client.get(f"/peixes/{especie_com_foto.id}/imagem?tamanho=miniatura")
        assert r.status_code == 200
        assert abrir(r.content).size == (
            imagens.LADO_MINIATURA, imagens.LADO_MINIATURA,
        )

    def test_a_miniatura_pesa_menos_que_a_completa(self, client, especie_com_foto):
        url = f"/peixes/{especie_com_foto.id}/imagem"
        completa = client.get(url).content
        miniatura = client.get(f"{url}?tamanho=miniatura").content
        assert len(miniatura) < len(completa)

    def test_tamanho_desconhecido_e_recusado(self, client, especie_com_foto):
        r = client.get(f"/peixes/{especie_com_foto.id}/imagem?tamanho=gigante")
        assert r.status_code == 422

    def test_especie_sem_foto_da_404(self, client, db):
        especie = Especie(nome_comum="Sem foto", ativo=True)
        db.add(especie)
        db.flush()
        assert client.get(f"/peixes/{especie.id}/imagem").status_code == 404

    def test_dispensa_token(self, client, especie_com_foto):
        # O catálogo é o mesmo para todas as lojas e não tem dado de
        # ninguém. Exigir cabeçalho quebraria o cache da imagem e faria a
        # foto sumir quando a sessão vencesse, no meio da lista rolando.
        r = client.get(f"/peixes/{especie_com_foto.id}/imagem")
        assert r.status_code == 200


class TestCache:
    def test_manda_etag_e_cache_control(self, client, especie_com_foto):
        r = client.get(f"/peixes/{especie_com_foto.id}/imagem")
        assert r.headers["etag"]
        assert "max-age" in r.headers["cache-control"]

    def test_etag_conhecido_devolve_304_sem_corpo(self, client, especie_com_foto):
        url = f"/peixes/{especie_com_foto.id}/imagem"
        etag = client.get(url).headers["etag"]

        r = client.get(url, headers={"If-None-Match": etag})
        assert r.status_code == 304
        assert r.content == b""

    def test_a_miniatura_nao_responde_pelo_etag_da_completa(
        self, client, especie_com_foto
    ):
        # As duas saem da mesma linha do banco: sem o tamanho dentro do
        # ETag, o cache serviria a miniatura no lugar da foto grande.
        url = f"/peixes/{especie_com_foto.id}/imagem"
        etag_completa = client.get(url).headers["etag"]

        r = client.get(f"{url}?tamanho=miniatura",
                       headers={"If-None-Match": etag_completa})
        assert r.status_code == 200


class TestCatalogoAponta:
    def test_a_especie_com_foto_traz_os_caminhos_e_o_credito(
        self, client, cab_loja, especie_com_foto
    ):
        catalogo = client.get("/peixes/", headers=cab_loja).json()
        peixe = next(e for e in catalogo if e["id"] == str(especie_com_foto.id))

        # O `v` é a identidade da foto, e existe para o endereço mudar
        # quando a foto muda. Sem ele, trocar a foto de um peixe não
        # apareceria: a resposta é guardada por trinta dias.
        assert peixe["imagem"].startswith(
            f"/peixes/{especie_com_foto.id}/imagem?v="
        )
        assert "tamanho=miniatura" in peixe["imagem_miniatura"]
        assert "&v=" in peixe["imagem_miniatura"]
        # A licença CC exige exibir o crédito onde a foto aparece.
        assert peixe["imagem_credito"] == "Fulano de Tal (CC BY-SA 4.0)"

    def test_a_especie_sem_foto_vem_com_os_campos_nulos(self, client, cab_loja, db):
        # Nulo em vez de um caminho que dá 404: assim o app desenha o
        # ícone padrão sem gastar uma requisição perdida por peixe.
        db.add(Especie(nome_comum="Sem foto", ativo=True))
        db.flush()

        catalogo = client.get("/peixes/", headers=cab_loja).json()
        peixe = next(e for e in catalogo if e["nome_comum"] == "Sem foto")
        assert peixe["imagem"] is None
        assert peixe["imagem_miniatura"] is None
        assert peixe["imagem_credito"] is None

    def test_o_habitante_do_aquario_tambem_traz_a_miniatura(
        self, client, cab_loja, db, especie_com_foto
    ):
        from app.models.especie import AquarioEspecie

        aquario = client.post("/aquarios/", json={
            "nome": "Teste", "volume_litros": 100,
            "temperatura": 26, "ph": 6.8,
        }, headers=cab_loja).json()

        db.add(AquarioEspecie(
            aquario_id=aquario["id"], especie_id=especie_com_foto.id, quantidade=3
        ))
        db.flush()

        habitantes = client.get(
            f"/peixes/aquario/{aquario['id']}", headers=cab_loja
        ).json()
        assert "tamanho=miniatura" in habitantes[0]["imagem_miniatura"]
        assert "&v=" in habitantes[0]["imagem_miniatura"]


class TestPesoDoCatalogo:
    def test_listar_especies_nao_carrega_os_bytes_das_fotos(
        self, client, cab_loja, especie_com_foto
    ):
        # A razão de a imagem morar em tabela separada. Se um dia alguém
        # trocar isso por um `selectinload`, o catálogo inteiro passa a
        # trafegar em cada abertura da aba Peixes — e este teste avisa.
        resposta = client.get("/peixes/", headers=cab_loja)
        assert resposta.status_code == 200
        assert len(resposta.content) < 60_000


# ═══════════════════════════════════════════════════════
# MEMÓRIA: O QUE CAUSOU UM 502 EM PRODUÇÃO
# ═══════════════════════════════════════════════════════
class TestTamanhoDaOrigem:
    """Baixar o original do Commons matou o servidor de 512 MB.

    Medindo seis espécies do catálogo, os originais tinham de 5 a 10
    megapixels e arquivos de até 7 MB. O Pillow precisa de uns 29 MB só
    para abrir um de 10 MP, e faz cópias para girar pelo EXIF, achatar
    transparência e redimensionar. Num lote de fotos, o processo morria
    e o Render respondia 502.

    A correção foi pedir ao Commons a versão já reduzida por ele.
    Depois dela, o pico medido por foto caiu para 1,6 MB.
    """

    def test_pede_a_largura_reduzida_ao_commons(self):
        """`iiurlwidth` é o que faz o Commons gerar a miniatura."""
        assert imagens.LARGURA_PEDIDA >= imagens.MAIOR_LADO_COMPLETA
        # Pedir menos do que o card mostra entregaria foto borrada.
        assert imagens.LARGURA_PEDIDA <= 2000

    def test_prefere_a_reduzida_quando_ela_vem(self, monkeypatch):
        def responder(cliente, url, params):
            return {"query": {"pages": {"1": {"imageinfo": [{
                "url": "https://upload.wikimedia.org/Peixe.jpg",
                "thumburl": "https://upload.wikimedia.org/thumb/Peixe.jpg",
                "extmetadata": {
                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                    "Artist": {"value": "Fulano"},
                },
            }]}}}}

        monkeypatch.setattr(imagens, "_pedir", responder)
        achado = imagens._detalhes_do_arquivo(None, "File:Peixe.jpg")

        assert achado is not None
        assert "/thumb/" in achado.url

    def test_cai_para_o_original_se_nao_houver_reduzida(self, monkeypatch):
        """Alguns formatos antigos o Commons não consegue reduzir."""
        def responder(cliente, url, params):
            return {"query": {"pages": {"1": {"imageinfo": [{
                "url": "https://upload.wikimedia.org/Peixe.jpg",
                "extmetadata": {
                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                    "Artist": {"value": "Fulano"},
                },
            }]}}}}

        monkeypatch.setattr(imagens, "_pedir", responder)
        achado = imagens._detalhes_do_arquivo(None, "File:Peixe.jpg")

        assert achado is not None
        assert achado.url.endswith("/Peixe.jpg")

    def test_recusa_imagem_absurda_antes_de_descomprimir(self):
        """A recusa precisa vir antes do `load()`, que é quem estoura."""
        enorme = imagem_teste(largura=9000, altura=6000)

        # 54 MP passa do teto de 40 MP.
        with pytest.raises(imagens.ImagemInvalida) as erro:
            imagens.preparar(enorme)
        assert "grande demais" in str(erro.value)

    def test_imagem_grande_mas_dentro_do_teto_passa(self):
        pronta = imagens.preparar(imagem_teste(largura=3000, altura=2000))
        assert pronta.largura <= imagens.MAIOR_LADO_COMPLETA
