"""
Converte o Markdown do TCC em um .docx formatado, pronto para o Google Docs.

    python md_para_docx.py AquaSys_TCC.md AquaSys_TCC.docx

A referencia de formatacao e' a mesma do gerador LaTeX: o artigo aprovado
com nota 10, medido no PDF. O que sai daqui deve ser indistinguivel do que
sai de la', com as diferencas que o formato impoe.

  . A4, margens 3 cm em cima e a esquerda, 2 cm embaixo e a direita;
  . Times New Roman 12, entrelinha 1,5, corpo justificado, recuo de 1,25 cm;
  . cabecalho do artigo: titulo 13 pt negrito, autores 11 pt negrito com o
    indicador de vinculo, afiliacao e enderecos 12 pt, tudo centralizado;
  . secao primaria com ponto ("1. Introducao") e subsecao sem ele ("2.1 ...");
  . sem negrito no corpo -- so em titulo, cabecalho de quadro e linha "Fonte:";
  . legenda de quadro e figura acima do elemento, 12 pt redondo centralizado;
    linha "Fonte:" abaixo, 12 pt negrito centralizado;
  . celulas de quadro em 10 pt com entrelinha simples;
  . referencias a esquerda, entrelinha simples, separadas por uma linha;
  . notas de rodape de verdade, numeradas pelo Word e pelo Google Docs.

A nota de rodape e' montada a mao. O python-docx nao tem API para ela: e'
preciso criar a parte word/footnotes.xml, ligar o documento a ela e inserir
o w:footnoteReference no proprio XML do paragrafo.
"""

import os
import re
import sys

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONTE = "Times New Roman"
CORPO = Pt(12)
MIUDO = Pt(10)          # celulas de quadro e texto da nota de rodape
TITULO_ARTIGO = Pt(13)
AUTORES = Pt(11)
ENTRELINHA = 1.5
RECUO = Cm(1.25)

_MARCADORES = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*)")
_NEGRITO = re.compile(r"\*\*(.+?)\*\*")
_NOTA = re.compile(r"\^\[([^\]]+)\]")
_LEGENDA = re.compile(r"^\*\*(Quadro|Figura) ")
_FONTE_ELEMENTO = re.compile(r"^Fonte:")
# Subsecao perde o ponto final do numero; a secao primaria o mantem.
_NUMERO_SUB = re.compile(r"^(\d+(?:\.\d+)+)\.(\s)")

DECLARACAO_IA = [
    "Durante a elaboração deste trabalho foi utilizado o assistente de "
    "inteligência artificial Claude, da Anthropic, nas seguintes atividades: "
    "redação e revisão do texto a partir de conteúdo, decisões técnicas e "
    "dados fornecidos pelo autor; apoio à implementação do protótipo, "
    "incluindo escrita e revisão de código; execução das buscas nas bases "
    "bibliográficas e triagem preliminar dos estudos retornados no mapeamento "
    "sistemático; e verificação de consistência interna do documento, como "
    "remissões a seções, numeração de quadros e correspondência entre "
    "citações e referências.",
    "As decisões de projeto, a arquitetura adotada, a definição do escopo, a "
    "seleção final dos estudos e a leitura integral das obras referenciadas "
    "são de responsabilidade do autor. Os dados quantitativos apresentados, "
    "que são os retornos das buscas, as métricas do protótipo e os resultados "
    "dos testes automatizados, foram obtidos por execução direta e "
    "verificados pelo autor.",
]


# ═══════════════════════════════════════════════════════
# NOTAS DE RODAPÉ
# ═══════════════════════════════════════════════════════
# O separador e o separador de continuação são exigidos pelo formato: sem
# eles o Word reclama do arquivo. Os dois primeiros identificadores ficam
# reservados para eles, e as notas do texto começam em 2.
_ABERTURA_NOTAS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml'
    '/2006/main">'
    '<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:spacing '
    'w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:separator/>'
    '</w:r></w:p></w:footnote>'
    '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr>'
    '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r>'
    '<w:continuationSeparator/></w:r></w:p></w:footnote>'
)

_TIPO_NOTAS = ("application/vnd.openxmlformats-officedocument"
               ".wordprocessingml.footnotes+xml")


def _escapar(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Notas:
    """Acumula as notas e escreve a parte footnotes.xml no fim."""

    def __init__(self):
        self.textos = []

    def marcar(self, paragrafo, texto):
        """Põe a chamada da nota no fim do parágrafo e guarda o texto dela."""
        self.textos.append(texto)
        ident = len(self.textos) + 1        # 0 e 1 estão reservados
        run = paragrafo.add_run()
        run.font.name = FONTE
        run.font.size = CORPO
        run.font.superscript = True
        marca = run._r.makeelement(qn("w:footnoteReference"), {})
        marca.set(qn("w:id"), str(ident))
        run._r.append(marca)

    def gravar(self, doc):
        if not self.textos:
            return
        partes = [_ABERTURA_NOTAS]
        for i, texto in enumerate(self.textos, start=2):
            partes.append(
                '<w:footnote w:id="%d"><w:p><w:pPr><w:spacing w:after="0" '
                'w:line="240" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr>'
                '<w:r><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s"/>'
                '<w:sz w:val="20"/><w:vertAlign w:val="superscript"/></w:rPr>'
                '<w:footnoteRef/></w:r>'
                '<w:r><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s"/>'
                '<w:sz w:val="20"/></w:rPr>'
                '<w:t xml:space="preserve"> %s</w:t></w:r>'
                '</w:p></w:footnote>'
                % (i, FONTE, FONTE, FONTE, FONTE, _escapar(texto)))
        partes.append("</w:footnotes>")

        parte = Part(PackURI("/word/footnotes.xml"), _TIPO_NOTAS,
                     "".join(partes).encode("utf-8"), doc.part.package)
        doc.part.relate_to(parte, RT.FOOTNOTES)


# ═══════════════════════════════════════════════════════
# PÁGINA E ESTILOS
# ═══════════════════════════════════════════════════════
def preparar_pagina(doc):
    for secao in doc.sections:
        secao.orientation = WD_ORIENT.PORTRAIT
        secao.page_width = Cm(21.0)
        secao.page_height = Cm(29.7)
        secao.top_margin = Cm(3.0)
        secao.left_margin = Cm(3.0)
        secao.bottom_margin = Cm(2.0)
        secao.right_margin = Cm(2.0)


def preparar_estilos(doc):
    normal = doc.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = CORPO
    # O nome da fonte precisa valer também para os caracteres acentuados,
    # que o Word resolve por outro atributo do mesmo elemento.
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
    normal.element.rPr.rFonts.set(qn("w:cs"), FONTE)
    pf = normal.paragraph_format
    pf.line_spacing = ENTRELINHA
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)

    # Os estilos de título continuam sendo usados, e não substituídos por
    # formatação direta, porque são eles que alimentam o sumário e o painel
    # de navegação do Google Docs. Só se apaga o que a ABNT não admite:
    # a cor azul, o corpo aumentado e a fonte sem serifa do padrão.
    for nivel in (1, 2, 3):
        estilo = doc.styles["Heading %d" % nivel]
        estilo.font.name = FONTE
        estilo.font.size = CORPO
        estilo.font.bold = True
        estilo.font.italic = False
        estilo.font.color.rgb = RGBColor(0, 0, 0)
        estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
        estilo.element.rPr.rFonts.set(qn("w:cs"), FONTE)
        pf = estilo.paragraph_format
        pf.line_spacing = ENTRELINHA
        pf.first_line_indent = Cm(0)
        pf.space_before = Pt(10)
        pf.space_after = Pt(12)
        pf.keep_with_next = True


# ═══════════════════════════════════════════════════════
# TEXTO
# ═══════════════════════════════════════════════════════
def escrever(paragrafo, texto, notas=None, tamanho=CORPO, tudo_negrito=False):
    """Aplica itálico e negrito, e converte ^[...] em nota de rodapé.

    A nota sai do texto antes da marcação de ênfase porque o conteúdo dela
    não pertence ao parágrafo: vai para outra parte do arquivo.
    """
    pendentes = []
    if notas is not None:
        def guardar(mo):
            pendentes.append(mo.group(1))
            return "\x00"
        texto = _NOTA.sub(guardar, texto)
    else:
        texto = _NOTA.sub("", texto)

    for pedaco in _MARCADORES.split(texto):
        if not pedaco:
            continue
        if pedaco.startswith("**") and pedaco.endswith("**"):
            trecho, negrito, italico = pedaco[2:-2], True, False
        elif pedaco.startswith("*") and pedaco.endswith("*"):
            trecho, negrito, italico = pedaco[1:-1], False, True
        else:
            trecho, negrito, italico = pedaco, False, False

        # A chamada da nota tem que nascer no lugar exato em que estava a
        # marca, e não no fim do parágrafo: por isso o texto é quebrado nela.
        for i, fatia in enumerate(trecho.split("\x00")):
            if i:
                notas.marcar(paragrafo, pendentes.pop(0))
            if not fatia:
                continue
            run = paragrafo.add_run(fatia)
            run.bold = negrito or tudo_negrito
            run.italic = italico
            run.font.name = FONTE
            run.font.size = tamanho


def _formatar(p, alinhamento, recuo, entrelinha, antes=0, depois=0):
    p.alignment = alinhamento
    pf = p.paragraph_format
    pf.first_line_indent = recuo
    pf.line_spacing = entrelinha
    pf.space_before = Pt(antes)
    pf.space_after = Pt(depois)
    return p


def paragrafo_corpo(doc, texto, notas):
    p = doc.add_paragraph()
    escrever(p, _NEGRITO.sub(r"\1", texto), notas)   # ABNT: sem negrito no corpo
    return _formatar(p, WD_ALIGN_PARAGRAPH.JUSTIFY, RECUO, ENTRELINHA)


def paragrafo_simples(doc, texto, notas, negrito=False, tamanho=CORPO,
                      alinhamento=WD_ALIGN_PARAGRAPH.LEFT, antes=0, depois=0):
    p = doc.add_paragraph()
    escrever(p, texto, notas, tamanho=tamanho, tudo_negrito=negrito)
    return _formatar(p, alinhamento, Cm(0), 1.0, antes, depois)


def paragrafo_referencia(doc, texto):
    """NBR 6023: à esquerda, entrelinha simples, uma linha entre entradas.

    O destaque do título da obra vem marcado como negrito no Markdown e sai
    em itálico, que é o recurso usado no trabalho aprovado.
    """
    p = doc.add_paragraph()
    escrever(p, _NEGRITO.sub(r"*\1*", texto), None)
    return _formatar(p, WD_ALIGN_PARAGRAPH.LEFT, Cm(0), 1.0, depois=12)


def paragrafo_legenda(doc, texto):
    p = doc.add_paragraph()
    escrever(p, texto.strip("*"), None)
    return _formatar(p, WD_ALIGN_PARAGRAPH.CENTER, Cm(0), 1.0, antes=9, depois=3)


def paragrafo_fonte(doc, texto):
    p = doc.add_paragraph()
    escrever(p, texto, None, tudo_negrito=True)
    return _formatar(p, WD_ALIGN_PARAGRAPH.CENTER, Cm(0), 1.0, antes=3, depois=9)


def paragrafo_lista(doc, texto, notas, numerada=False):
    p = doc.add_paragraph(style="List Number" if numerada else "List Bullet")
    escrever(p, _NEGRITO.sub(r"\1", texto), notas)
    return _formatar(p, WD_ALIGN_PARAGRAPH.JUSTIFY, Cm(0), ENTRELINHA)


def titulo(doc, rotulo, nivel, notas):
    p = doc.add_paragraph(style="Heading %d" % min(nivel, 3))
    escrever(p, rotulo, None, tudo_negrito=True)
    return p


# ═══════════════════════════════════════════════════════
# CABEÇALHO DO ARTIGO
# ═══════════════════════════════════════════════════════
def montar_cabecalho(doc, linhas):
    """Título, autores e vínculo, nas medidas do trabalho aprovado."""
    titulo_artigo = linhas[0].lstrip("#").strip()
    resto = [l.strip() for l in linhas[1:] if l.strip()]

    paragrafo_simples(doc, titulo_artigo, None, negrito=True,
                      tamanho=TITULO_ARTIGO,
                      alinhamento=WD_ALIGN_PARAGRAPH.CENTER, depois=8)
    if resto:
        paragrafo_simples(doc, resto[0], None, negrito=True, tamanho=AUTORES,
                          alinhamento=WD_ALIGN_PARAGRAPH.CENTER, depois=18)
    for i, linha in enumerate(resto[1:]):
        ultimo = i == len(resto) - 2
        paragrafo_simples(doc, linha, None,
                          alinhamento=WD_ALIGN_PARAGRAPH.CENTER,
                          antes=6 if linha.startswith("{") else 0,
                          depois=18 if ultimo else 0)


# ═══════════════════════════════════════════════════════
# QUADROS
# ═══════════════════════════════════════════════════════
def celulas(linha):
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def e_separador(linha):
    return bool(re.fullmatch(r"\|[\s:\-|]+\|", linha.strip()))


def montar_quadro(doc, linhas):
    cabecalho = celulas(linhas[0])
    dados = [celulas(l) for l in linhas[2:]]

    tabela = doc.add_table(rows=1, cols=len(cabecalho))
    tabela.style = "Table Grid"
    tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabela.autofit = True

    # Ocupar a largura da mancha e deixar o próprio editor distribuir as
    # colunas: o Word e o Google Docs calculam isso melhor do que uma
    # largura fixa, que estouraria a margem nos quadros de texto longo.
    largura = tabela._tbl.tblPr.makeelement(qn("w:tblW"), {})
    largura.set(qn("w:type"), "pct")
    largura.set(qn("w:w"), "5000")
    tabela._tbl.tblPr.append(largura)

    def preencher(celula, texto, negrito=False):
        p = celula.paragraphs[0]
        escrever(p, _NEGRITO.sub(r"\1", texto), None, tamanho=MIUDO,
                 tudo_negrito=negrito)
        _formatar(p, WD_ALIGN_PARAGRAPH.LEFT, Cm(0), 1.0)

    for celula, texto in zip(tabela.rows[0].cells, cabecalho):
        preencher(celula, texto, negrito=True)
    for linha in dados:
        nova = tabela.add_row().cells
        for celula, texto in zip(nova, linha):
            preencher(celula, texto)


# ═══════════════════════════════════════════════════════
# CONVERSÃO
# ═══════════════════════════════════════════════════════
def converter(entrada, saida):
    base = os.path.dirname(os.path.abspath(entrada))
    linhas = open(entrada, encoding="utf-8").read().split("\n")

    doc = Document()
    preparar_pagina(doc)
    preparar_estilos(doc)
    notas = Notas()

    # O cabeçalho é tudo que vem antes da primeira linha horizontal.
    fim = next(i for i, l in enumerate(linhas) if l.strip() == "---")
    montar_cabecalho(doc, linhas[:fim])

    nas_referencias = False
    declarada = False
    quadros = figuras = 0
    i = fim + 1

    while i < len(linhas):
        despida = linhas[i].strip()

        if not despida or despida == "---":
            i += 1
            continue

        if despida.startswith("|") and i + 1 < len(linhas) \
                and e_separador(linhas[i + 1]):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            montar_quadro(doc, bloco)
            quadros += 1
            continue

        figura = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", despida)
        if figura:
            caminho = os.path.join(base, figura.group(2))
            if os.path.isfile(caminho):
                doc.add_picture(caminho, width=Cm(15.0))
                p = doc.paragraphs[-1]
                _formatar(p, WD_ALIGN_PARAGRAPH.CENTER, Cm(0), 1.0)
                figuras += 1
            else:
                paragrafo_corpo(doc, "[imagem não encontrada: %s]"
                                % figura.group(2), notas)
            i += 1
            continue

        if despida.startswith("#"):
            nivel = len(despida) - len(despida.lstrip("#"))
            rotulo = _NUMERO_SUB.sub(r"\1\2", despida[nivel:].strip())
            # A declaração exigida pelo modelo entra logo antes das
            # referências, como no gerador LaTeX.
            if rotulo.startswith("Referências") and not declarada:
                declarada = True
                titulo(doc, "Declaração de Uso de IA", 1, notas)
                for p in DECLARACAO_IA:
                    paragrafo_corpo(doc, p, notas)
            nas_referencias = rotulo.startswith("Referências")
            titulo(doc, rotulo, max(1, nivel - 1), notas)
            i += 1
            continue

        if _LEGENDA.match(despida):
            paragrafo_legenda(doc, despida)
            i += 1
            continue
        if _FONTE_ELEMENTO.match(despida):
            paragrafo_fonte(doc, despida)
            i += 1
            continue

        if re.match(r"^[-*] ", despida):
            paragrafo_lista(doc, despida[2:], notas)
            i += 1
            continue
        if re.match(r"^\d+\. ", despida):
            paragrafo_lista(doc, re.sub(r"^\d+\. ", "", despida), notas,
                            numerada=True)
            i += 1
            continue

        if nas_referencias:
            paragrafo_referencia(doc, despida)
        else:
            paragrafo_corpo(doc, despida, notas)
        i += 1

    notas.gravar(doc)
    doc.save(saida)

    print("gerado: %s" % saida)
    print("  A4, margens 3/3/2/2 cm . Times New Roman 12 . entrelinha 1,5")
    print("  paragrafos: %d | quadros: %d | figuras: %d | notas: %d"
          % (len(doc.paragraphs), quadros, figuras, len(notas.textos)))


if __name__ == "__main__":
    converter(sys.argv[1], sys.argv[2])
