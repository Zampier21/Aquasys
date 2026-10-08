"""Configuração da aplicação, lida do ambiente.

O que muda entre a máquina de desenvolvimento e o servidor de produção
mora aqui, num lugar só. A regra é que o padrão seja o comportamento
seguro: quem esquecer de configurar alguma coisa recebe o modo fechado,
e não o aberto. Abrir exige ato deliberado no `.env`.
"""

import secrets
from typing import Annotated, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode

# Valores de exemplo que existem no .env.example e nos tutoriais. Se um
# deles chegar em produção, é porque ninguém trocou.
_CHAVES_DE_EXEMPLO = {
    "troque-por-uma-chave-aleatoria-longa",
    "secret",
    "secret-key",
    "changeme",
    "sua-chave-secreta",
    "super-secret-key",
}

TAMANHO_MINIMO_DA_CHAVE = 32


class Settings(BaseSettings):
    # ─── Banco de dados ───────────────────────────────
    DATABASE_URL: str

    # ─── JWT ──────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Quanto tempo o aparelho continua reconhecido sem pedir senha.
    # Trinta dias e o prazo tipico; alonga-lo nao enfraquece como
    # alongar o token de acesso, porque esta sessao e revogavel.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    YOUTUBE_API_KEY: Optional[str] = None

    # ─── Aplicação ────────────────────────────────────
    APP_NAME: str = "AquaSys"
    APP_VERSION: str = "1.0.0"

    # 'desenvolvimento' | 'producao' | 'teste'
    AMBIENTE: str = "desenvolvimento"

    # Nunca ligado por padrão: DEBUG faz o servidor devolver detalhe
    # interno em resposta de erro.
    DEBUG: bool = False
    SQL_ECHO: bool = False

    # ─── Fronteira HTTP ───────────────────────────────
    # Origens que podem chamar a API pelo navegador. Lista vazia em
    # produção significa "nenhuma origem de navegador", que é o certo
    # para uma API consumida só por aplicativo nativo.
    # `NoDecode` desliga o parser de JSON que o pydantic-settings
    # aplicaria à lista antes de o validador rodar. Sem isso, um
    # `CORS_ORIGENS=` vazio no .env estoura, porque string vazia não é
    # JSON válido, e a lista teria de ser escrita como ["a","b"].
    CORS_ORIGENS: Annotated[List[str], NoDecode] = []

    # A documentação interativa descreve todas as rotas e todos os
    # campos. Útil enquanto se desenvolve, mapa do tesouro em produção.
    DOCS_PUBLICOS: bool = False

    # Redireciona http para https e manda o cabeçalho HSTS.
    FORCAR_HTTPS: bool = False

    # Ligar apenas quando houver mesmo um proxy reverso na frente. Com
    # isto ligado sem proxy, qualquer um escolhe o próprio endereço de
    # origem pelo cabeçalho X-Forwarded-For e escapa do limitador.
    CONFIAR_NO_PROXY: bool = False

    # Teto do corpo da requisição, antes de qualquer leitura. O limite
    # de 512 KB do CSV é verificado depois de o arquivo já estar na
    # memória; este aqui é o que impede que ele chegue lá.
    TAMANHO_MAXIMO_CORPO: int = 2 * 1024 * 1024

    # ─── Limite de requisições ────────────────────────
    RATE_LIMIT_ATIVO: bool = True
    # Teto geral, por endereço, por minuto.
    RATE_LIMIT_POR_MINUTO: int = 120
    # Teto do login. Bem mais baixo: é a única rota em que um acerto
    # vale uma conta, e ninguém tenta entrar dez vezes por minuto sem
    # estar chutando senha.
    RATE_LIMIT_LOGIN: int = 8
    RATE_LIMIT_LOGIN_JANELA_SEGUNDOS: int = 300

    class Config:
        env_file = ".env"

    # ─── Validações ───────────────────────────────────
    @field_validator("CORS_ORIGENS", mode="before")
    @classmethod
    def _separar_origens(cls, valor):
        """Aceita a lista escrita no .env separada por vírgula."""
        if isinstance(valor, str):
            return [parte.strip() for parte in valor.split(",") if parte.strip()]
        return valor

    @field_validator("AMBIENTE")
    @classmethod
    def _ambiente_conhecido(cls, valor: str) -> str:
        valor = (valor or "").strip().lower()
        if valor not in {"desenvolvimento", "producao", "teste"}:
            raise ValueError(
                "AMBIENTE deve ser 'desenvolvimento', 'producao' ou 'teste'"
            )
        return valor

    @property
    def em_producao(self) -> bool:
        return self.AMBIENTE == "producao"

    def conferir_para_producao(self) -> List[str]:
        """Lista o que impede esta configuração de ir para produção.

        Devolver a lista, em vez de estourar, permite que a checagem
        seja usada tanto na subida do servidor quanto num teste que
        prova que a checagem funciona.
        """
        problemas: List[str] = []

        if self.SECRET_KEY.strip().lower() in _CHAVES_DE_EXEMPLO:
            problemas.append(
                "SECRET_KEY ainda é o valor de exemplo. Gere uma nova com: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        elif len(self.SECRET_KEY) < TAMANHO_MINIMO_DA_CHAVE:
            problemas.append(
                f"SECRET_KEY tem {len(self.SECRET_KEY)} caracteres; o mínimo "
                f"é {TAMANHO_MINIMO_DA_CHAVE}. Uma chave curta é forçável."
            )

        if self.DEBUG:
            problemas.append(
                "DEBUG está ligado: respostas de erro vazam detalhe interno."
            )

        if self.SQL_ECHO:
            problemas.append("SQL_ECHO está ligado: todo SQL vai para o log.")

        if "*" in self.CORS_ORIGENS:
            problemas.append(
                "CORS_ORIGENS contém '*', que permite qualquer site chamar "
                "a API com as credenciais do usuário."
            )

        if not self.FORCAR_HTTPS:
            problemas.append(
                "FORCAR_HTTPS está desligado: o token trafega em texto claro."
            )

        url = self.DATABASE_URL
        if "sslmode=" not in url and "localhost" not in url and "127.0.0.1" not in url:
            problemas.append(
                "DATABASE_URL não pede TLS. Acrescente ?sslmode=require "
                "quando o banco não estiver na mesma máquina."
            )

        return problemas


def gerar_chave() -> str:
    """Chave nova, no formato que o .env.example manda gerar."""
    return secrets.token_urlsafe(48)


# Instância global
settings = Settings()
