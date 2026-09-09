from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    YOUTUBE_API_KEY: str | None = None

    # Aplicação
    APP_NAME: str = "AquaSys"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SQL_ECHO: bool = False

    class Config:
        env_file = ".env"


# Instância global
settings = Settings()