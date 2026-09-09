"""
Testes de cursos.

Duas regras a prender:
  - publicar é da loja; o cliente só assiste;
  - o progresso é de cada pessoa, não do curso.
"""

import pytest

from app.models.curso import Aula, Curso


@pytest.fixture
def curso_global(db):
    """Curso do AquaSys: `dono_id` nulo, visível a todos."""
    curso = Curso(dono_id=None, titulo="Curso Global", ativo=True)
    db.add(curso)
    db.flush()
    for i in range(4):
        db.add(Aula(
            curso_id=curso.id,
            titulo=f"Aula {i + 1}",
            youtube_id=f"video{i:06d}x",
            ordem=i,
        ))
    db.flush()
    return curso


@pytest.fixture
def curso_da_loja(db, loja):
    curso = Curso(dono_id=loja.id, titulo="Curso da Loja A", ativo=True)
    db.add(curso)
    db.flush()
    db.add(Aula(curso_id=curso.id, titulo="Única", youtube_id="soUmVideo1", ordem=0))
    db.flush()
    return curso


class TestVisibilidade:
    def test_todos_veem_o_curso_global(
        self, client, cab_loja, cab_cliente, curso_global
    ):
        for cabecalho in (cab_loja, cab_cliente):
            titulos = [c["titulo"] for c in client.get("/cursos/", headers=cabecalho).json()]
            assert "Curso Global" in titulos

    def test_cliente_ve_o_curso_da_loja_dele(
        self, client, cab_cliente, curso_da_loja
    ):
        titulos = [c["titulo"] for c in client.get("/cursos/", headers=cab_cliente).json()]
        assert "Curso da Loja A" in titulos

    def test_outra_loja_nao_ve_o_curso_da_primeira(
        self, client, cab_outra_loja, curso_da_loja
    ):
        titulos = [
            c["titulo"] for c in client.get("/cursos/", headers=cab_outra_loja).json()
        ]
        assert "Curso da Loja A" not in titulos

    def test_curso_desativado_some_da_lista(
        self, client, db, cab_loja, curso_da_loja
    ):
        curso_da_loja.ativo = False
        db.flush()
        titulos = [c["titulo"] for c in client.get("/cursos/", headers=cab_loja).json()]
        assert "Curso da Loja A" not in titulos

    def test_a_resposta_diz_se_o_curso_e_global(
        self, client, cab_loja, curso_global, curso_da_loja
    ):
        por_titulo = {
            c["titulo"]: c["curso_global"]
            for c in client.get("/cursos/", headers=cab_loja).json()
        }
        assert por_titulo["Curso Global"] is True
        assert por_titulo["Curso da Loja A"] is False


class TestQuemPodePublicar:
    def test_loja_cria_curso(self, client, cab_loja):
        r = client.post("/cursos/", json={"titulo": "Novo"}, headers=cab_loja)
        assert r.status_code == 201
        assert r.json()["curso_global"] is False  # nasce da loja, nunca global

    def test_cliente_nao_cria_curso(self, client, cab_cliente):
        r = client.post("/cursos/", json={"titulo": "Não pode"}, headers=cab_cliente)
        assert r.status_code == 403

    def test_cliente_nao_adiciona_aula(self, client, cab_cliente, curso_da_loja):
        r = client.post(
            f"/cursos/{curso_da_loja.id}/aulas",
            json={"url": "https://youtu.be/dQw4w9WgXcQ"},
            headers=cab_cliente,
        )
        assert r.status_code == 403

    def test_cliente_nao_apaga_curso(self, client, cab_cliente, curso_da_loja):
        r = client.delete(f"/cursos/{curso_da_loja.id}", headers=cab_cliente)
        assert r.status_code == 403

    def test_nem_a_loja_edita_curso_global(self, client, cab_loja, curso_global):
        # Conteúdo do AquaSys não é editável por assinante nenhum.
        r = client.delete(f"/cursos/{curso_global.id}", headers=cab_loja)
        assert r.status_code == 404


class TestProgresso:
    def test_marcar_aula_muda_o_percentual(
        self, client, cab_cliente, curso_global
    ):
        aula = client.get(
            f"/cursos/{curso_global.id}", headers=cab_cliente
        ).json()["aulas"][0]

        r = client.patch(
            f"/cursos/aulas/{aula['id']}/concluida?concluida=true",
            headers=cab_cliente,
        )
        assert r.status_code == 200
        assert r.json()["percentual"] == 25  # 1 de 4 aulas

    def test_desmarcar_volta_a_zero(self, client, cab_cliente, curso_global):
        aula = client.get(
            f"/cursos/{curso_global.id}", headers=cab_cliente
        ).json()["aulas"][0]

        client.patch(
            f"/cursos/aulas/{aula['id']}/concluida?concluida=true",
            headers=cab_cliente,
        )
        r = client.patch(
            f"/cursos/aulas/{aula['id']}/concluida?concluida=false",
            headers=cab_cliente,
        )
        assert r.json()["percentual"] == 0

    def test_progresso_e_de_cada_pessoa(
        self, client, cab_cliente, cab_loja, curso_global
    ):
        aula = client.get(
            f"/cursos/{curso_global.id}", headers=cab_cliente
        ).json()["aulas"][0]

        client.patch(
            f"/cursos/aulas/{aula['id']}/concluida?concluida=true",
            headers=cab_cliente,
        )

        def percentual(cabecalho):
            cursos = client.get("/cursos/", headers=cabecalho).json()
            return next(c["percentual"] for c in cursos if c["titulo"] == "Curso Global")

        assert percentual(cab_cliente) == 25
        assert percentual(cab_loja) == 0  # a loja não herda o progresso

    def test_curso_sem_aula_nao_divide_por_zero(self, client, db, cab_loja):
        vazio = Curso(dono_id=None, titulo="Sem aulas", ativo=True)
        db.add(vazio)
        db.flush()

        cursos = client.get("/cursos/", headers=cab_loja).json()
        sem_aulas = next(c for c in cursos if c["titulo"] == "Sem aulas")
        assert sem_aulas["percentual"] == 0
        assert sem_aulas["total_aulas"] == 0


class TestExclusao:
    """
    A tela da loja ganhou seleção múltipla e botão de excluir. O que a
    interface deixa marcar tem de bater com o que a API deixa apagar,
    senão o usuário marca cinco e recebe erro em dois.
    """

    def test_loja_apaga_o_proprio_curso(self, client, cab_loja, curso_da_loja, db):
        r = client.delete(f"/cursos/{curso_da_loja.id}", headers=cab_loja)
        assert r.status_code == 204
        assert db.query(Curso).filter(Curso.id == curso_da_loja.id).first() is None

    def test_apagar_o_curso_leva_as_aulas(self, client, cab_loja, curso_da_loja, db):
        client.delete(f"/cursos/{curso_da_loja.id}", headers=cab_loja)
        assert db.query(Aula).filter(Aula.curso_id == curso_da_loja.id).count() == 0

    def test_ninguem_apaga_curso_global(self, client, cab_loja, curso_global, db):
        # Conteúdo do AquaSys. Por isso a tela nem deixa marcar o card.
        assert client.delete(
            f"/cursos/{curso_global.id}", headers=cab_loja
        ).status_code in (403, 404)
        assert db.query(Curso).filter(Curso.id == curso_global.id).first() is not None

    def test_uma_loja_nao_apaga_o_curso_da_outra(
        self, client, cab_outra_loja, curso_da_loja, db
    ):
        assert client.delete(
            f"/cursos/{curso_da_loja.id}", headers=cab_outra_loja
        ).status_code == 404
        assert db.query(Curso).filter(Curso.id == curso_da_loja.id).first() is not None

    def test_apagar_varios_de_uma_vez(self, client, cab_loja, db, loja):
        # É o caminho da seleção múltipla: o app chama a rota uma vez por
        # curso marcado.
        ids = []
        for i in range(3):
            curso = Curso(dono_id=loja.id, titulo=f"Curso {i}", ativo=True)
            db.add(curso)
            db.flush()
            ids.append(curso.id)

        for curso_id in ids:
            assert client.delete(
                f"/cursos/{curso_id}", headers=cab_loja
            ).status_code == 204

        assert client.get("/cursos/", headers=cab_loja).json() == []
