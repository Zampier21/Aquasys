"""Camadas de proteção que valem para toda requisição, antes das rotas.

São três, e cada uma resolve um problema que nenhuma rota resolveria
sozinha: o tamanho do corpo, os cabeçalhos de segurança da resposta e a
exigência de HTTPS.
"""

from typing import Iterable

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# ═══════════════════════════════════════════════════════
# TAMANHO DO CORPO
# ═══════════════════════════════════════════════════════
class LimiteDeCorpo:
    """Recusa corpo acima do teto sem terminar de lê-lo.

    A rota de importação já recusa CSV acima de 512 KB, mas só depois de
    `await request.body()`, ou seja, com o arquivo inteiro na memória.
    Um POST de um gigabyte derrubaria o servidor antes de a verificação
    rodar. Este middleware é ASGI puro de propósito: só assim dá para
    interromper a leitura no meio, o que o middleware de alto nível do
    Starlette não permite.
    """

    def __init__(self, app: ASGIApp, maximo: int) -> None:
        self.app = app
        self.maximo = maximo

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cabecalhos = Headers(scope=scope)
        declarado = cabecalhos.get("content-length")
        if declarado is not None:
            try:
                if int(declarado) > self.maximo:
                    await self._recusar(scope, receive, send)
                    return
            except ValueError:
                # Content-Length que não é número é requisição malformada;
                # deixa o Starlette decidir o que fazer com ela.
                pass

        lidos = 0
        estourou = False

        async def receber() -> Message:
            nonlocal lidos, estourou
            mensagem = await receive()
            if mensagem["type"] == "http.request":
                lidos += len(mensagem.get("body", b""))
                if lidos > self.maximo:
                    estourou = True
                    # Encerra o corpo em vez de seguir acumulando: a rota
                    # recebe o que veio até aqui e a resposta de erro já
                    # está a caminho.
                    return {"type": "http.disconnect"}
            return mensagem

        await self.app(scope, receber, send)
        if estourou:
            return

    async def _recusar(self, scope: Scope, receive: Receive, send: Send) -> None:
        limite = self.maximo // 1024
        resposta = JSONResponse(
            status_code=413,
            content={"detail": f"Envio muito grande. O limite é {limite} KB."},
        )
        await resposta(scope, receive, send)


# ═══════════════════════════════════════════════════════
# CABEÇALHOS DE SEGURANÇA
# ═══════════════════════════════════════════════════════
# Uma API que só devolve JSON não precisa executar nada, não precisa ser
# embutida em moldura e não precisa que o navegador adivinhe o tipo do
# conteúdo. A política abaixo diz exatamente isso.
_CSP_DA_API = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
    "form-action 'none'"
)

# O Swagger carrega script e folha de estilo de CDN, e desenha com
# imagem embutida. Sem esta exceção, ligar DOCS_PUBLICOS entregaria uma
# página em branco.
_CSP_DOS_DOCS = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; base-uri 'none'"
)

_CAMINHOS_DE_DOC = ("/docs", "/redoc", "/openapi.json")

_FIXOS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # A API não usa nenhum sensor do aparelho; desligar tudo é o padrão
    # correto e custa nada.
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), "
                          "payment=(), usb=()",
    # Sem isto, uma resposta autenticada pode ficar num cache
    # intermediário e ser servida a outra pessoa.
    "Cache-Control": "no-store",
}


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, hsts: bool = False) -> None:
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request, call_next):
        resposta = await call_next(request)

        for nome, valor in _FIXOS.items():
            resposta.headers.setdefault(nome, valor)

        eh_doc = request.url.path.startswith(_CAMINHOS_DE_DOC)
        resposta.headers.setdefault(
            "Content-Security-Policy", _CSP_DOS_DOCS if eh_doc else _CSP_DA_API
        )

        if self.hsts:
            # Um ano, subdomínios incluídos. Sem `preload`: entrar na
            # lista do navegador é decisão que não se desfaz rápido.
            resposta.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return resposta


# ═══════════════════════════════════════════════════════
# HTTPS OBRIGATÓRIO
# ═══════════════════════════════════════════════════════
class ExigirHTTPS(BaseHTTPMiddleware):
    """Manda o navegador de volta pelo https e recusa o resto em claro.

    O redirecionamento só serve para GET e HEAD. Num POST, redirecionar
    faria o cliente reenviar o corpo, e o primeiro envio (com o token no
    cabeçalho) já teria viajado em texto claro de qualquer jeito. Aí o
    certo é recusar.

    Atrás de um proxy que termina o TLS, quem sabe o protocolo original
    é o cabeçalho `X-Forwarded-Proto`. Confiar nele exige que o proxy o
    reescreva sempre, o que é a configuração padrão do Nginx, do Caddy e
    dos balanceadores de nuvem.
    """

    LIVRES: Iterable[str] = ("/health",)

    async def dispatch(self, request, call_next):
        if self._seguro(request) or request.url.path in self.LIVRES:
            return await call_next(request)

        if request.method in ("GET", "HEAD"):
            return RedirectResponse(
                str(request.url.replace(scheme="https")), status_code=307
            )

        return JSONResponse(
            status_code=400,
            content={"detail": "Esta API só aceita conexões https."},
        )

    @staticmethod
    def _seguro(request) -> bool:
        encaminhado = request.headers.get("x-forwarded-proto")
        if encaminhado:
            # Pode vir encadeado: "https, http".
            return encaminhado.split(",")[0].strip().lower() == "https"
        return request.url.scheme == "https"
