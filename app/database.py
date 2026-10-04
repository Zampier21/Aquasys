"""Conexão com o PostgreSQL.

As opções do pool abaixo existem por causa do banco gerenciado que o
AquaSys usa fora da máquina de desenvolvimento. Ele adormece sozinho
depois de alguns minutos sem consulta, e quem dorme derruba as conexões
que estavam abertas. Sem tratar isso, a primeira requisição depois de
um intervalo de silêncio recebe erro de conexão morta em vez de
resposta — e é justamente a primeira requisição do dia que alguém vê.

Num Postgres local nada disso atrapalha: `pool_pre_ping` custa um
`SELECT 1` por conexão retirada do pool, o que é barato até em rede
local.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

OPCOES_DO_POOL = {
    # Confere se a conexão ainda está viva antes de entregá-la. É o que
    # transforma "banco adormeceu" em uma reconexão silenciosa.
    "pool_pre_ping": True,
    # Descarta conexão parada há mais de quatro minutos. Fica abaixo do
    # tempo que o banco gerenciado leva para adormecer, então é o pool
    # que solta a conexão, e não o servidor que a corta.
    "pool_recycle": 240,
    # O plano gratuito tem poucas conexões simultâneas, e o serviço roda
    # em um processo só. Cinco mais cinco sobra para o uso previsto e
    # não chega perto do teto.
    "pool_size": 5,
    "max_overflow": 5,
    # Sem isto, uma requisição fica pendurada esperando vaga no pool
    # enquanto o usuário olha para a tela girando.
    "pool_timeout": 15,
}

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    **OPCOES_DO_POOL,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
