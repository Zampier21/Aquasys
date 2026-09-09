"""
Preparação comum dos testes da API.

Os testes rodam contra um banco PostgreSQL **separado**, criado do zero a
cada execução e derrubado no fim: o banco de desenvolvimento nunca é
tocado. O nome sai de `DATABASE_URL` com o sufixo `_test`.

Cada teste roda numa transação própria, desfeita ao final, então um teste
nunca enxerga o que o outro gravou.
"""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_senha
from app.database import Base, get_db
# Importado com outro nome: `import app.models` abaixo reatribuiria
# `app` para o pacote e esconderia a instância do FastAPI.
from app.main import app as api
from app.models.usuario import Usuario

import app.models  # noqa: F401,E402  — registra todos os modelos no metadata


def _url_de_teste() -> tuple[str, str, str]:
    """Devolve (url do banco de teste, url do 'postgres', nome do banco)."""
    url = settings.DATABASE_URL
    base, nome = url.rsplit("/", 1)
    nome_teste = f"{nome}_test"
    return f"{base}/{nome_teste}", f"{base}/postgres", nome_teste


URL_TESTE, URL_ADMIN, NOME_TESTE = _url_de_teste()


@pytest.fixture(scope="session")
def engine():
    """Cria o banco de teste, monta o esquema e derruba tudo no fim."""
    admin = create_engine(URL_ADMIN, isolation_level="AUTOCOMMIT")
    with admin.connect() as con:
        con.execute(text(f'DROP DATABASE IF EXISTS "{NOME_TESTE}"'))
        con.execute(text(f'CREATE DATABASE "{NOME_TESTE}"'))

    motor = create_engine(URL_TESTE)
    Base.metadata.create_all(bind=motor)

    yield motor

    motor.dispose()
    with admin.connect() as con:
        con.execute(text(f'DROP DATABASE IF EXISTS "{NOME_TESTE}"'))
    admin.dispose()


@pytest.fixture
def db(engine):
    """
    Sessão dentro de uma transação que é sempre desfeita.

    É o que garante isolamento entre testes sem recriar o banco a cada um.
    """
    conexao = engine.connect()
    transacao = conexao.begin()
    Sessao = sessionmaker(bind=conexao, autocommit=False, autoflush=False)
    sessao = Sessao()

    yield sessao

    sessao.close()
    transacao.rollback()
    conexao.close()


@pytest.fixture
def client(db):
    """TestClient com o banco de teste no lugar do banco real."""
    api.dependency_overrides[get_db] = lambda: db
    with TestClient(api) as c:
        yield c
    api.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════
# USUÁRIOS DE APOIO
# ═══════════════════════════════════════════════════════
SENHA = "senha123"


def _criar_usuario(db, nome, documento, tipo, dono=None) -> Usuario:
    usuario = Usuario(
        nome=nome,
        cpf_cnpj=documento,
        senha_hash=hash_senha(SENHA),
        tipo=tipo,
        dono_id=dono.id if dono else None,
        ativo=True,
    )
    db.add(usuario)
    db.flush()
    return usuario


@pytest.fixture
def loja(db) -> Usuario:
    return _criar_usuario(db, "Loja A", "11.222.333/0001-81", "dono")


@pytest.fixture
def outra_loja(db) -> Usuario:
    """Segunda loja — usada para provar que uma não enxerga a outra."""
    return _criar_usuario(db, "Loja B", "11.444.777/0001-61", "dono")


@pytest.fixture
def cliente(db, loja) -> Usuario:
    return _criar_usuario(db, "Cliente da A", "123.456.789-09", "cliente", loja)


def _token(client, documento) -> str:
    resposta = client.post(
        "/auth/login", json={"cpf_cnpj": documento, "senha": SENHA}
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["access_token"]


@pytest.fixture
def cab_loja(client, loja) -> dict:
    return {"Authorization": f"Bearer {_token(client, loja.cpf_cnpj)}"}


@pytest.fixture
def cab_outra_loja(client, outra_loja) -> dict:
    return {"Authorization": f"Bearer {_token(client, outra_loja.cpf_cnpj)}"}


@pytest.fixture
def cab_cliente(client, cliente) -> dict:
    return {"Authorization": f"Bearer {_token(client, cliente.cpf_cnpj)}"}
