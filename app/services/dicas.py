"""
Dicas da Home montadas a partir do aquário de quem está olhando.

A tabela `dica` guarda conselho curado — geral ("troque 20% da água por
semana") ou preso a uma espécie. Isso é bom, mas é sempre o mesmo texto
para todo mundo, e o cliente logo para de ler.

Aqui nascem as dicas de SITUAÇÃO: elas leem o estado atual dos aquários
da conta e falam do que está acontecendo agora — o pH que não serve aos
peixes de lá, o cardume incompleto, o aquário ainda vazio. Vêm primeiro
na Home justamente porque são as únicas escritas para aquele aquário.
"""

from typing import Dict, List, Tuple

from app.services import parametros as svc_parametros


def _sem_aquario() -> List[dict]:
    return [{
        "categoria": "equipamento",
        "conteudo": (
            "Cadastre seu primeiro aquário para o AquaSys acompanhar os "
            "parâmetros e avisar quando algo sair do lugar."
        ),
    }]


def _dicas_de_parametro(aquario, medicao, habitantes) -> List[dict]:
    """
    Um conselho por parâmetro fora da faixa, com o motivo já explicado.

    Reaproveita o mesmo motor que gera os alertas — se um dia a regra
    mudar, a dica muda junto e as duas telas continuam concordando.
    """
    problemas, _ = svc_parametros.avaliar(aquario, medicao, habitantes)

    return [
        {
            "categoria": "quimica",
            "conteudo": f'No aquário "{aquario.nome}": {p["motivo"]}',
        }
        for p in problemas
    ]


def _dicas_de_cardume(aquario, povoamento) -> List[dict]:
    """Espécie de cardume com menos peixes do que o mínimo que ela pede."""
    conselhos = []

    for especie, quantidade in povoamento:
        minimo = especie.cardume_minimo
        if especie.agrupamento != "cardume" or not minimo:
            continue
        if quantidade >= minimo:
            continue

        faltam = minimo - quantidade
        plural = "peixe" if faltam == 1 else "peixes"
        conselhos.append({
            "categoria": "comportamento",
            "conteudo": (
                f'Você tem {quantidade} {especie.nome_comum} em "{aquario.nome}", '
                f"mas eles só se sentem seguros em grupo de {minimo}. "
                f"Faltam {faltam} {plural}."
            ),
        })

    return conselhos


def _aquario_vazio(aquario) -> dict:
    return {
        "categoria": "comportamento",
        "conteudo": (
            f'"{aquario.nome}" ainda está sem peixes. Na aba Peixes o app '
            f"mostra quais espécies combinam com a água dele."
        ),
    }


def situacionais(
    aquarios: List,
    povoamento: Dict[object, List[Tuple]],
) -> List[dict]:
    """
    Dicas tiradas do estado atual dos aquários da conta.

    `povoamento` mapeia id do aquário → lista de (Especie, quantidade).
    A ordem da saída é a ordem de urgência: parâmetro errado primeiro,
    depois convívio, e por último o aquário que nem começou.
    """
    if not aquarios:
        return _sem_aquario()

    de_parametro: List[dict] = []
    de_cardume: List[dict] = []
    vazios: List[dict] = []

    for aquario in aquarios:
        moradores = povoamento.get(aquario.id, [])
        habitantes = [especie for especie, _ in moradores]
        medicao = aquario.parametros[0] if aquario.parametros else None

        de_parametro += _dicas_de_parametro(aquario, medicao, habitantes)
        de_cardume += _dicas_de_cardume(aquario, moradores)

        if not moradores:
            vazios.append(_aquario_vazio(aquario))

    return de_parametro + de_cardume + vazios
