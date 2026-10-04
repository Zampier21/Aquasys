"""
Gera a Figura 2 do TCC — arquitetura em três camadas do AquaSys.

    python gerar_figura_arquitetura.py

Desenhado com Pillow, e não a partir do SVG, porque esta máquina não tem
as bibliotecas nativas do cairo (cairosvg e reportlab falham sem elas).
O SVG equivalente fica em figura_arquitetura.svg, para quem preferir
inserir vetor no Word — o Word 2016 em diante aceita SVG e imprime mais
nítido do que qualquer PNG.

Tema claro, como pedido na revisão: fundo branco e traços escuros, que
é o que sobrevive à impressão em preto e branco.
"""

from PIL import Image, ImageDraw, ImageFont

ESCALA = 2  # 2x para a figura não serrilhar no papel
L, A = 940, 812

# ─── Paleta ──────────────────────────────────────────
BRANCO = (255, 255, 255)
CINZA_SETA = (90, 107, 123)

AZUL_FUNDO, AZUL_BORDA, AZUL_TEXTO, AZUL_FRACO = (
    (244, 249, 253), (90, 143, 191), (31, 58, 82), (74, 96, 118))
AZUL_CLARO, AZUL_LINHA = (234, 242, 250), (143, 180, 212)

VERDE_FUNDO, VERDE_BORDA, VERDE_TEXTO, VERDE_FRACO = (
    (242, 250, 246), (62, 142, 107), (20, 80, 58), (47, 107, 82))
VERDE_CLARO, VERDE_LINHA = (230, 245, 238), (127, 191, 163)

AMBAR_FUNDO, AMBAR_BORDA, AMBAR_TEXTO, AMBAR_FRACO = (
    (251, 247, 236), (217, 185, 121), (122, 91, 18), (138, 109, 42))

MARROM_FUNDO, MARROM_BORDA, MARROM_TEXTO, MARROM_FRACO = (
    (250, 246, 242), (176, 122, 74), (107, 63, 22), (138, 90, 46))

VERMELHO = (176, 58, 46)
VERDE_OK = (27, 122, 75)


def fonte(tamanho, negrito=False, italico=False):
    nome = "arialbi.ttf" if (negrito and italico) else \
           "arialbd.ttf" if negrito else \
           "ariali.ttf" if italico else "arial.ttf"
    try:
        return ImageFont.truetype(rf"C:\Windows\Fonts\{nome}", tamanho * ESCALA)
    except OSError:
        return ImageFont.load_default()


img = Image.new("RGB", (L * ESCALA, A * ESCALA), BRANCO)
d = ImageDraw.Draw(img)


def e(v):
    return v * ESCALA


def caixa(x, y, larg, alt, raio, fundo, borda, grossura=2):
    d.rounded_rectangle(
        [e(x), e(y), e(x + larg), e(y + alt)],
        radius=e(raio), fill=fundo, outline=borda, width=int(e(grossura)),
    )


def txt(x, y, texto, tam, cor, negrito=False, italico=False, centro=None):
    f = fonte(tam, negrito, italico)
    if centro is not None:
        largura = d.textlength(texto, font=f)
        x = centro - largura / e(1) / 2 if False else centro - largura / ESCALA / 2
    d.text((e(x), e(y)), texto, font=f, fill=cor)


def seta(x, y1, y2, dupla=False):
    """Seta vertical; `dupla` desenha ponta nas duas extremidades."""
    d.line([e(x), e(y1), e(x), e(y2)], fill=CINZA_SETA, width=int(e(2)))
    p = 7
    d.polygon([(e(x), e(y2)), (e(x - p / 2), e(y2 - p)), (e(x + p / 2), e(y2 - p))],
              fill=CINZA_SETA)
    if dupla:
        d.polygon([(e(x), e(y1)), (e(x - p / 2), e(y1 + p)), (e(x + p / 2), e(y1 + p))],
                  fill=CINZA_SETA)


def seta_diagonal(x1, y1, x2, y2):
    d.line([e(x1), e(y1), e(x2), e(y2)], fill=CINZA_SETA, width=int(e(1.5)))
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    p = 8
    pts = [(x2, y2)]
    for delta in (2.6, -2.6):
        pts.append((x2 + p * math.cos(ang + delta), y2 + p * math.sin(ang + delta)))
    d.polygon([(e(a), e(b)) for a, b in pts], fill=CINZA_SETA)


# ═══════════ USUÁRIOS ═══════════
for x, titulo, sub in ((250, "Loja assinante", "perfil CNPJ"),
                       (490, "Cliente da loja", "perfil CPF")):
    caixa(x, 18, 200, 46, 23, AZUL_CLARO, AZUL_LINHA, 1.5)
    txt(0, 28, titulo, 14, AZUL_TEXTO, negrito=True, centro=x + 100)
    txt(0, 46, sub, 11, AZUL_FRACO, centro=x + 100)

seta_diagonal(350, 66, 400, 96)
seta_diagonal(590, 66, 540, 96)

# ═══════════ 1. APRESENTAÇÃO ═══════════
caixa(60, 100, 820, 176, 10, AZUL_FUNDO, AZUL_BORDA)
txt(82, 116, "1. CAMADA DE APRESENTAÇÃO", 15, AZUL_TEXTO, negrito=True)
txt(82, 138, "Flutter (Dart) — executa no aparelho do usuário · base de código "
             "única para Android e iOS", 12, AZUL_FRACO)

blocos = [("Telas", "exibem o que a API decidiu"),
          ("Widgets", "componentes reutilizáveis"),
          ("Serviços", "acesso à API por domínio"),
          ("Tema", "cores, tipografia, espaçamento")]
for i, (titulo, sub) in enumerate(blocos):
    x = 82 + i * 196
    larg = 188 if i == 3 else 180
    caixa(x, 162, larg, 52, 6, BRANCO, AZUL_LINHA, 1.3)
    txt(0, 171, titulo, 12.5, AZUL_TEXTO, negrito=True, centro=x + larg / 2)
    txt(0, 191, sub, 10.5, (90, 107, 123), centro=x + larg / 2)

caixa(82, 224, 776, 38, 6, (227, 239, 248), AZUL_BORDA, 1.3)
txt(0, 235, "Api — cliente HTTP único: monta a requisição, anexa o token, "
            "traduz o erro", 12.5, AZUL_TEXTO, negrito=True, centro=470)

txt(0, 284, "Não contém regra de negócio", 12, VERMELHO, italico=True, centro=470)

# ═══════════ COMUNICAÇÃO ═══════════
seta(440, 302, 352, dupla=True)
caixa(470, 304, 392, 46, 6, AMBAR_FUNDO, AMBAR_BORDA, 1.3)
txt(0, 312, "API REST sobre HTTPS · token JWT em cada requisição",
    12, AMBAR_TEXTO, negrito=True, centro=666)
txt(0, 331, "requisições autocontidas — servidor sem estado de sessão",
    11, AMBAR_FRACO, centro=666)

# ═══════════ 2. LÓGICA DE NEGÓCIO ═══════════
caixa(60, 358, 820, 282, 10, VERDE_FUNDO, VERDE_BORDA)
txt(82, 374, "2. CAMADA DE LÓGICA DE NEGÓCIO", 15, VERDE_TEXTO, negrito=True)
txt(82, 396, "FastAPI (Python) — monolito modular, replicável horizontalmente",
    12, VERDE_FRACO)

camadas = [
    (420, 42, "Rotas",
     "recebem a requisição, verificam a autorização e delegam — 47 rotas, "
     "sem regra de negócio", BRANCO, VERDE_LINHA, 1.3),
    (470, 42, "Contratos",
     "validam entrada e saída antes de a regra ser executada (Pydantic)",
     BRANCO, VERDE_LINHA, 1.3),
    (520, 52, "Serviços de domínio",
     "avaliação de parâmetros · compatibilidade entre espécies · dicas · "
     "imagens — independentes de HTTP", VERDE_CLARO, VERDE_BORDA, 1.6),
    (582, 42, "Modelos",
     "mapeiam as tabelas do banco (SQLAlchemy)", BRANCO, VERDE_LINHA, 1.3),
]
for y, alt, titulo, sub, fundo, borda, grossura in camadas:
    caixa(82, y, 776, alt, 6, fundo, borda, grossura)
    txt(100, y + 8, titulo, 12.5, VERDE_TEXTO, negrito=True)
    txt(100, y + 25, sub, 11, VERDE_FRACO)

txt(0, 652, "Fonte única das regras de negócio", 12, VERDE_OK,
    italico=True, centro=470)

# ═══════════ SQL ═══════════
seta(440, 670, 706, dupla=True)
txt(452, 680, "SQL", 11.5, CINZA_SETA)

# ═══════════ 3. DADOS ═══════════
caixa(60, 712, 820, 84, 10, MARROM_FUNDO, MARROM_BORDA)
txt(82, 728, "3. CAMADA DE DADOS", 15, MARROM_TEXTO, negrito=True)
txt(82, 750, "PostgreSQL — 18 tabelas · integridade referencial e restrições "
             "de verificação no próprio esquema", 12, MARROM_FRACO)
txt(82, 771, "Multilocação por linha: cada registro é vinculado ao usuário "
             "proprietário; toda consulta filtra pelo usuário autenticado",
    11.5, MARROM_FRACO)

img.save("figura_arquitetura.png", dpi=(300, 300))
print(f"figura_arquitetura.png gerada: {img.size[0]}x{img.size[1]} px")
