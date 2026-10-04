"""Teto de requisições por origem, em janela deslizante.

Sem isto, a rota de login aceita quantas tentativas o atacante quiser.
Uma senha de seis dígitos, que é o mínimo que o cadastro permite, cai
em minutos numa máquina comum. O teto não impede o ataque; obriga quem
o faz a levar meses, o que é o suficiente.

A contagem mora na memória do processo. É a escolha certa para o
tamanho de hoje, com um único servidor, e é preciso dizer a limitação
em voz alta: com vários trabalhadores do uvicorn, cada um conta o seu,
e o teto real vira o teto multiplicado pelo número de processos. No dia
em que o AquaSys rodar em mais de uma máquina, isto tem de virar uma
contagem no Redis, e o resto do arquivo não muda.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


class JanelaDeslizante:
    """Conta eventos por chave dentro de uma janela de tempo."""

    def __init__(self) -> None:
        self._marcas: Dict[str, Deque[float]] = defaultdict(deque)
        self._trava = threading.Lock()

    def registrar(self, chave: str, teto: int, janela: float) -> Tuple[bool, float]:
        """Anota uma tentativa.

        Devolve (permitido, segundos até liberar). Quando permitido, o
        segundo valor é zero.
        """
        agora = time.monotonic()
        limite_inferior = agora - janela

        with self._trava:
            marcas = self._marcas[chave]
            while marcas and marcas[0] <= limite_inferior:
                marcas.popleft()

            if len(marcas) >= teto:
                # A mais antiga é a que vai liberar a próxima vaga.
                return False, max(0.0, marcas[0] + janela - agora)

            marcas.append(agora)
            return True, 0.0

    def esquecer(self, chave: str) -> None:
        """Zera a contagem de uma chave. É o que o login bem-sucedido faz."""
        with self._trava:
            self._marcas.pop(chave, None)

    def limpar(self) -> None:
        with self._trava:
            self._marcas.clear()

    def faxinar(self, janela: float) -> None:
        """Descarta chaves cuja janela inteira já passou.

        Sem isto o dicionário cresce para sempre, um endereço por
        visitante que nunca mais voltou.
        """
        limite = time.monotonic() - janela
        with self._trava:
            mortas = [c for c, m in self._marcas.items() if not m or m[-1] <= limite]
            for chave in mortas:
                del self._marcas[chave]


# Uma janela para o teto geral e outra para o login: as durações são
# diferentes, e misturá-las numa só daria conta errada.
geral = JanelaDeslizante()
login = JanelaDeslizante()


def zerar_tudo() -> None:
    """Usado pelos testes entre um caso e outro."""
    geral.limpar()
    login.limpar()


# ═══════════════════════════════════════════════════════
# DE ONDE VEIO A REQUISIÇÃO
# ═══════════════════════════════════════════════════════
def endereco(request) -> str:
    """Endereço de origem, respeitando o proxy só quando configurado.

    Confiar em `X-Forwarded-For` sem proxy na frente anula o limitador:
    o próprio atacante escolhe o cabeçalho e ganha uma identidade nova
    a cada tentativa. Por isso o padrão é ignorá-lo.
    """
    if settings.CONFIAR_NO_PROXY:
        encaminhado = request.headers.get("x-forwarded-for")
        if encaminhado:
            # O primeiro da lista é o cliente; os seguintes são proxies.
            return encaminhado.split(",")[0].strip()

    return request.client.host if request.client else "desconhecido"


# ═══════════════════════════════════════════════════════
# TETO GERAL
# ═══════════════════════════════════════════════════════
class LimitadorGeral(BaseHTTPMiddleware):
    """Teto por endereço para toda a API.

    Não é proteção contra negação de serviço distribuída, que se resolve
    antes de chegar aqui. Serve para o caso comum: um aplicativo com
    laço errado, ou um raspador de dados percorrendo o catálogo.
    """

    JANELA = 60.0
    # A cada tantas requisições, joga fora as chaves que já venceram.
    # Barato, e evita que o dicionário guarde um endereço por visitante
    # que passou uma vez e nunca mais voltou.
    FAXINA_A_CADA = 500

    def __init__(self, app) -> None:
        super().__init__(app)
        self._desde_a_faxina = 0

    async def dispatch(self, request, call_next):
        if not settings.RATE_LIMIT_ATIVO:
            return await call_next(request)

        self._desde_a_faxina += 1
        if self._desde_a_faxina >= self.FAXINA_A_CADA:
            self._desde_a_faxina = 0
            geral.faxinar(self.JANELA)
            login.faxinar(float(settings.RATE_LIMIT_LOGIN_JANELA_SEGUNDOS))

        chave = endereco(request)
        permitido, espera = geral.registrar(
            chave, settings.RATE_LIMIT_POR_MINUTO, self.JANELA
        )

        if not permitido:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Muitas requisições. Aguarde um instante e "
                              "tente de novo."
                },
                headers={"Retry-After": str(int(espera) + 1)},
            )

        return await call_next(request)


# ═══════════════════════════════════════════════════════
# TETO DO LOGIN
# ═══════════════════════════════════════════════════════
def conferir_login(request, documento: Optional[str]) -> None:
    """Barra a enxurrada de tentativas de senha.

    Conta por endereço e também por documento. São dois ataques
    diferentes: um endereço chutando muitas contas, e muitos endereços
    chutando a mesma. Contar só o endereço deixaria o segundo passar.
    """
    if not settings.RATE_LIMIT_ATIVO:
        return

    teto = settings.RATE_LIMIT_LOGIN
    janela = float(settings.RATE_LIMIT_LOGIN_JANELA_SEGUNDOS)

    chaves = [f"ip:{endereco(request)}"]
    if documento:
        chaves.append(f"doc:{documento}")

    for chave in chaves:
        permitido, espera = login.registrar(chave, teto, janela)
        if not permitido:
            minutos = max(1, int(espera) // 60 + 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Muitas tentativas de entrada. Aguarde {minutos} "
                    f"minuto(s) antes de tentar de novo."
                ),
                headers={"Retry-After": str(int(espera) + 1)},
            )


def perdoar_login(request, documento: Optional[str]) -> None:
    """Zera a contagem depois que a senha foi aceita.

    Quem acertou não é o atacante. Sem isto, uma loja que erra a senha
    algumas vezes pela manhã ficaria com o saldo gasto até a janela
    fechar, mesmo já tendo entrado.
    """
    if not settings.RATE_LIMIT_ATIVO:
        return

    login.esquecer(f"ip:{endereco(request)}")
    if documento:
        login.esquecer(f"doc:{documento}")
