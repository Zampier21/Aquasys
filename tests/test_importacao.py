"""Importação da lista de peixes da loja.

O arquivo vem do sistema de estoque de uma loja, e não de um formulário
controlado: chega com ponto e vírgula, acento em Latin-1, marcador de
ordem de bytes do Excel, coluna extra de preço e nome digitado errado.
Os testes cobrem esse material, e não um CSV ideal.
"""

import pytest

from app.models.especie import Especie
from app.services import importacao


def subir(client, cabecalho, conteudo):
    if isinstance(conteudo, str):
        conteudo = conteudo.encode("utf-8")
    return client.post("/peixes/importar", content=conteudo, headers=cabecalho)


@pytest.fixture
def catalogo(db):
    """Três espécies e uma variedade, com nomes que se confundem."""
    especies = [
        Especie(nome_comum="Neon Tetra", nome_cientifico="Paracheirodon innesi",
                nomes_alternativos="tetra neon, neon azul", ativo=True),
        Especie(nome_comum="Acará Bandeira",
                nome_cientifico="Pterophyllum scalare",
                nomes_alternativos="escalar, peixe anjo", ativo=True),
        Especie(nome_comum="Acará Disco",
                nome_cientifico="Symphysodon aequifasciatus",
                nomes_alternativos="disco, discus", ativo=True),
        Especie(nome_comum="Betta", nome_cientifico="Betta splendens",
                nomes_alternativos="beta", ativo=True),
    ]
    for e in especies:
        db.add(e)
    db.flush()
    variedade = Especie(nome_comum="Betta Halfmoon", variante_de_id=especies[3].id,
                        nome_cientifico="Betta splendens", ativo=True)
    db.add(variedade)
    db.flush()
    return especies


# ═══════════════════════════════════════════════════════
# LEITURA DO ARQUIVO
# ═══════════════════════════════════════════════════════
class TestLeitura:
    def test_uma_coluna_sem_cabecalho(self):
        assert importacao.ler_nomes(b"Betta\nNeon Tetra\n") == ["Betta", "Neon Tetra"]

    def test_cabecalho_e_reconhecido_e_descartado(self):
        bruto = "nome;preco\nBetta;35,00\nNeon Tetra;7,50\n".encode()
        assert importacao.ler_nomes(bruto) == ["Betta", "Neon Tetra"]

    def test_sem_cabecalho_a_primeira_coluna_e_o_nome(self):
        bruto = "Betta;35,00\nNeon Tetra;7,50\n".encode()
        assert importacao.ler_nomes(bruto) == ["Betta", "Neon Tetra"]

    def test_marcador_do_excel_nao_vira_lixo_no_primeiro_nome(self):
        """O Excel brasileiro grava BOM; sem tratá-lo, o nome não casaria."""
        bruto = "nome\nBetta\n".encode("utf-8-sig")
        assert importacao.ler_nomes(bruto) == ["Betta"]

    def test_acento_em_latin1(self):
        bruto = "Acará Bandeira\n".encode("latin-1")
        assert importacao.ler_nomes(bruto) == ["Acará Bandeira"]

    def test_separador_por_tabulacao(self):
        assert importacao.ler_nomes(b"nome\tqtd\nBetta\t3\n") == ["Betta"]

    def test_linhas_em_branco_somem(self):
        assert importacao.ler_nomes(b"Betta\n\n\nNeon Tetra\n") == ["Betta", "Neon Tetra"]

    def test_arquivo_vazio_e_recusado(self):
        with pytest.raises(importacao.ArquivoInvalido):
            importacao.ler_nomes(b"   \n")

    def test_binario_renomeado_e_recusado(self):
        """Em latin-1 qualquer byte decodifica; o nulo é o que denuncia."""
        with pytest.raises(importacao.ArquivoInvalido):
            importacao.ler_nomes(b"\x89PNG\x00\x1a\n\x00algo")

    def test_arquivo_grande_demais_e_recusado(self):
        with pytest.raises(importacao.ArquivoInvalido):
            importacao.ler_nomes(b"Betta\n" * 200_000)

    def test_lista_longa_demais_e_recusada(self):
        with pytest.raises(importacao.ArquivoInvalido):
            importacao.ler_nomes(b"Betta\n" * (importacao.LIMITE_NOMES + 1))


# ═══════════════════════════════════════════════════════
# CASAMENTO
# ═══════════════════════════════════════════════════════
class TestCasamento:
    def test_nome_exato(self, db, catalogo):
        (r,) = importacao.casar(["Neon Tetra"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Neon Tetra"
        assert r.como == "nome do catálogo"

    def test_sem_acento_e_em_caixa_qualquer(self, db, catalogo):
        (r,) = importacao.casar(["acara bandeira"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Acará Bandeira"

    def test_nome_popular_alternativo(self, db, catalogo):
        (r,) = importacao.casar(["escalar"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Acará Bandeira"
        assert r.como == "outro nome da mesma espécie"

    def test_nome_cientifico(self, db, catalogo):
        (r,) = importacao.casar(["Paracheirodon innesi"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Neon Tetra"

    def test_nome_parcial_que_serve_a_dois_fica_ambiguo(self, db, catalogo):
        (r,) = importacao.casar(["Acará"], db)
        assert r.situacao == "ambiguo"
        assert {c.nome_comum for c in r.candidatos} == {
            "Acará Bandeira", "Acará Disco"
        }

    def test_nome_da_especie_base_nao_fica_ambiguo_com_a_variedade(
        self, db, catalogo
    ):
        """"Betta" é o nome exato da base, e exato ganha do parcial."""
        (r,) = importacao.casar(["Betta"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Betta"

    def test_variedade_e_encontrada_pelo_nome_inteiro(self, db, catalogo):
        (r,) = importacao.casar(["Betta Halfmoon"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Betta Halfmoon"

    def test_nome_desconhecido_vem_com_sugestao(self, db, catalogo):
        (r,) = importacao.casar(["Neon Tetrra"], db)
        assert r.situacao == "nao_encontrado"
        assert "Neon Tetra" in r.sugestoes

    def test_peixe_que_nao_existe_no_catalogo(self, db, catalogo):
        (r,) = importacao.casar(["Tubarão Branco"], db)
        assert r.situacao == "nao_encontrado"

    def test_nome_repetido_vira_uma_linha_com_a_contagem(self, db, catalogo):
        resultado = importacao.casar(["Betta", "betta", "BETTA"], db)
        assert len(resultado) == 1
        assert resultado[0].vezes == 3

    def test_especie_desativada_fica_fora(self, db, catalogo):
        catalogo[0].ativo = False
        db.flush()
        (r,) = importacao.casar(["Neon Tetra"], db)
        assert r.situacao == "nao_encontrado"


# ═══════════════════════════════════════════════════════
# ROTA
# ═══════════════════════════════════════════════════════
class TestRota:
    def test_relatorio_completo(self, client, cab_loja, catalogo):
        arquivo = "nome;quantidade\nBetta;4\nescalar;2\nAcará;1\nXis;9\nBetta;7\n"
        r = subir(client, cab_loja, arquivo)
        assert r.status_code == 200

        corpo = r.json()
        assert corpo["total_linhas"] == 5      # conta a repetição
        assert corpo["total_nomes"] == 4       # nomes distintos
        assert corpo["encontrados"] == 2       # Betta e escalar
        assert corpo["ambiguos"] == 1          # Acará
        assert corpo["nao_encontrados"] == 1   # Xis

        por_nome = {i["nome_lido"]: i for i in corpo["itens"]}
        assert por_nome["Betta"]["vezes"] == 2
        assert por_nome["escalar"]["nome_comum"] == "Acará Bandeira"
        assert len(por_nome["Acará"]["candidatos"]) == 2

    def test_variedade_informa_a_especie_base(self, client, cab_loja, catalogo):
        corpo = subir(client, cab_loja, "Betta Halfmoon\n").json()
        assert corpo["itens"][0]["variedade_de"] == "Betta"

    def test_nada_e_gravado_no_catalogo(self, client, cab_loja, catalogo, db):
        antes = db.query(Especie).count()
        subir(client, cab_loja, "Xis\nIpsilon\nZe\n")
        assert db.query(Especie).count() == antes

    def test_arquivo_invalido_explica_o_motivo(self, client, cab_loja, catalogo):
        r = subir(client, cab_loja, b"")
        assert r.status_code == 422
        assert "vazio" in r.json()["detail"].lower()

    def test_cliente_nao_importa(self, client, cab_cliente, catalogo):
        assert subir(client, cab_cliente, "Betta\n").status_code == 403

    def test_exige_autenticacao(self, client, catalogo):
        assert subir(client, {}, "Betta\n").status_code in (401, 403)


class TestVariedadesNaoViramRuido:
    """A variedade herda os nomes populares da base, e sem cuidado isso
    transformava todo nome popular numa lista de oito candidatos."""

    @pytest.fixture
    def com_variedades(self, db, catalogo):
        bandeira, disco = catalogo[1], catalogo[2]
        for base, sufixos in ((bandeira, ["Marmorato", "Koi", "Véu"]),
                              (disco, ["Leopardo"])):
            for sufixo in sufixos:
                db.add(Especie(
                    nome_comum=f"{base.nome_comum} {sufixo}",
                    nome_cientifico=base.nome_cientifico,
                    nomes_alternativos=base.nomes_alternativos,
                    variante_de_id=base.id,
                    ativo=True,
                ))
        db.flush()

    def test_nome_popular_da_base_resolve_na_base(self, db, com_variedades):
        (r,) = importacao.casar(["escalar"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Acará Bandeira"

    def test_ambiguidade_real_pergunta_por_especie_e_nao_por_variedade(
        self, db, com_variedades
    ):
        (r,) = importacao.casar(["Acará"], db)
        assert r.situacao == "ambiguo"
        assert {c.nome_comum for c in r.candidatos} == {
            "Acará Bandeira", "Acará Disco"
        }

    def test_a_variedade_continua_alcancavel_pelo_nome_inteiro(
        self, db, com_variedades
    ):
        (r,) = importacao.casar(["Acará Bandeira Koi"], db)
        assert r.situacao == "encontrado"
        assert r.especie.nome_comum == "Acará Bandeira Koi"


class TestComoOAplicativoEnvia:
    """O app manda os bytes crus com Content-Type de CSV, e não JSON."""

    def test_content_type_de_csv_e_aceito(self, client, cab_loja, catalogo):
        r = client.post(
            "/peixes/importar",
            content="Betta\nNeon Tetra\n".encode("utf-8"),
            headers={**cab_loja, "Content-Type": "text/csv"},
        )
        assert r.status_code == 200
        assert r.json()["encontrados"] == 2

    def test_arquivo_do_excel_com_marcador_de_bytes(self, client, cab_loja, catalogo):
        r = client.post(
            "/peixes/importar",
            content="nome;preco\nBetta;35\n".encode("utf-8-sig"),
            headers={**cab_loja, "Content-Type": "text/csv"},
        )
        assert r.json()["encontrados"] == 1
