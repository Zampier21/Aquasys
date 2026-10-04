import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.limitador import LimitadorGeral
from app.core.seguranca_http import (
    CabecalhosDeSeguranca, ExigirHTTPS, LimiteDeCorpo,
)
from app.routers import (
    auth, aquarios, peixes, clientes, fichas, cursos, painel, perfil,
)

log = logging.getLogger("aquasys")

# Qualquer porta, mas só na própria máquina.
_LOCALHOST = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

# ─── A configuração precisa estar sã antes de subir ───
# Em produção, subir com a chave de exemplo ou com DEBUG ligado é pior
# do que não subir: o servidor fica de pé parecendo saudável enquanto
# está aberto. Falhar aqui é barulhento na hora certa.
if settings.em_producao:
    problemas = settings.conferir_para_producao()
    if problemas:
        raise RuntimeError(
            "Configuração insegura para produção:\n  - "
            + "\n  - ".join(problemas)
        )

# ─── Criação da aplicação ─────────────────────────────
# A documentação interativa lista todas as rotas, todos os campos e
# todos os formatos aceitos. É andaime de desenvolvimento, e fica
# desligada por padrão.
_docs = settings.DOCS_PUBLICOS

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API do sistema AquaSys: gerenciamento de aquários e "
                "serviços de manutenção",
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)

# ─── Camadas de proteção ──────────────────────────────
# O Starlette executa na ordem inversa da inclusão: o último incluído é
# o mais externo. A ordem desejada, de fora para dentro, é cabeçalhos,
# CORS, HTTPS, tamanho do corpo e limite de requisições — assim toda
# resposta sai com os cabeçalhos, inclusive as recusas.
app.add_middleware(LimitadorGeral)
app.add_middleware(LimiteDeCorpo, maximo=settings.TAMANHO_MAXIMO_CORPO)

if settings.FORCAR_HTTPS:
    app.add_middleware(ExigirHTTPS)

# CORS só existe para navegador: o aplicativo nativo não passa por
# isso. O que havia aqui era allow_origins=['*'] com allow_credentials
# ligado, que é a combinação que permite a qualquer site na internet
# chamar a API em nome de quem estiver logado.
#
# `allow_credentials` fica desligado porque o AquaSys não usa cookie
# nenhum: o token viaja no cabeçalho Authorization, que o CORS libera
# pela lista de allow_headers, sem precisar do modo com credenciais.
#
# Em desenvolvimento a origem liberada é localhost em qualquer porta —
# o `flutter run -d chrome` sorteia uma porta nova a cada execução, e
# uma lista fixa obrigaria a editar o .env toda vez. A expressão aceita
# só a máquina local, e nada mais.
_origens = settings.CORS_ORIGENS
_regex_origens = None if settings.em_producao else _LOCALHOST

if _origens or _regex_origens:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origens,
        allow_origin_regex=_regex_origens,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

app.add_middleware(CabecalhosDeSeguranca, hsts=settings.FORCAR_HTTPS)


# ─── Erro não previsto não vira relatório ─────────────
@app.exception_handler(Exception)
async def erro_inesperado(request: Request, erro: Exception):
    """Responde sempre a mesma frase, e guarda o detalhe no log.

    Traço de pilha em resposta de erro conta a estrutura de pastas, as
    bibliotecas instaladas e, às vezes, trechos de consulta com dado de
    usuário dentro. Quem precisa disso é quem mantém o servidor, e esse
    lê o log.
    """
    log.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno. Tente novamente em instantes."},
    )


# ─── Registro dos routers ─────────────────────────────
app.include_router(auth.router,      prefix="/auth",      tags=["Autenticação"])
app.include_router(perfil.router,    prefix="/perfil",    tags=["Perfil"])
app.include_router(painel.router,    prefix="/painel",    tags=["Painel"])
app.include_router(aquarios.router,  prefix="/aquarios",  tags=["Aquários"])
app.include_router(peixes.router,    prefix="/peixes",    tags=["Peixes"])
app.include_router(clientes.router,  prefix="/clientes",  tags=["Clientes"])
app.include_router(fichas.router,    prefix="/fichas",    tags=["Fichas de Manutenção"])
app.include_router(cursos.router,    prefix="/cursos",    tags=["Cursos"])


# ─── Rota raiz ────────────────────────────────────────
@app.get("/", tags=["Status"])
def root():
    """Prova de vida, e nada além disso.

    Anunciar nome, versão e caminho da documentação numa rota aberta é
    entregar de graça metade do trabalho de quem procura uma versão com
    falha conhecida.
    """
    return {"status": "online"}


@app.get("/health", tags=["Status"])
def health():
    return {"status": "ok"}
