"""
Converte o Markdown do TCC em um .docx já formatado nas normas ABNT.

    python md_para_docx.py AquaSys_TCC.md AquaSys_TCC.docx

Não existe pandoc nem LibreOffice nesta máquina, então a conversão é
feita direto com python-docx.

Formatação aplicada:
  · papel A4 (21 × 29,7 cm);
  · margens superior e esquerda 3 cm, inferior e direita 2 cm;
  · Times New Roman 12, entrelinha 1,5, corpo justificado;
  · recuo de 1,25 cm na primeira linha de cada parágrafo do texto;
  · títulos sem recuo, alinhados à esquerda;
  · legendas de quadros e figuras acima do elemento, fonte acompanhando
    as fontes logo abaixo, em corpo 10 e entrelinha simples;
  · referências alinhadas à esquerda, entrelinha simples e separadas por
    uma linha em branco, conforme a NBR 6023.
"""

import os
import re
import sys

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

FONTE = "Times New Roman"
CORPO = Pt(12)
MENOR = Pt(10)          # legendas de fonte, conteúdo de quadros
ENTRELINHA = 1.5
RECUO = Cm(1.25)        # recuo de primeira linha, NBR 14724

_MARCADORES = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*)")

# Uma legenda começa assim; a fonte, assado.
_LEGENDA = re.compile(r"^\*\*(Quadro|Figura) ")
_FONTE_ELEMENTO = re.compile(r"^Fonte:")


# ═══════════════════════════════════════════════════════
# PÁGINA
# ═══════════════════════════════════════════════════════
def preparar_pagina(doc) -> None:
    for secao in doc.sections:
        secao.orientation = WD_ORIENT.PORTRAIT
        secao.page_width = Cm(21.0)
        secao.page_height = Cm(29.7)
        secao.top_margin = Cm(3.0)
        secao.left_margin = Cm(3.0)
        secao.bottom_margin = Cm(2.0)
        secao.right_margin = Cm(2.0)


def preparar_estilo(doc) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = CORPO
    pf = normal.paragraph_format
    pf.line_spacing = ENTRELINHA
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)


# ═══════════════════════════════════════════════════════
# TEXTO
# ═══════════════════════════════════════════════════════
def escrever(paragrafo, texto: str, tamanho=CORPO, negrito_tudo=False) -> None:
    """Aplica **negrito** e *itálico* dentro do parágrafo."""
    for pedaco in _MARCADORES.split(texto):
        if not pedaco:
            continue
        if pedaco.startswith("**") and pedaco.endswith("**"):
            trecho, negrito, italico = pedaco[2:-2], True, False
        elif pedaco.startswith("*") and pedaco.endswith("*"):
            trecho, negrito, italico = pedaco[1:-1], False, True
        else:
            trecho, negrito, italico = pedaco, False, False

        run = paragrafo.add_run(trecho)
        run.bold = negrito or negrito_tudo
        run.italic = italico
        run.font.name = FONTE
        run.font.size = tamanho


def paragrafo_corpo(doc, texto: str):
    p = doc.add_paragraph()
    escrever(p, texto)
    pf = p.paragraph_format
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.first_line_indent = RECUO
    pf.line_spacing = ENTRELINHA
    pf.space_after = Pt(0)
    return p


def paragrafo_referencia(doc, texto: str):
    """NBR 6023: à esquerda, entrelinha simples, sem recuo."""
    p = doc.add_paragraph()
    escrever(p, texto)
    pf = p.paragraph_format
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.first_line_indent = Cm(0)
    pf.line_spacing = 1.0
    pf.space_after = Pt(12)
    return p


def paragrafo_legenda(doc, texto: str, acima=True):
    p = doc.add_paragraph()
    escrever(p, texto, tamanho=MENOR)
    pf = p.paragraph_format
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.first_line_indent = Cm(0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(12 if acima else 0)
    pf.space_after = Pt(3 if acima else 12)
    return p


def paragrafo_lista(doc, texto: str, numerada=False):
    p = doc.add_paragraph(style="List Number" if numerada else "List Bullet")
    escrever(p, texto)
    pf = p.paragraph_format
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing = ENTRELINHA
    pf.space_after = Pt(0)
    return p


def titulo(doc, texto: str, nivel: int):
    p = doc.add_heading(level=nivel)
    escrever(p, texto, negrito_tudo=True)
    for run in p.runs:
        run.font.name = FONTE
        run.font.size = CORPO          # ABNT: mesmo corpo do texto
        run.font.color.rgb = None
    pf = p.paragraph_format
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.first_line_indent = Cm(0)
    pf.line_spacing = ENTRELINHA
    pf.space_before = Pt(18 if nivel <= 2 else 12)
    pf.space_after = Pt(12 if nivel <= 2 else 6)
    return p


# ═══════════════════════════════════════════════════════
# QUADROS
# ═══════════════════════════════════════════════════════
def celulas(linha: str):
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def e_separador(linha: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:\-|]+\|", linha.strip()))


def montar_quadro(doc, linhas) -> None:
    cabecalho = celulas(linhas[0])
    dados = [celulas(l) for l in linhas[2:]]

    tabela = doc.add_table(rows=1, cols=len(cabecalho))
    tabela.style = "Table Grid"
    tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabela.autofit = True

    def preencher(celula, texto, negrito=False):
        p = celula.paragraphs[0]
        escrever(p, texto, tamanho=MENOR, negrito_tudo=negrito)
        pf = p.paragraph_format
        pf.line_spacing = 1.0
        pf.space_after = Pt(0)
        pf.first_line_indent = Cm(0)

    for celula, texto in zip(tabela.rows[0].cells, cabecalho):
        preencher(celula, texto, negrito=True)

    for linha in dados:
        nova = tabela.add_row().cells
        for celula, texto in zip(nova, linha):
            preencher(celula, texto)


# ═══════════════════════════════════════════════════════
# CONVERSÃO
# ═══════════════════════════════════════════════════════
def converter(entrada: str, saida: str) -> None:
    with open(entrada, encoding="utf-8") as arquivo:
        linhas = arquivo.read().split("\n")

    doc = Document()
    preparar_pagina(doc)
    preparar_estilo(doc)

    nas_referencias = False
    i = 0
    quadros = figuras = 0

    while i < len(linhas):
        despida = linhas[i].strip()

        if not despida or despida == "---":
            i += 1
            continue

        # ─ quadro ─
        if despida.startswith("|") and i + 1 < len(linhas) and e_separador(linhas[i + 1]):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            montar_quadro(doc, bloco)
            quadros += 1
            continue

        # ─ figura ─
        figura = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", despida)
        if figura:
            caminho = figura.group(2)
            if os.path.isfile(caminho):
                doc.add_picture(caminho, width=Cm(15.0))
                p = doc.paragraphs[-1]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.first_line_indent = Cm(0)
                figuras += 1
            else:
                paragrafo_corpo(doc, f"[imagem não encontrada: {caminho}]")
            i += 1
            continue

        # ─ título ─
        if despida.startswith("#"):
            nivel = len(despida) - len(despida.lstrip("#"))
            rotulo = despida[nivel:].strip()
            nas_referencias = rotulo.startswith("Referências")
            titulo(doc, rotulo, min(nivel, 4))
            i += 1
            continue

        # ─ legenda de quadro ou figura, e a fonte logo abaixo ─
        if _LEGENDA.match(despida):
            paragrafo_legenda(doc, despida, acima=True)
            i += 1
            continue
        if _FONTE_ELEMENTO.match(despida):
            paragrafo_legenda(doc, despida, acima=False)
            i += 1
            continue

        # ─ listas ─
        if re.match(r"^[-*] ", despida):
            paragrafo_lista(doc, despida[2:])
            i += 1
            continue
        if re.match(r"^\d+\. ", despida):
            paragrafo_lista(doc, re.sub(r"^\d+\. ", "", despida), numerada=True)
            i += 1
            continue

        # ─ parágrafo comum ─
        if nas_referencias:
            paragrafo_referencia(doc, despida)
        else:
            paragrafo_corpo(doc, despida)
        i += 1

    doc.save(saida)
    print(f"gerado: {saida}")
    print(f"  A4, margens 3/3/2/2 cm · Times New Roman 12 · entrelinha 1,5")
    print(f"  parágrafos: {len(doc.paragraphs)} | quadros: {quadros} | figuras: {figuras}")


if __name__ == "__main__":
    converter(sys.argv[1], sys.argv[2])
