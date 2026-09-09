from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # YouTube — opcional, usado só pelo seed de cursos no servidor.
    # Sem ela o import de playlist cai no feed RSS público, que entrega
    # no máximo 15 vídeos. O app nunca usa esta chave.
    YOUTUBE_API_KEY: str | None = None

    # Aplicação
    APP_NAME: str = "AquaSys"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Despeja todo SQL no console. Fica separado do DEBUG de propósito:
    # ligado junto, ele enterra a saída dos seeds e ainda quebra no
    # console do Windows ao imprimir acento ou emoji vindo do banco.
    SQL_ECHO: bool = False

    class Config:
        env_file = ".env"


# Instância global
settings = Settings()