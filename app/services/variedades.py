"""
Variedades de uma mesma espécie, e como elas herdam a biologia da base.

Tetra Neon Negro e Tetra Neon Negro Albino são o mesmo peixe: mesma
água, mesmo porte, mesmo temperamento. Muda a aparência, e é ela que a
loja mostra na hora da venda. A variedade aponta para a espécie-base
por `variante_de_id` e o catálogo lista apenas as bases, cada uma
levando suas variedades dentro.

POR QUE A HERANÇA É MATERIALIZADA, E NÃO RESOLVIDA NA LEITURA
-------------------------------------------------------------
A primeira versão deste módulo devolvia um invólucro que lia a
variedade e caía na base no que estivesse nulo. Era mais elegante e
teria uma fonte de verdade só — mas exigia que TODO caminho até os
motores passasse pelo invólucro, e há vários: as três rotas de
compatibilidade, o `_habitantes` de peixes.py, o `aquario.habitantes`
lido por aquarios.py e por painel.py.

Esquecer um deles não daria erro. Daria resposta errada em silêncio,
porque `_faixa_dos_habitantes`, em parametros.py, descarta quem tem o
campo nulo:

    if getattr(e, campo_min, None) is not None

Uma variedade com `ph_min` nulo simplesmente sumiria da interseção, e o
aquário seria avaliado como se aquele peixe não estivesse lá. Um alerta
que não aparece é pior do que um alerta errado: ninguém percebe.

Por isso os valores herdados são gravados na linha da variedade. Ela
passa a ser, para todo o resto do sistema, uma espécie como qualquer
outra — nenhum motor precisa saber que variedades existem. O preço é a
duplicação dos campos, que se paga com `sincronizar` sempre que a base
muda.
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.especie import Especie

# O que pertence à variedade e nunca vem da base: é o que a distingue.
NAO_HERDA = frozenset({
    "id",
    "nome_comum",
    "variante_de_id",
    "ativo",
    "criado_em",
    "observacoes",
    "imagem_url",
})


def _campos_herdaveis() -> List[str]:
    """Colunas que uma variedade pode receber da base."""
    return [
        coluna.key
        for coluna in Especie.__table__.columns
        if coluna.key not in NAO_HERDA
    ]


def criar_variedade(base: Especie, nome_comum: str, **diferencas) -> Especie:
    """Monta uma variedade já com a biologia da base. É O caminho de criar.

    Todos os campos herdáveis são copiados da base NA CONSTRUÇÃO, antes
    de o objeto ir para o banco. A ordem importa, e custou um defeito:
    cinco colunas booleanas têm `default=False` no modelo. Se a variedade
    fosse gravada primeiro e sincronizada depois, o banco já as teria
    preenchido com False — e `sincronizar`, que só copia o que é nulo,
    não as tocaria. Um Betta Halfmoon nasceria com
    `agressivo_coespecificos=False`, e o motor liberaria dois machos no
    mesmo aquário.

    `diferencas` é o que a variedade declara de próprio — um Plakat com
    `barbatana_longa=False`, um albino com `ph_max` mais baixo — e
    prevalece sobre a base.
    """
    valores = {campo: getattr(base, campo) for campo in _campos_herdaveis()}
    valores.update(diferencas)
    return Especie(
        nome_comum=nome_comum,
        variante_de_id=base.id,
        ativo=True,
        **valores,
    )


def sincronizar(variedade: Especie, base: Especie) -> List[str]:
    """Copia da base o que a variedade deixou em branco.

    Só preenche o que está nulo: uma variedade que declara o próprio
    valor — um albino mais sensível, com faixa de pH mais estreita —
    mantém o que declarou.

    Devolve os campos que foram preenchidos, para quem quiser registrar.
    """
    preenchidos = []
    for campo in _campos_herdaveis():
        if getattr(variedade, campo, None) is None:
            valor = getattr(base, campo, None)
            if valor is not None:
                setattr(variedade, campo, valor)
                preenchidos.append(campo)
    return preenchidos


def propagar(base: Especie, db: Session) -> int:
    """Repassa às variedades a mudança feita na base.

    Não sobrescreve o que a variedade tem preenchido, porque não há como
    distinguir um valor herdado de um valor escolhido. Serve para
    completar variedades novas e para campos que a base ganhou depois.
    """
    tocadas = 0
    for variedade in base.variantes:
        if sincronizar(variedade, base):
            tocadas += 1
    if tocadas:
        db.flush()
    return tocadas


def e_variedade(especie: Especie) -> bool:
    return getattr(especie, "variante_de_id", None) is not None


def nome_curto_de(nome: str, nome_base: str) -> str:
    """O mesmo corte de `nome_curto`, a partir de duas cadeias."""
    nome = nome or ""
    if nome_base and nome.lower().startswith(nome_base.lower()):
        curto = nome[len(nome_base):].strip(" -–—")
        if curto:
            return curto
    return nome


def nome_curto(especie: Especie, base: Especie = None) -> str:
    """Nome da variedade sem repetir o da base.

    Dentro de um card que já se chama "Acará Bandeira", a variedade
    "Acará Bandeira Leopardo Azul" aparece como "Leopardo Azul".
    """
    base = base or getattr(especie, "base", None)
    if base is None:
        return especie.nome_comum or ""
    return nome_curto_de(especie.nome_comum, base.nome_comum)
