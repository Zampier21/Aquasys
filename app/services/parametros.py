"""
Faixas ideais dos parâmetros de água e geração de alertas.

Fonte única da regra: antes, as faixas viviam duplicadas no app
(`parametrosInfo`, em tela_aquarios.dart) e não existiam no servidor.
Agora o app só exibe o que a API decidiu.

A faixa sai de duas camadas, nesta ordem:

1. O TIPO do aquário (doce | marinho | plantado | comunitario) — é o
   palpite inicial, usado enquanto o aquário está vazio.
2. Os PEIXES que moram nele — quando há habitantes cadastrados, são eles
   que mandam. Um "comunitário" povoado só com ciclídeos africanos vive
   em água alcalina, e acusar pH 8 de erro ali seria falso alarme.
"""

from dataclasses import dataclass, replace
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════
# ESCALA DE pH
# ═══════════════════════════════════════════════════════
# O cliente não sabe o que fazer com um intervalo solto ("6.5 – 7.0").
# Saber ler o número é mais útil: por isso o app mostra a escala, e não
# só a faixa.
ESCALA_PH = (
    "O pH mede se a água é ácida ou alcalina: de 0 a 6.8 é ácida, "
    "7.0 é neutra e de 7.2 até 14 é alcalina."
)


def classificar_ph(valor: float) -> str:
    """Devolve 'ácida', 'neutra' ou 'alcalina' para o valor medido."""
    if valor < 6.9:
        return "ácida"
    if valor <= 7.1:
        return "neutra"
    return "alcalina"


# ═══════════════════════════════════════════════════════
# FAIXAS
# ═══════════════════════════════════════════════════════
@dataclass(frozen=True)
class FaixaIdeal:
    chave: str
    nome: str
    campo: str          # atributo em ParametrosAgua / Aquario
    minimo: float
    maximo: float
    unidade: str

    # Preenchidos quando a faixa foi apertada pelos peixes do aquário.
    origem: str = "tipo"                    # "tipo" | "habitantes"
    conflito: bool = False                  # espécies que não convivem
    responsavel_min: Optional[str] = None   # espécie que puxou o piso
    responsavel_max: Optional[str] = None   # espécie que puxou o teto

    def fora_da_faixa(self, valor: float) -> bool:
        return valor < self.minimo or valor > self.maximo

    @property
    def texto(self) -> str:
        """Faixa em texto para a tela: '24 °C – 28 °C', '0 ppm — sempre zero'."""
        unidade = f" {self.unidade}" if self.unidade else ""
        if self.minimo == self.maximo == 0:
            return "0 ppm — sempre zero"

        # Se um dos limites tem decimal, os dois mostram decimal: "6.5 – 7.0"
        # lê melhor que "6.5 – 7" numa faixa de pH. E pH sempre mostra a
        # casa: "6 – 7" parece grosseiro para uma escala de 0 a 14.
        decimal = self.chave == "ph" or self.minimo % 1 or self.maximo % 1
        fmt = (lambda v: f"{v:.1f}") if decimal else (lambda v: f"{v:g}")

        if self.minimo == 0:
            return f"Abaixo de {fmt(self.maximo)}{unidade}"
        return f"{fmt(self.minimo)}{unidade} – {fmt(self.maximo)}{unidade}"

    def descrever_desvio(self, valor: float) -> str:
        """Ex.: '0.3 acima do ideal' — o texto que vai para o alerta."""
        if valor > self.maximo:
            diferenca = valor - self.maximo
            direcao = "acima"
        else:
            diferenca = self.minimo - valor
            direcao = "abaixo"

        # Sem casa decimal quando o número é redondo: "2" em vez de "2.0".
        formatado = f"{diferenca:.1f}".rstrip("0").rstrip(".")
        return f"{formatado} {direcao} do ideal"

    def culpado(self, valor: float) -> Optional[str]:
        """Espécie cujo limite o valor medido está furando, se houver."""
        if valor > self.maximo:
            return self.responsavel_max
        if valor < self.minimo:
            return self.responsavel_min
        return None


def _faixas(temp: tuple, ph: tuple, nitrato_max: float) -> List[FaixaIdeal]:
    """Monta o conjunto de faixas variando só o que muda entre os tipos."""
    return [
        FaixaIdeal("temperatura", "Temperatura", "temperatura", temp[0], temp[1], "°C"),
        FaixaIdeal("ph", "pH", "ph", ph[0], ph[1], ""),
        # Amônia e nitrito são tóxicos em qualquer concentração, em
        # qualquer tipo de aquário: o ideal é sempre zero.
        FaixaIdeal("amonia", "Amônia", "amonia_ppm", 0, 0, "ppm"),
        FaixaIdeal("nitrito", "Nitrito", "nitrito_ppm", 0, 0, "ppm"),
        FaixaIdeal("nitrato", "Nitrato", "nitrato_ppm", 0, nitrato_max, "ppm"),
    ]


FAIXAS_POR_TIPO: Dict[str, List[FaixaIdeal]] = {
    # Peixes tropicais em convívio. Faixa de pH conforme o seu Figma:
    # é ela que faz 7.3 aparecer como "0.3 acima do ideal".
    "comunitario": _faixas(temp=(24, 28), ph=(6.5, 7.0), nitrato_max=40),
    "doce": _faixas(temp=(24, 28), ph=(6.5, 7.5), nitrato_max=40),
    # Plantado aceita pH mais ácido e tolera nitrato — as plantas consomem.
    "plantado": _faixas(temp=(22, 28), ph=(6.0, 7.5), nitrato_max=40),
    # Marinho vive em água alcalina e é bem menos tolerante a nitrato.
    "marinho": _faixas(temp=(24, 27), ph=(8.0, 8.4), nitrato_max=20),
}

TIPO_PADRAO = "comunitario"

# Só temperatura e pH têm equivalente no catálogo de espécies. Amônia,
# nitrito e nitrato são veneno para todo peixe: não dependem de quem mora
# no aquário e continuam vindo do tipo.
_CAMPOS_ESPECIE = {
    "temperatura": ("temp_min", "temp_max"),
    "ph": ("ph_min", "ph_max"),
}


def _faixa_dos_habitantes(base: FaixaIdeal, habitantes) -> FaixaIdeal:
    """
    Aperta a faixa do tipo com o que as espécies do aquário aguentam.

    A mesma água serve todo mundo ao mesmo tempo, então o intervalo válido
    é a interseção das tolerâncias: o maior dos mínimos e o menor dos
    máximos. É isso que impede um comunitário povoado com peixes de água
    alcalina de ser acusado de "pH acima do ideal" pela faixa genérica.
    """
    campo_min, campo_max = _CAMPOS_ESPECIE[base.chave]

    limites = [
        (getattr(e, campo_min), getattr(e, campo_max), e.nome_comum)
        for e in habitantes
        if getattr(e, campo_min, None) is not None
        and getattr(e, campo_max, None) is not None
    ]
    if not limites:
        # Espécie sem esse dado no catálogo: a faixa do tipo continua valendo.
        return base

    piso, _, dono_piso = max(limites, key=lambda l: l[0])
    _, teto, dono_teto = min(limites, key=lambda l: l[1])

    if piso > teto:
        # As exigências não se cruzam — não existe água que agrade a todos.
        # Alargar em vez de inventar um alvo impossível: quem aponta esse
        # conflito é o motor de compatibilidade, não o alerta de parâmetro.
        return replace(
            base,
            minimo=min(l[0] for l in limites),
            maximo=max(l[1] for l in limites),
            origem="habitantes",
            conflito=True,
        )

    return replace(
        base,
        minimo=piso,
        maximo=teto,
        origem="habitantes",
        responsavel_min=dono_piso,
        responsavel_max=dono_teto,
    )


def faixas_do_aquario(aquario, habitantes=None) -> List[FaixaIdeal]:
    """
    Faixas válidas para este aquário.

    `habitantes` é a lista de `Especie` que vive nele. Quando vem vazia
    (aquário novo), valem as faixas do tipo; sem tipo definido, assume
    comunitário.
    """
    tipo = (getattr(aquario, "tipo", None) or TIPO_PADRAO).lower()
    faixas = FAIXAS_POR_TIPO.get(tipo, FAIXAS_POR_TIPO[TIPO_PADRAO])

    if not habitantes:
        return faixas

    return [
        _faixa_dos_habitantes(f, habitantes) if f.chave in _CAMPOS_ESPECIE else f
        for f in faixas
    ]


def _valor_do_parametro(faixa: FaixaIdeal, aquario, medicao) -> Optional[float]:
    """Temperatura e pH vivem no aquário; os químicos, na última medição."""
    origem = aquario if faixa.campo in ("temperatura", "ph") else medicao
    if origem is None:
        return None

    valor = getattr(origem, faixa.campo, None)
    return None if valor is None else float(valor)


# ═══════════════════════════════════════════════════════
# EXPLICAÇÕES EM LINGUAGEM DE GENTE
# ═══════════════════════════════════════════════════════
def _num(valor: float) -> str:
    """26.0 → '26'; 26.5 → '26.5'. Casa decimal só onde ela informa algo."""
    return f"{valor:.1f}" if valor % 1 else f"{valor:g}"


def _num_ph(valor: float) -> str:
    """pH sempre com uma casa: 7 vira '7.0', que é como o teste de água mostra."""
    return f"{valor:.1f}"


def _motivo_do_erro(faixa: FaixaIdeal, valor: float) -> str:
    """
    Por que este parâmetro está errado, citando o peixe responsável.

    É a diferença entre "pH 0.3 acima do ideal" — que não diz o que fazer —
    e "o Neon Tetra vive em água mais ácida".
    """
    culpado = faixa.culpado(valor)
    alto = valor > faixa.maximo

    if faixa.chave == "ph":
        estado = classificar_ph(valor)
        if culpado:
            lado = "mais ácida" if alto else "mais alcalina"
            limite = (
                f"até {_num_ph(faixa.maximo)}" if alto
                else f"a partir de {_num_ph(faixa.minimo)}"
            )
            return (
                f"Esse parâmetro está errado pois o {culpado} vive em água "
                f"{lado} (pH {limite}), e a sua está em {_num_ph(valor)} ({estado})."
            )
        return (
            f"A água está em pH {_num_ph(valor)} ({estado}), fora da faixa "
            f"{faixa.texto} indicada para este tipo de aquário."
        )

    if faixa.chave == "temperatura" and culpado:
        lado = "mais fria" if alto else "mais quente"
        return (
            f"Esse parâmetro está errado pois o {culpado} vive em água "
            f"{lado} ({faixa.texto}), e a sua está em {_num(valor)} °C."
        )

    unidade = f" {faixa.unidade}" if faixa.unidade else ""
    return (
        f"{faixa.nome} está {faixa.descrever_desvio(valor)} "
        f"({_num(valor)}{unidade}). O recomendado é {faixa.texto}."
    )


def _confirmacao(faixa: FaixaIdeal, valor: float) -> str:
    """Frase para quando o parâmetro está certo — sossega o cliente."""
    if faixa.chave == "ph":
        estado = classificar_ph(valor)
        if faixa.origem == "habitantes":
            return (
                f"A água está em pH {_num_ph(valor)} ({estado}) e serve aos "
                f"peixes deste aquário, que vivem entre {faixa.texto}."
            )
        return (
            f"A água está em pH {_num_ph(valor)} ({estado}), "
            f"dentro de {faixa.texto}."
        )

    return f"Dentro do recomendado ({faixa.texto})."


def explicar(aquario, medicao, habitantes=None) -> Dict[str, str]:
    """
    Uma frase por parâmetro, dizendo se está certo e por quê.

    É o que a tela de aquários mostra no lugar do intervalo cru.
    """
    textos: Dict[str, str] = {}

    for faixa in faixas_do_aquario(aquario, habitantes):
        valor = _valor_do_parametro(faixa, aquario, medicao)
        if valor is None:
            continue

        if faixa.conflito:
            textos[faixa.chave] = (
                f"Os peixes deste aquário pedem faixas de {faixa.nome.lower()} "
                f"que não se cruzam — veja a compatibilidade na aba Peixes."
            )
            continue

        textos[faixa.chave] = (
            _motivo_do_erro(faixa, valor) if faixa.fora_da_faixa(valor)
            else _confirmacao(faixa, valor)
        )

    return textos


# ═══════════════════════════════════════════════════════
# AVALIAÇÃO
# ═══════════════════════════════════════════════════════
def avaliar(aquario, medicao, habitantes=None) -> tuple[List[dict], int]:
    """
    Confere os parâmetros de um aquário contra as faixas que valem para ele.

    Devolve `(problemas, avaliados)`:
    - `problemas`: um dicionário por parâmetro fora da faixa, pronto para
      virar linha em `alerta` ou item da tela;
    - `avaliados`: quantos parâmetros tinham valor para conferir. Parâmetro
      sem medição não conta como aprovado — só fica de fora da conta.
    """
    problemas = []
    avaliados = 0

    for faixa in faixas_do_aquario(aquario, habitantes):
        valor = _valor_do_parametro(faixa, aquario, medicao)
        if valor is None:
            continue

        avaliados += 1

        # Faixa em conflito não reprova o parâmetro: o problema ali é a
        # combinação de espécies, e é na aba Peixes que ele aparece.
        if faixa.conflito or not faixa.fora_da_faixa(valor):
            continue

        unidade = f" {faixa.unidade}" if faixa.unidade else ""
        problemas.append({
            "parametro": faixa.chave,
            "nome": faixa.nome,
            "valor": valor,
            "unidade": faixa.unidade,
            "mensagem": (
                f'{faixa.nome} do aquário "{aquario.nome}" está '
                f"{faixa.descrever_desvio(valor)} "
                f"({valor:g}{unidade})"
            ),
            "motivo": _motivo_do_erro(faixa, valor),
        })

    return problemas, avaliados


def faixas_em_texto(aquario, habitantes=None) -> dict:
    """{chave: faixa ideal em texto} conforme o tipo e os peixes do aquário."""
    return {f.chave: f.texto for f in faixas_do_aquario(aquario, habitantes)}
