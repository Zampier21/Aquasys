"""
Gera a Figura 1 do TCC: arquitetura do AquaSys.

    python gerar_figura_arquitetura.py

Saem dois arquivos do mesmo desenho:

  figura_arquitetura.svg  para importar no Figma (Arquivo > Importar).
                          Cada caixa, texto e seta vira uma camada
                          editavel, com nome, e a fonte e' a Inter,
                          que e' a padrao do Figma.
  figura_arquitetura.png  para o documento, em 2x.

O desenho e' descrito uma vez so, como lista de formas, e as duas saidas
leem a mesma lista. Assim o PNG e o SVG nao tem como divergir.

O que mudou em relacao a primeira versao, e por que:

  . as integracoes externas aparecem. O servidor consulta o YouTube para
    buscar os dados dos videos quando a loja cadastra um curso, e o
    aplicativo toca o video direto do YouTube. As fotos do Wikimedia
    Commons NAO passam pela API em tempo de uso: um script as baixa uma
    vez e grava no banco. Por isso a seta do Wikimedia e' tracejada e
    entra direto no PostgreSQL;
  . cada caixa diz o nome da coisa, e nao uma frase explicando o que ela
    faz. A explicacao esta no texto da Secao 5.2, que e' onde a banca le;
  . sem travessao, sem ponto medio como separador e sem titulo em caixa
    alta numerado, que eram o que dava a cara de gerado;
  . as cores sao as do tema do proprio aplicativo (AppTheme).
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
L, A = 1200, 776
SUPER = 4          # desenha em 4x e reduz: e' o que da borda lisa no Pillow
SAIDA = 2          # PNG final em 2x: 2400 px, acima de 300 dpi em 16 cm

# ─── Cores do AppTheme do aplicativo ─────────────────
PRIMARIA = "#0096C7"
SUCESSO = "#00875A"
ALERTA = "#D97706"
SUPERFICIE = "#EAF4FB"
FUNDO_CAMADA = "#F5FAFE"
BORDA_CAMADA = "#D6EAF5"
BORDA_CAIXA = "#D0D5DD"
TEXTO = "#1D2939"
TEXTO_MEDIO = "#344054"
TEXTO_ROTULO = "#475467"
TEXTO_FRACO = "#667085"
SETA = "#98A2B3"
BRANCO = "#FFFFFF"

# ─── Fontes ──────────────────────────────────────────
# No Figma a figura usa Inter. Aqui, para o PNG, a Segoe UI: e' a que
# esta instalada e tem o mesmo desenho geometrico e a mesma largura.
FONTES = {
    400: r"C:\Windows\Fonts\segoeui.ttf",
    600: r"C:\Windows\Fonts\seguisb.ttf",
}


# ═══════════════════════════════════════════════════════
# O DESENHO, DESCRITO UMA VEZ
# ═══════════════════════════════════════════════════════
formas = []


def caixa(nome, x0, y0, x1, y1, raio=8, fundo=BRANCO, borda=BORDA_CAIXA,
          espessura=1, tracejado=False):
    formas.append(("caixa", nome, x0, y0, x1, y1, raio, fundo, borda,
                   espessura, tracejado))


def texto(nome, x, cy, conteudo, tamanho, peso=400, cor=TEXTO,
          centro=False):
    formas.append(("texto", nome, x, cy, conteudo, tamanho, peso, cor,
                   centro))


def ponto(nome, cx, cy, raio, cor):
    formas.append(("ponto", nome, cx, cy, raio, cor))


def seta(nome, pontos, dupla=False, tracejada=False, ponta=8):
    formas.append(("seta", nome, pontos, dupla, tracejada, ponta))


def etiqueta(nome, cx, cy, conteudo):
    """Rótulo sobre o conector, como o FigJam faz."""
    largura = 10 + len(conteudo) * 6.6
    caixa(nome + "-fundo", cx - largura / 2, cy - 11, cx + largura / 2,
          cy + 11, raio=11, borda=BORDA_CAMADA)
    texto(nome, cx, cy, conteudo, 12, cor=TEXTO_ROTULO, centro=True)


def camada(chave, rotulo, cor, y0, y1, titulo, legenda):
    ponto(chave + "-marca", 46, y0 - 17, 4, cor)
    texto(chave + "-rotulo", 57, y0 - 17, rotulo, 13, 600, TEXTO_ROTULO)
    caixa(chave, 40, y0, 780, y1, raio=12, fundo=FUNDO_CAMADA,
          borda=BORDA_CAMADA)
    texto(chave + "-titulo", 64, y0 + 30, titulo, 17, 600, TEXTO)
    texto(chave + "-legenda", 64, y0 + 52, legenda, 13, 400, TEXTO_FRACO)


def modulos(chave, nomes, y0, intervalo, destaque=None, setas=False):
    """Uma fileira de caixas iguais dentro da camada."""
    x, x_fim, altura = 64, 756, 54
    largura = (x_fim - x - intervalo * (len(nomes) - 1)) / len(nomes)
    for i, nome in enumerate(nomes):
        a = x + i * (largura + intervalo)
        cy = y0 + altura / 2
        if nome == destaque:
            caixa("%s-%d" % (chave, i), a, y0, a + largura, y0 + altura,
                  fundo=SUPERFICIE, borda=PRIMARIA, espessura=1.5)
            texto("%s-%d-nome" % (chave, i), a + largura / 2, cy - 8, nome,
                  14, 600, TEXTO_MEDIO, centro=True)
            texto("%s-%d-legenda" % (chave, i), a + largura / 2, cy + 11,
                  "regras de negócio", 11.5, 400, PRIMARIA, centro=True)
        else:
            caixa("%s-%d" % (chave, i), a, y0, a + largura, y0 + altura)
            texto("%s-%d-nome" % (chave, i), a + largura / 2, cy, nome, 14,
                  600, TEXTO_MEDIO, centro=True)
        if setas and i < len(nomes) - 1:
            seta("%s-fluxo-%d" % (chave, i),
                 [(a + largura + 5, cy), (a + largura + intervalo - 5, cy)],
                 ponta=6)


# ─── Quem usa ────────────────────────────────────────
for i, (nome, legenda) in enumerate([("Loja assinante", "CNPJ"),
                                      ("Cliente da loja", "CPF")]):
    x0 = 190 + i * 240
    caixa("usuario-%d" % i, x0, 30, x0 + 200, 84, raio=27)
    texto("usuario-%d-nome" % i, x0 + 100, 50, nome, 15, 600, TEXTO,
          centro=True)
    texto("usuario-%d-perfil" % i, x0 + 100, 68, legenda, 12, 400,
          TEXTO_FRACO, centro=True)
    seta("acesso-%d" % i, [(x0 + 100, 84), (x0 + 100, 131)])

# ─── Apresentação ────────────────────────────────────
camada("apresentacao", "Apresentação", PRIMARIA, 132, 292,
       "Aplicativo Flutter", "Android e iOS")
modulos("apresentacao-modulo",
        ["Telas", "Componentes", "Cliente HTTP", "Notificações locais"],
        212, 16)

seta("requisicao", [(410, 293), (410, 391)], dupla=True)
texto("requisicao-protocolo", 422, 332, "REST sobre HTTPS", 12, 600,
      TEXTO_ROTULO)
texto("requisicao-token", 422, 350, "token JWT", 12, 400, TEXTO_FRACO)

# ─── Lógica de negócio ───────────────────────────────
camada("negocio", "Lógica de negócio", SUCESSO, 392, 552,
       "API FastAPI", "monolito modular")
modulos("negocio-modulo", ["Rotas", "Contratos", "Serviços", "Modelos"],
        472, 28, destaque="Serviços", setas=True)

seta("consulta", [(410, 553), (410, 651)], dupla=True)
texto("consulta-sql", 422, 602, "SQL", 12, 600, TEXTO_ROTULO)

# ─── Dados ───────────────────────────────────────────
camada("dados", "Dados", ALERTA, 652, 736, "PostgreSQL",
       "18 tabelas, multilocação por linha")

# ─── Serviços externos ───────────────────────────────
ponto("youtube-marca", 910, 315, 4, SETA)
texto("youtube-rotulo", 921, 315, "Serviço externo", 13, 600, TEXTO_ROTULO)
caixa("youtube", 904, 332, 1144, 396, tracejado=True)
texto("youtube-nome", 1024, 355, "YouTube", 15, 600, TEXTO, centro=True)
texto("youtube-legenda", 1024, 374, "vídeos dos cursos", 12, 400,
      TEXTO_FRACO, centro=True)

# O aplicativo toca o vídeo direto do YouTube; o servidor só consulta os
# dados do vídeo quando a loja cadastra o curso.
seta("reproducao", [(780, 250), (830, 250), (830, 352), (903, 352)])
etiqueta("reproducao-rotulo", 830, 300, "reprodução")
seta("metadados", [(780, 440), (830, 440), (830, 376), (903, 376)])
etiqueta("metadados-rotulo", 830, 408, "metadados")

ponto("wikimedia-marca", 910, 645, 4, SETA)
texto("wikimedia-rotulo", 921, 645, "Serviço externo", 13, 600, TEXTO_ROTULO)
caixa("wikimedia", 904, 662, 1144, 726, tracejado=True)
texto("wikimedia-nome", 1024, 685, "Wikimedia Commons", 15, 600, TEXTO,
      centro=True)
texto("wikimedia-legenda", 1024, 704, "fotos das espécies", 12, 400,
      TEXTO_FRACO, centro=True)

# Tracejada porque não é chamada em tempo de uso: um script baixa as
# fotos uma vez e grava no banco, e a API serve a cópia local.
seta("carga", [(903, 694), (781, 694)], tracejada=True)
texto("carga-rotulo", 790, 680, "carga por script", 12, 400, TEXTO_FRACO)


# ═══════════════════════════════════════════════════════
# SAÍDA 1: SVG PARA O FIGMA
# ═══════════════════════════════════════════════════════
def _ponta(p, q, tamanho):
    """Triângulo da ponta em q, apontando na direção p -> q."""
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    esq = (q[0] - tamanho * math.cos(ang - 0.45),
           q[1] - tamanho * math.sin(ang - 0.45))
    dir_ = (q[0] - tamanho * math.cos(ang + 0.45),
            q[1] - tamanho * math.sin(ang + 0.45))
    return [q, esq, dir_]


def _escapar(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def gerar_svg(caminho):
    # As pontas das setas são polígonos soltos, e não <marker>: o Figma
    # descarta marcadores na importação e a seta chegaria sem ponta.
    saida = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d">' % (L, A, L, A),
             '<rect id="fundo" width="%d" height="%d" fill="%s"/>'
             % (L, A, BRANCO)]
    for f in formas:
        tipo, nome = f[0], f[1]
        if tipo == "caixa":
            _, _, x0, y0, x1, y1, r, fundo, borda, esp, trac = f
            saida.append(
                '<rect id="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                'rx="%g" fill="%s" stroke="%s" stroke-width="%g"%s/>'
                % (nome, x0, y0, x1 - x0, y1 - y0, r, fundo, borda, esp,
                   ' stroke-dasharray="6 4"' if trac else ""))
        elif tipo == "texto":
            _, _, x, cy, s, tam, peso, cor, centro = f
            saida.append(
                '<text id="%s" x="%.1f" y="%.1f" font-family="Inter, Segoe UI, '
                'sans-serif" font-size="%g" font-weight="%d" fill="%s"%s>%s'
                '</text>' % (nome, x, cy + tam * 0.35, tam, peso, cor,
                             ' text-anchor="middle"' if centro else "",
                             _escapar(s)))
        elif tipo == "ponto":
            _, _, cx, cy, r, cor = f
            saida.append('<circle id="%s" cx="%g" cy="%g" r="%g" fill="%s"/>'
                         % (nome, cx, cy, r, cor))
        elif tipo == "seta":
            _, _, pts, dupla, trac, tam = f
            saida.append('<g id="%s">' % nome)
            saida.append(
                '<polyline points="%s" fill="none" stroke="%s" '
                'stroke-width="1.5" stroke-linejoin="round"%s/>'
                % (" ".join("%g,%g" % p for p in pts), SETA,
                   ' stroke-dasharray="5 4"' if trac else ""))
            pontas = [_ponta(pts[-2], pts[-1], tam)]
            if dupla:
                pontas.append(_ponta(pts[1], pts[0], tam))
            for tri in pontas:
                saida.append('<polygon points="%s" fill="%s"/>'
                             % (" ".join("%.1f,%.1f" % p for p in tri), SETA))
            saida.append("</g>")
    saida.append("</svg>")
    open(caminho, "w", encoding="utf-8").write("\n".join(saida))


# ═══════════════════════════════════════════════════════
# SAÍDA 2: PNG PARA O DOCUMENTO
# ═══════════════════════════════════════════════════════
def _perimetro(x0, y0, x1, y1, r, passos=12):
    """Contorno da caixa arredondada como polilinha, para o tracejado."""
    pts = []
    cantos = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0),
              (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    for cx, cy, inicio in cantos:
        for k in range(passos + 1):
            a = math.radians(inicio + 90 * k / passos)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(pts[0])
    return pts


def _tracejar(desenho, pts, cor, esp, traco, vao):
    ligado, resto = True, traco
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, by - ay)
        feito = 0.0
        while feito < seg:
            passo = min(resto, seg - feito)
            t0, t1 = feito / seg, (feito + passo) / seg
            if ligado:
                desenho.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0),
                              (ax + (bx - ax) * t1, ay + (by - ay) * t1)],
                             fill=cor, width=esp)
            feito += passo
            resto -= passo
            if resto <= 1e-6:
                ligado = not ligado
                resto = traco if ligado else vao


def gerar_png(caminho):
    s = SUPER
    img = Image.new("RGB", (L * s, A * s), BRANCO)
    d = ImageDraw.Draw(img)
    cache = {}

    def fonte(tam, peso):
        chave = (tam, peso)
        if chave not in cache:
            cache[chave] = ImageFont.truetype(FONTES[peso], round(tam * s))
        return cache[chave]

    for f in formas:
        tipo = f[0]
        if tipo == "caixa":
            _, _, x0, y0, x1, y1, r, fundo, borda, esp, trac = f
            caixa_px = [x0 * s, y0 * s, x1 * s, y1 * s]
            if trac:
                d.rounded_rectangle(caixa_px, r * s, fill=fundo)
                _tracejar(d, [(x * s, y * s) for x, y in
                              _perimetro(x0, y0, x1, y1, r)],
                          borda, round(esp * s), 6 * s, 4 * s)
            else:
                d.rounded_rectangle(caixa_px, r * s, fill=fundo, outline=borda,
                                    width=round(esp * s))
        elif tipo == "texto":
            _, _, x, cy, conteudo, tam, peso, cor, centro = f
            d.text((x * s, cy * s), conteudo, font=fonte(tam, peso), fill=cor,
                   anchor="mm" if centro else "lm")
        elif tipo == "ponto":
            _, _, cx, cy, r, cor = f
            d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s],
                      fill=cor)
        elif tipo == "seta":
            _, _, pts, dupla, trac, tam = f
            px = [(x * s, y * s) for x, y in pts]
            # A linha para antes da ponta, senão o traço grosso aparece
            # por cima do triângulo e cega a ponta.
            recuo = tam * 0.8 * s

            def recuar(p, q):
                dist = math.hypot(q[0] - p[0], q[1] - p[1])
                return (q[0] - (q[0] - p[0]) * recuo / dist,
                        q[1] - (q[1] - p[1]) * recuo / dist)

            linha = list(px)
            linha[-1] = recuar(px[-2], px[-1])
            if dupla:
                linha[0] = recuar(px[1], px[0])
            if trac:
                _tracejar(d, linha, SETA, round(1.5 * s), 5 * s, 4 * s)
            else:
                d.line(linha, fill=SETA, width=round(1.5 * s), joint="curve")
            d.polygon(_ponta(px[-2], px[-1], tam * s), fill=SETA)
            if dupla:
                d.polygon(_ponta(px[1], px[0], tam * s), fill=SETA)

    img = img.resize((L * SAIDA, A * SAIDA), Image.LANCZOS)
    img.save(caminho, dpi=(300, 300))


if __name__ == "__main__":
    svg = os.path.join(AQUI, "figura_arquitetura.svg")
    png = os.path.join(AQUI, "figura_arquitetura.png")
    gerar_svg(svg)
    gerar_png(png)
    print("gerado: %s" % svg)
    print("gerado: %s (%d x %d px)" % (png, L * SAIDA, A * SAIDA))
    print("formas: %d" % len(formas))
