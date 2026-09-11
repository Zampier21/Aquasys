"""
Planos de assinatura e o teto de acessos que cada um concede.

A loja assinante cria os acessos dos próprios clientes. Sem teto, uma
assinatura só bastaria para atender uma rede inteira — e o modelo B2B2C
deixaria de se sustentar. O limite é, portanto, regra de negócio, e não
detalhe de interface: mora no servidor, junto com as demais.

Os números abaixo são a régua comercial do produto. São o único lugar
onde ela existe: mudá-la aqui muda o comportamento de todas as lojas do
mesmo plano, sem migração e sem publicar versão nova do aplicativo.

Uma vaga é ocupada por acesso ATIVO. Desativar um cliente devolve a
vaga; reativá-lo volta a consumi-la, e por isso a reativação passa pela
mesma verificação da criação.
"""

from typing import Dict, Optional

# ─── A régua ──────────────────────────────────────────
# `None` significa sem teto.
LIMITE_DE_ACESSOS: Dict[str, Optional[int]] = {
    "basico": 15,
    "profissional": 60,
    "ilimitado": None,
}

PLANO_PADRAO = "basico"

# Nome que o aplicativo mostra ao usuário.
ROTULO: Dict[str, str] = {
    "basico": "Básico",
    "profissional": "Profissional",
    "ilimitado": "Ilimitado",
}

PLANOS = tuple(LIMITE_DE_ACESSOS)


def limite(plano: Optional[str]) -> Optional[int]:
    """Teto de acessos do plano, ou None se não houver teto.

    Plano desconhecido ou ausente cai no padrão em vez de estourar: uma
    conta gravada antes desta regra existir continua funcionando, com o
    teto mais conservador.
    """
    if plano not in LIMITE_DE_ACESSOS:
        plano = PLANO_PADRAO
    return LIMITE_DE_ACESSOS[plano]


def rotulo(plano: Optional[str]) -> str:
    return ROTULO.get(plano or PLANO_PADRAO, ROTULO[PLANO_PADRAO])


def cabe_mais_um(plano: Optional[str], ativos: int) -> bool:
    """Se ainda há vaga para mais um acesso ativo."""
    teto = limite(plano)
    return teto is None or ativos < teto


def restantes(plano: Optional[str], ativos: int) -> Optional[int]:
    """Vagas livres, ou None quando o plano não tem teto."""
    teto = limite(plano)
    if teto is None:
        return None
    return max(0, teto - ativos)
