from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Nivel(str, Enum):
    OTIMO = "otimo"
    OK = "ok"
    RUIM = "ruim"
    FATAL = "fatal"

    @property
    def peso(self) -> int:
        return {"otimo": 0, "ok": 1, "ruim": 2, "fatal": 3}[self.value]


@dataclass
class Achado:
    """Um problema (ou confirmação) encontrado pela análise."""
    nivel: Nivel
    motivo: str
    mensagem: str


@dataclass
class Resultado:
    nivel: Nivel = Nivel.OTIMO
    achados: List[Achado] = field(default_factory=list)

    def adicionar(self, nivel: Nivel, motivo: str, mensagem: str) -> None:
        self.achados.append(Achado(nivel, motivo, mensagem))
        if nivel.peso > self.nivel.peso:
            self.nivel = nivel

    @property
    def mensagens(self) -> List[str]:
        return [a.mensagem for a in self.achados]

FATOR_PREDACAO = 3.0

# Sobreposição de faixa considerada apertada demais para ser confortável
MARGEM_ESTREITA_TEMP = 2.0   # °C
MARGEM_ESTREITA_PH = 0.4     # unidades de pH

ALIMENTACAO_PREDADORA = {"carnivoro", "onivoro"}

# ─── Classificação dos motivos ─────────────────────────────
# Impeditivos: o aquarista NÃO tem como corrigir. Bloqueiam a adição.
MOTIVOS_IMPEDITIVOS = {"ambiente", "predacao", "agressao", "lotacao"}

# Corrigíveis: geram alerta, mas permitem seguir com confirmação explícita.
MOTIVOS_CORRIGIVEIS = {
    "parametros", "comportamento", "territorio", "barbatana",
    # Ficha que ninguém conferiu. Não impede, mas nunca sai "liberado":
    # o que falta é justamente porte e temperamento, que são o que o
    # motor usa para decidir. Melhor avisar do que afirmar.
    "ficha_incompleta",
}


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "?"
    return str(int(v)) if float(v) == int(v) else str(v)


def _sobreposicao(a_min, a_max, b_min, b_max):
    """Interseção entre duas faixas. Devolve (inicio, fim) ou None."""
    if None in (a_min, a_max, b_min, b_max):
        return None
    inicio, fim = max(a_min, b_min), min(a_max, b_max)
    return (inicio, fim) if inicio <= fim else None


# ═══════════════════════════════════════════════════════════
# ESPÉCIE × AQUÁRIO
# ═══════════════════════════════════════════════════════════
def avaliar_especie_no_aquario(especie, aquario) -> Resultado:
    """A espécie sobrevive nas condições atuais deste aquário?"""
    r = Resultado()

    temp = getattr(aquario, "temperatura", None)
    ph = getattr(aquario, "ph", None)
    volume = getattr(aquario, "volume_litros", None)
    tipo_aquario = getattr(aquario, "tipo", None)

    # Tipo de água — filtro eliminatório
    if especie.tipo_agua and tipo_aquario:
        aquario_marinho = tipo_aquario == "marinho"
        especie_marinha = especie.tipo_agua == "marinho"
        if aquario_marinho != especie_marinha:
            r.adicionar(
                Nivel.FATAL, "ambiente",
                f"Espécie de água {especie.tipo_agua} — incompatível com este aquário",
            )

    # Temperatura — corrigível com termostato
    if temp is not None and especie.temp_min is not None:
        if temp < especie.temp_min:
            r.adicionar(
                Nivel.RUIM, "parametros",
                f"Temperatura baixa: precisa de "
                f"{_fmt(especie.temp_min)}–{_fmt(especie.temp_max)} °C",
            )
        elif especie.temp_max is not None and temp > especie.temp_max:
            r.adicionar(
                Nivel.RUIM, "parametros",
                f"Temperatura alta: precisa de "
                f"{_fmt(especie.temp_min)}–{_fmt(especie.temp_max)} °C",
            )

    # pH — corrigível gradualmente
    if ph is not None and especie.ph_min is not None:
        if ph < especie.ph_min:
            r.adicionar(
                Nivel.RUIM, "parametros",
                f"Requer pH acima de {_fmt(especie.ph_min)} — o aquário está em {_fmt(ph)}",
            )
        elif especie.ph_max is not None and ph > especie.ph_max:
            r.adicionar(
                Nivel.RUIM, "parametros",
                f"Requer pH abaixo de {_fmt(especie.ph_max)} — o aquário está em {_fmt(ph)}",
            )

    # Volume — limite físico, não há como contornar
    if volume is not None and especie.volume_minimo_l:
        if volume < especie.volume_minimo_l:
            r.adicionar(
                Nivel.FATAL, "ambiente",
                f"Volume insuficiente: a espécie exige no mínimo "
                f"{especie.volume_minimo_l}L e o aquário tem {_fmt(volume)}L",
            )

    # Aquário plantado
    if especie.come_plantas and tipo_aquario == "plantado":
        r.adicionar(
            Nivel.RUIM, "comportamento",
            "Danifica plantas — não indicada para aquário plantado",
        )

    return r


# ═══════════════════════════════════════════════════════════
# ESPÉCIE × ESPÉCIE
# ═══════════════════════════════════════════════════════════
def avaliar_par(a, b, excecao: Optional[dict] = None) -> Resultado:
    if excecao:
        r = Resultado()
        r.adicionar(
            Nivel(excecao["nivel"]),
            excecao.get("motivo") or "outro",
            excecao.get("observacao") or "Combinação não recomendada",
        )
        return r

    r = Resultado()

    # ─── 1. Tipo de água ───────────────────────────────────
    if a.tipo_agua and b.tipo_agua and a.tipo_agua != b.tipo_agua:
        r.adicionar(
            Nivel.FATAL, "ambiente",
            f"{a.nome_comum} é de água {a.tipo_agua} e "
            f"{b.nome_comum} de água {b.tipo_agua}",
        )
        return r  # nem faz sentido avaliar o resto

    # ─── 2. Temperatura ────────────────────────────────────
    faixa = _sobreposicao(a.temp_min, a.temp_max, b.temp_min, b.temp_max)
    if faixa is None and None not in (a.temp_min, b.temp_min):
        r.adicionar(
            Nivel.FATAL, "ambiente",
            f"Faixas de temperatura não se sobrepõem: "
            f"{_fmt(a.temp_min)}–{_fmt(a.temp_max)} °C contra "
            f"{_fmt(b.temp_min)}–{_fmt(b.temp_max)} °C",
        )
    elif faixa and (faixa[1] - faixa[0]) < MARGEM_ESTREITA_TEMP:
        r.adicionar(
            Nivel.RUIM, "parametros",
            f"Sobreposição estreita de temperatura: só "
            f"{_fmt(faixa[0])}–{_fmt(faixa[1])} °C atende às duas espécies",
        )

    # ─── 3. pH ─────────────────────────────────────────────
    faixa = _sobreposicao(a.ph_min, a.ph_max, b.ph_min, b.ph_max)
    if faixa is None and None not in (a.ph_min, b.ph_min):
        r.adicionar(
            Nivel.FATAL, "ambiente",
            f"Faixas de pH não se sobrepõem: "
            f"{_fmt(a.ph_min)}–{_fmt(a.ph_max)} contra "
            f"{_fmt(b.ph_min)}–{_fmt(b.ph_max)}",
        )
    elif faixa and (faixa[1] - faixa[0]) < MARGEM_ESTREITA_PH:
        r.adicionar(
            Nivel.RUIM, "parametros",
            f"Sobreposição estreita de pH: só "
            f"{_fmt(faixa[0])}–{_fmt(faixa[1])} atende às duas espécies",
        )

    # ─── 4. Dureza ─────────────────────────────────────────
    faixa = _sobreposicao(a.dgh_min, a.dgh_max, b.dgh_min, b.dgh_max)
    if faixa is None and None not in (a.dgh_min, b.dgh_min):
        r.adicionar(
            Nivel.RUIM, "parametros",
            "Exigências de dureza da água são incompatíveis",
        )

    # ─── 5. Predação por tamanho ───────────────────────────
    # Aqui mora o caso Acará bandeira × Neon tetra
    for maior, menor in ((a, b), (b, a)):
        if not (maior.tamanho_adulto_cm and menor.tamanho_adulto_cm):
            continue
        if maior.alimentacao not in ALIMENTACAO_PREDADORA:
            continue
        if maior.tamanho_adulto_cm >= menor.tamanho_adulto_cm * FATOR_PREDACAO:
            r.adicionar(
                Nivel.FATAL, "predacao",
                f"{maior.nome_comum} adulto ({_fmt(maior.tamanho_adulto_cm)} cm) "
                f"predará {menor.nome_comum} ({_fmt(menor.tamanho_adulto_cm)} cm)",
            )

    # ─── 6. Mordedor de barbatana × peixe de véu ───────────
    for mordedor, alvo in ((a, b), (b, a)):
        if mordedor.morde_barbatana and alvo.barbatana_longa:
            r.adicionar(
                Nivel.RUIM, "barbatana",
                f"{mordedor.nome_comum} belisca as nadadeiras de {alvo.nome_comum}",
            )

    # ─── 7. Agressividade ──────────────────────────────────
    for x, y in ((a, b), (b, a)):
        if x.comportamento == "agressivo":
            r.adicionar(
                Nivel.FATAL, "agressao",
                f"{x.nome_comum} é agressivo e atacará {y.nome_comum}",
            )
        elif x.comportamento == "territorial" and y.nivel_natacao == x.nivel_natacao:
            r.adicionar(
                Nivel.RUIM, "territorio",
                f"{x.nome_comum} é territorial e disputa o mesmo espaço "
                f"que {y.nome_comum}",
            )

    # ─── 8. Predador de invertebrados ──────────────────────
    for x, y in ((a, b), (b, a)):
        if x.come_invertebrados and (y.familia or "").lower() in {
            "atyidae", "palaemonidae", "caridea"
        }:
            r.adicionar(
                Nivel.RUIM, "predacao",
                f"{x.nome_comum} preda camarões e invertebrados",
            )

    return r


# ═══════════════════════════════════════════════════════════
# ANÁLISE COMPLETA DE UMA ADIÇÃO
# ═══════════════════════════════════════════════════════════
def _raiz(especie):
    """A espécie-base, ou a própria espécie quando ela não é variedade."""
    return getattr(especie, "variante_de_id", None) or especie.id


def _mesma_especie(a, b) -> bool:
    """Se dois itens do catálogo são o mesmo animal.

    São quando têm a mesma raiz: duas variedades da mesma base, ou a base
    e uma variedade dela. Duas linhas diferentes do catálogo podem ser o
    mesmo peixe — é para isso que as variedades existem.
    """
    return _raiz(a) == _raiz(b)


def avaliar_adicao(
    nova,
    quantidade: int,
    aquario,
    habitantes: List[tuple],
    excecoes: Optional[dict] = None,
) -> dict:
    excecoes = excecoes or {}
    resultado = Resultado()

    # Espécie criada por importação, ainda sem revisão humana. O aviso
    # entra antes de tudo para que a decisão nunca seja "liberado".
    if getattr(nova, "revisada", True) is False:
        resultado.adicionar(
            Nivel.RUIM, "ficha_incompleta",
            f"A ficha de {nova.nome_comum} veio de uma importação e ainda "
            f"não foi conferida: porte e temperamento não estão "
            f"preenchidos, então esta análise está incompleta",
        )

    # Condições do aquário
    ambiente = avaliar_especie_no_aquario(nova, aquario)
    for a in ambiente.achados:
        resultado.adicionar(a.nivel, a.motivo, a.mensagem)

    # Cardume — corrigível comprando mais indivíduos
    if nova.agrupamento == "cardume" and nova.cardume_minimo:
        if quantidade < nova.cardume_minimo:
            resultado.adicionar(
                Nivel.RUIM, "comportamento",
                f"Vive em cardume: mínimo recomendado de "
                f"{nova.cardume_minimo} indivíduos",
            )

    # Agressividade entre indivíduos da mesma espécie.
    #
    # Contam também os que JÁ estão no aquário e são da mesma espécie-base.
    # Antes das variedades bastava olhar `quantidade`: um segundo Betta
    # caía em "edite a quantidade", porque era a mesma linha do catálogo.
    # Betta Halfmoon e Betta Crowntail são linhas diferentes e o mesmo
    # animal — e dois machos iriam para o mesmo aquário sem aviso.
    ja_presentes = [(e, q) for e, q in habitantes if _mesma_especie(nova, e)]
    total = quantidade + sum(q for _, q in ja_presentes)
    briga = nova.agressivo_coespecificos or any(
        e.agressivo_coespecificos for e, _ in ja_presentes
    )
    if briga and total > 1:
        if ja_presentes:
            nomes = ", ".join(e.nome_comum for e, _ in ja_presentes)
            mensagem = (
                f"{nova.nome_comum} não convive com outros da mesma espécie, "
                f"e o aquário já tem {nomes}"
            )
        else:
            mensagem = f"{nova.nome_comum} não convive com outros da mesma espécie"
        resultado.adicionar(Nivel.FATAL, "agressao", mensagem)

    # Confronto com cada habitante
    for especie, _qtd in habitantes:
        chave = tuple(sorted([str(nova.id), str(especie.id)]))
        par = avaliar_par(nova, especie, excecoes.get(chave))
        for a in par.achados:
            resultado.adicionar(a.nivel, a.motivo, a.mensagem)

    # Lotação — regra clássica de 1 cm de peixe adulto por litro
    if aquario and getattr(aquario, "volume_litros", None):
        cm_total = sum(
            (e.tamanho_adulto_cm or 0) * q for e, q in habitantes
        ) + (nova.tamanho_adulto_cm or 0) * quantidade

        if cm_total > aquario.volume_litros:
            resultado.adicionar(
                Nivel.RUIM, "lotacao",
                f"Aquário ficará superlotado: {_fmt(cm_total)} cm de peixe "
                f"adulto para {_fmt(aquario.volume_litros)}L",
            )

    # ─── Decisão final ─────────────────────────────────────
    tem_fatal = any(a.nivel == Nivel.FATAL for a in resultado.achados)
    tem_impeditivo = any(
        a.nivel == Nivel.RUIM and a.motivo in MOTIVOS_IMPEDITIVOS
        for a in resultado.achados
    )
    tem_ressalva = any(
        a.nivel == Nivel.RUIM and a.motivo in MOTIVOS_CORRIGIVEIS
        for a in resultado.achados
    )

    if tem_fatal or tem_impeditivo:
        decisao = "bloqueado"
    elif tem_ressalva:
        decisao = "requer_confirmacao"
    else:
        decisao = "liberado"

    motivos_bloqueio = [
        a.mensagem
        for a in resultado.achados
        if a.nivel == Nivel.FATAL or a.motivo in MOTIVOS_IMPEDITIVOS
    ]

    ressalvas = [
        a.mensagem
        for a in resultado.achados
        if a.nivel == Nivel.RUIM and a.motivo in MOTIVOS_CORRIGIVEIS
    ]

    return {
        "nivel": resultado.nivel.value,
        "decisao": decisao,
        "pode_adicionar": decisao != "bloqueado",
        "exige_confirmacao": decisao == "requer_confirmacao",
        "motivos_bloqueio": motivos_bloqueio,
        "ressalvas": ressalvas,
        "avisos": [
            {"nivel": a.nivel.value, "motivo": a.motivo, "mensagem": a.mensagem}
            for a in resultado.achados
        ],
    }