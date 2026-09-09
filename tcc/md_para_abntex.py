"""
Converte o TCC do Markdown para abnTeX2, no modelo do Campo Real.

    python md_para_abntex.py AquaSys_TCC.md AquaSys_TCC.tex

Decisões que valem registro:

  · A numeração das seções é do LaTeX, não do texto. Os números que
    existiam nos títulos do Markdown são removidos, e a classe abntex2
    os regenera. Como o mapeamento é um para um, as remissões escritas
    por extenso ("Seção 2.2.4") continuam corretas.

  · O preâmbulo é o do modelo, acrescido de: `graphicx`, `longtable` e
    `array`, necessários para a figura e para os quadros; e `mathptmx`,
    `helvet` e `courier`, que trocam a Latin Modern herdada da memoir
    pela Times New Roman que a NBR 14724 exige. Sem esse último grupo o
    trabalho sai inteiro em Computer Modern, por mais que se declare
    12pt na classe.

  · O texto sai em UTF-8 direto, e não com acentos escapados, já que o
    modelo carrega `inputenc` com utf8. Se o compilador reclamar, o
    caminho é trocar o motor para lualatex ou xelatex.

  · Quadros viram `longtable` solta, e não dentro de `center`: ela já se
    centraliza sozinha, e o `center` só a impediria de quebrar entre
    páginas. Corpo 10 e entrelinha simples dentro das células. A legenda
    e a fonte saem pelos comandos legendaabnt e fonteabnt, declarados
    no preâmbulo. Não se usou o ambiente `quadro` do abntex2 para não
    depender da versão do pacote instalada na plataforma.
"""

import os
import re
import sys

LARGURA_TEXTO = 15.5      # cm úteis entre as margens de 3 e 2 cm

# A Figura 1 sai desenhada em TikZ, dentro do proprio .tex. Para usar um
# desenho feito a mao no lugar, ponha o arquivo na mesma pasta do .tex,
# escreva o nome dele aqui e troque a chave para False. O caminho da
# imagem e' relativo ao .tex, e o editor precisa receber os dois.
FIGURA_EM_TIKZ = True
ARQUIVO_DA_FIGURA = "figura_arquitetura.png"
CM_POR_CARACTERE = 0.20   # largura media de um caractere em Times 10 pt
PISO_MINIMO = 1.0         # nenhuma coluna mais estreita que isto
TETO_DO_PISO = 2.6        # nem uma palavra comprida reserva mais que isto

PREAMBULO = r"""\RequirePackage{silence}
\WarningFilter{babel}{Name 'brazil' is deprecated}
\documentclass[12pt,oneside,a4paper,brazilian]{abntex2}

% Core packages
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usepackage{tikz-cd}
\usepackage{multicol}

% Extra packages for Portuguese and citations
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{csquotes}
\usepackage[alf]{abntex2cite}

% Acrescentados para a figura e para os quadros deste trabalho
\usepackage{graphicx}
\usepackage{longtable}
\usepackage{array}

% ─── Fonte: Times New Roman (NBR 14724) ───────────────────────────
% A abntex2 e' construida sobre a memoir e herda dela a Latin Modern.
% Sem um pacote de fonte no preambulo, o trabalho sai em Computer
% Modern por mais que se peca 12pt na classe. O mathptmx troca texto e
% matematica pela Times; helvet e courier completam as familias sem
% serifa e monoespacada, para que \textsf e \texttt nao voltem a
% Computer Modern no meio da pagina.
\usepackage{mathptmx}
\usepackage[scaled=0.90]{helvet}
\usepackage{courier}

% ─── Margens da NBR 14724 ─────────────────────────────────────────
% 3 cm em cima e a esquerda, 2 cm embaixo e a direita. A abntex2 ja
% adota esses valores, mas declara-los aqui torna a exigencia
% verificavel no proprio arquivo, em vez de depender do padrao da
% versao da classe instalada na plataforma.
\setlrmarginsandblock{3cm}{2cm}{*}
\setulmarginsandblock{3cm}{2cm}{*}
\checkandfixthelayout

% ─── Legenda e fonte de quadros e figuras ─────────────────────────
% NBR 14724: a legenda vem acima do elemento e a fonte logo abaixo,
% ambas centralizadas, em corpo menor e entrelinha simples.
% Corpo 12, e nao 10: no trabalho aprovado a legenda e a fonte saem no
% mesmo tamanho do texto. A legenda vai em redondo e a linha de fonte em
% negrito -- invertido em relacao ao que se esperaria, mas e o que o
% modelo faz, verificado em cinco quadros e figuras dele.
\newcommand{\legendaabnt}[1]{%
  \par\vspace{9pt}%
  \begingroup\centering\normalsize\SingleSpacing #1\par\endgroup
  \vspace{3pt}}
\newcommand{\fonteabnt}[1]{%
  \par\vspace{3pt}%
  \begingroup\centering\normalsize\SingleSpacing\bfseries #1\par\endgroup
  \vspace{9pt}}

% ─── Numeracao das secoes (NBR 6024) ──────────────────────────────
% A abntex2 e uma classe de livro: \section esta um nivel abaixo de
% \chapter. Este trabalho e no formato de artigo e nao usa \chapter
% nenhuma vez, entao o contador de capitulo fica parado em zero e a
% numeracao sai como "0.1 Introducao", "0.2.4 Arquitetura adotada".
% Promove-se a \section a nivel primario. Como nenhum \chapter e
% emitido, o contador de secao nunca e zerado, e a sequencia corre
% direto de 1 a 6 -- o que mantem corretas as remissoes escritas por
% extenso no texto ("Secao 2.2.4").
% O ponto depois do numero da secao primaria -- "1. Introducao" -- e do
% modelo aprovado, e nao da NBR 6024, que o dispensa. Entre os dois vale
% o modelo, porque e contra ele que o trabalho e comparado. As subsecoes
% seguem sem ponto no fim, como no original.
% Cada nivel e escrito por extenso a partir dos contadores, e nao
% derivado do nivel acima: derivar faria a subsecao herdar o ponto e
% sair como "2..1".
\renewcommand{\thesection}{\arabic{section}.}
\renewcommand{\thesubsection}{\arabic{section}.\arabic{subsection}}
\renewcommand{\thesubsubsection}%
  {\arabic{section}.\arabic{subsection}.\arabic{subsubsection}}

% ─── Discricao dos titulos ────────────────────────────────────────
% A abntex2 compoe os titulos em corpo maior e sem serifa. A NBR 14724
% pede o contrario: mesma fonte e mesmo corpo do texto, distinguidos
% so pelo negrito. Os comandos abaixo so sao redefinidos se existirem
% na versao da classe instalada, para que o arquivo nao quebre em
% plataforma com abntex2 mais antiga.
\makeatletter
\newcommand{\aquasysface}[2]{%
  \@ifundefined{#1}{}{\expandafter\renewcommand\csname #1\endcsname{#2}}}
\aquasysface{ABNTEXchapterfont}{\normalfont\bfseries}
\aquasysface{ABNTEXchapterfontsize}{\normalsize}
\aquasysface{ABNTEXsectionfont}{\normalfont\bfseries}
\aquasysface{ABNTEXsectionfontsize}{\normalsize}
\aquasysface{ABNTEXsubsectionfont}{\normalfont\bfseries}
\aquasysface{ABNTEXsubsectionfontsize}{\normalsize}
\aquasysface{ABNTEXsubsubsectionfont}{\normalfont\bfseries}
\aquasysface{ABNTEXsubsubsectionfontsize}{\normalsize}
\makeatother

% Espaco antes e depois do titulo: a NBR 14724 pede uma linha de 1,5,
% que a 12 pt da os 18 pt daqui -- e nao os saltos de 39 pt que a
% classe usava. O valor depois e menor porque o \parskip de 0,2 cm do
% modelo ainda se soma a ele.
% ─── Entrelinha do corpo ──────────────────────────────────────────
% O \OnehalfSpacing da memoir rende 17,9 pt a 12 pt, porque usa o fator
% de 1,24 herdado da tipografia de maquina de escrever. O modelo foi
% feito no Word, cujo "1,5 linhas" da 20,7 pt para Times 12 -- medido no
% PDF dele. Iguala-se ao modelo. O \SingleSpacing continua valendo 14,5
% pt, que e o que resumo, quadros e referencias usam.
\makeatletter
\@ifundefined{setSpacing}{}{\AtBeginDocument{\setSpacing{1.428}}}
\makeatother

\setbeforesecskip{10pt plus 2pt minus 2pt}
\setaftersecskip{12pt plus 1pt minus 1pt}
\setbeforesubsecskip{10pt plus 2pt minus 2pt}
\setaftersubsecskip{12pt plus 1pt minus 1pt}
\setbeforesubsubsecskip{10pt plus 2pt minus 2pt}
\setaftersubsubsecskip{10pt plus 1pt minus 1pt}

% Remissoes em preto: continuam clicaveis na tela e nao saem cinzas
% na impressao, como sairiam as cores padrao do hyperref.
\hypersetup{colorlinks=true, linkcolor=black, citecolor=black,
            urlcolor=black, filecolor=black}

% Paragraphs
% O recuo de primeira linha e o unico separador entre paragrafos, como
% no modelo aprovado e como pede a NBR 14724. O \parskip de 0,2 cm que
% a abntex2 traz por padrao acrescentava 5,7 pt a cada troca.
\setlength{\parindent}{1.25cm}
\setlength{\parskip}{0pt}

% Folga extra na justificação: sem ela, linhas com termos longos e sem
% ponto de hifenização (URLs das referências, nomes de classe) estouram
% a margem e o LaTeX avisa com Overfull \hbox.
\setlength{\emergencystretch}{3em}
\sloppy

% Permite quebrar URL longa em qualquer ponto, em vez de deixá-la
% transbordar da mancha na lista de referências.
\makeatletter
\g@addto@macro{\UrlBreaks}{\UrlOrds}
\makeatother

\titulo{AquaSys --- aplicativo m\'ovel para gest\~ao de aqu\'arios e apoio \`a manuten\c{c}\~ao profissional em modelo SaaS}
\autor{Weslley Cesar Zampier \and Brenda Lopes Levandoski}
\instituicao{Centro Universit\'ario Campo Real \\
  Rua Comendador Norberto, 1299 -- Santa Cruz -- Guarapuava -- PR -- Brasil \\
  \texttt{\{engs-weslleyzampier@camporeal.edu.br, prof\_brendalevandoski@camporeal.edu.br\}}}
\local{Guarapuava -- PR}
\data{2026}

\begin{document}

% ─── Cabecalho do artigo ──────────────────────────────────────────
% O \maketitle da abntex2 monta a folha de rosto de monografia: titulo
% em 20,7 pt, autores sem vinculo e a data solta -- e descarta o
% \instituicao. Era dai que vinham a marca sobrescrita faltando nos
% autores e a ausencia do Campo Real. O modelo aprovado e um artigo,
% com outro cabecalho. Monta-se a mao, nas medidas tiradas do PDF dele:
% titulo 13 pt negrito, autores 11 pt negrito, vinculo 12 pt redondo.
\begingroup
\SingleSpacing
\setlength{\parindent}{0pt}
\begin{center}
{\bfseries\fontsize{13pt}{22.5pt}\selectfont
 AquaSys --- aplicativo móvel para gestão de aquários e apoio à
 manutenção profissional em modelo SaaS\par}

\vspace{8pt}

{\bfseries\fontsize{11pt}{13.2pt}\selectfont
 Weslley Cesar Zampier\textsuperscript{1},
 Brenda Lopes Levandoski\textsuperscript{1}\par}

\vspace{18pt}

{\fontsize{12pt}{13.8pt}\selectfont
 \textsuperscript{1}Centro Universitário Campo Real\par
 Rua Comendador Norberto, 1299 -- Santa Cruz -- Guarapuava -- PR -- Brasil\par
 \vspace{6pt}
 \{engs-weslleyzampier@camporeal.edu.br,
   prof\_brendalevandoski@camporeal.edu.br\}\par}
\end{center}
\endgroup

\vspace{18pt}
"""

DECLARACAO_IA = r"""
\section*{Declara\c{c}\~ao de Uso de IA}

Durante a elabora\c{c}\~ao deste trabalho foi utilizado o assistente de intelig\^encia
artificial Claude, da Anthropic, nas seguintes atividades: reda\c{c}\~ao e revis\~ao
do texto a partir de conte\'udo, decis\~oes t\'ecnicas e dados fornecidos pelo autor;
apoio \`a implementa\c{c}\~ao do prot\'otipo, incluindo escrita e revis\~ao de c\'odigo;
execu\c{c}\~ao das buscas nas bases bibliogr\'aficas e triagem preliminar dos estudos
retornados no mapeamento sistem\'atico; e verifica\c{c}\~ao de consist\^encia interna
do documento, como remiss\~oes a se\c{c}\~oes, numera\c{c}\~ao de quadros e
correspond\^encia entre cita\c{c}\~oes e refer\^encias.

As decis\~oes de projeto, a arquitetura adotada, a defini\c{c}\~ao do escopo, a
sele\c{c}\~ao final dos estudos e a leitura integral das obras referenciadas s\~ao de
responsabilidade do autor. Os dados quantitativos apresentados --- retornos das buscas,
m\'etricas do prot\'otipo e resultados dos testes automatizados --- foram obtidos por
execu\c{c}\~ao direta e verificados pelo autor.
"""


FIGURA_ARQUITETURA = r"""\begin{center}
% As cores precisam existir antes das opcoes do tikzpicture: os
% estilos sao expandidos ja na abertura do ambiente, e uma cor
% definida dentro do desenho chegaria tarde demais para o estilo
% `seta`, que usa corcinza.
\definecolor{corcinza}{RGB}{90,107,123}
\definecolor{azulfundo}{RGB}{244,249,253}
\definecolor{azulborda}{RGB}{90,143,191}
\definecolor{azultexto}{RGB}{31,58,82}
\definecolor{azulfraco}{RGB}{74,96,118}
\definecolor{azulclaro}{RGB}{227,239,248}
\definecolor{azullinha}{RGB}{143,180,212}
\definecolor{verdefundo}{RGB}{242,250,246}
\definecolor{verdeborda}{RGB}{62,142,107}
\definecolor{verdetexto}{RGB}{20,80,58}
\definecolor{verdefraco}{RGB}{47,107,82}
\definecolor{verdeclaro}{RGB}{230,245,238}
\definecolor{verdelinha}{RGB}{127,191,163}
\definecolor{ambarfundo}{RGB}{251,247,236}
\definecolor{ambarborda}{RGB}{217,185,121}
\definecolor{ambartexto}{RGB}{122,91,18}
\definecolor{marromfundo}{RGB}{250,246,242}
\definecolor{marromborda}{RGB}{176,122,74}
\definecolor{marromtexto}{RGB}{107,63,22}
\definecolor{vermelho}{RGB}{176,58,46}
\definecolor{verdeok}{RGB}{27,122,75}

\begin{tikzpicture}[
  x=1cm, y=1cm, line width=0.5pt,
  camada/.style   ={draw, line width=1pt, rounded corners=3pt},
  bloco/.style    ={draw, fill=white, rounded corners=2pt},
  faixa/.style    ={draw, fill=white, rounded corners=2pt},
  seta/.style     ={<->, >=stealth, line width=0.9pt, corcinza}]
% ─── usuários ───
\draw[bloco, draw=azullinha, fill=azulclaro, rounded corners=8pt]
  (2.6,0) rectangle (7.0,-1.0);
\node[align=center, text=azultexto, font=\footnotesize\bfseries]
  at (4.8,-0.35) {Loja assinante};
\node[align=center, text=azulfraco, font=\scriptsize] at (4.8,-0.72) {perfil CNPJ};
\draw[bloco, draw=azullinha, fill=azulclaro, rounded corners=8pt]
  (8.0,0) rectangle (12.4,-1.0);
\node[align=center, text=azultexto, font=\footnotesize\bfseries]
  at (10.2,-0.35) {Cliente da loja};
\node[align=center, text=azulfraco, font=\scriptsize] at (10.2,-0.72) {perfil CPF};
\draw[->, >=stealth, corcinza] (4.8,-1.05) -- (6.3,-1.9);
\draw[->, >=stealth, corcinza] (10.2,-1.05) -- (8.7,-1.9);

% ─── 1. apresentação ───
\draw[camada, draw=azulborda, fill=azulfundo] (0,-2.0) rectangle (15,-6.7);
\node[anchor=west, text=azultexto, font=\footnotesize\bfseries]
  at (0.4,-2.45) {1. CAMADA DE APRESENTAÇÃO};
\node[anchor=west, text=azulfraco, font=\scriptsize]
  at (0.4,-2.95) {Flutter (Dart), executa no aparelho do usuário; base de
                  código única para Android e iOS};
\draw[faixa, draw=azullinha] (0.40,-3.35) rectangle (3.80,-4.55);
\node[align=center, text=azultexto, font=\scriptsize\bfseries] at (2.10,-3.70) {Telas};
\node[align=center, text=azulfraco, font=\tiny, text width=3.1cm]
  at (2.10,-4.15) {exibem o que a API decidiu};
\draw[faixa, draw=azullinha] (4.07,-3.35) rectangle (7.47,-4.55);
\node[align=center, text=azultexto, font=\scriptsize\bfseries] at (5.77,-3.70) {Widgets};
\node[align=center, text=azulfraco, font=\tiny, text width=3.1cm]
  at (5.77,-4.15) {componentes reutilizáveis};
\draw[faixa, draw=azullinha] (7.74,-3.35) rectangle (11.14,-4.55);
\node[align=center, text=azultexto, font=\scriptsize\bfseries] at (9.44,-3.70) {Serviços};
\node[align=center, text=azulfraco, font=\tiny, text width=3.1cm]
  at (9.44,-4.15) {acesso à API por domínio};
\draw[faixa, draw=azullinha] (11.41,-3.35) rectangle (14.81,-4.55);
\node[align=center, text=azultexto, font=\scriptsize\bfseries] at (13.11,-3.70) {Tema};
\node[align=center, text=azulfraco, font=\tiny, text width=3.1cm]
  at (13.11,-4.15) {cores, tipografia, espaçamento};
\draw[faixa, draw=azulborda, fill=azulclaro] (0.4,-4.90) rectangle (14.6,-5.60);
\node[align=center, text=azultexto, font=\scriptsize\bfseries] at (7.5,-5.25)
  {Api, cliente HTTP único: monta a requisição, anexa o token, traduz o erro};
\node[align=center, text=vermelho, font=\scriptsize\itshape] at (7.5,-6.15)
  {Não contém regra de negócio};

% ─── comunicação ───
\draw[seta] (2.5,-6.7) -- (2.5,-7.8);
\draw[faixa, draw=ambarborda, fill=ambarfundo] (3.5,-6.80) rectangle (15,-7.70);
\node[align=center, text=ambartexto, font=\scriptsize\bfseries] at (9.25,-7.08)
  {API REST sobre HTTPS, com token JWT em cada requisição};
\node[align=center, text=ambartexto, font=\tiny] at (9.25,-7.45)
  {requisições autocontidas: o servidor não retém estado de sessão};

% ─── 2. lógica de negócio ───
\draw[camada, draw=verdeborda, fill=verdefundo] (0,-7.9) rectangle (15,-13.9);
\node[anchor=west, text=verdetexto, font=\footnotesize\bfseries]
  at (0.4,-8.35) {2. CAMADA DE LÓGICA DE NEGÓCIO};
\node[anchor=west, text=verdefraco, font=\scriptsize]
  at (0.4,-8.85) {FastAPI (Python), monolito modular, replicável horizontalmente};
\draw[faixa, draw=verdelinha] (0.4,-9.25) rectangle (14.6,-10.05);
\node[anchor=west, text=verdetexto, font=\scriptsize\bfseries] at (0.7,-9.50) {Rotas};
\node[anchor=west, text=verdefraco, font=\tiny] at (0.7,-9.85)
  {recebem a requisição, verificam a autorização e delegam; 47 rotas, sem regra de negócio};
\draw[faixa, draw=verdelinha] (0.4,-10.20) rectangle (14.6,-11.00);
\node[anchor=west, text=verdetexto, font=\scriptsize\bfseries] at (0.7,-10.45) {Contratos};
\node[anchor=west, text=verdefraco, font=\tiny] at (0.7,-10.80)
  {validam entrada e saída antes de a regra ser executada (Pydantic)};
\draw[faixa, draw=verdeborda, fill=verdeclaro, line width=0.8pt]
  (0.4,-11.15) rectangle (14.6,-12.05);
\node[anchor=west, text=verdetexto, font=\scriptsize\bfseries] at (0.7,-11.42)
  {Serviços de domínio};
\node[anchor=west, text=verdefraco, font=\tiny] at (0.7,-11.80)
  {avaliação de parâmetros, compatibilidade entre espécies, dicas e imagens; independentes de HTTP};
\draw[faixa, draw=verdelinha] (0.4,-12.20) rectangle (14.6,-13.00);
\node[anchor=west, text=verdetexto, font=\scriptsize\bfseries] at (0.7,-12.45) {Modelos};
\node[anchor=west, text=verdefraco, font=\tiny] at (0.7,-12.80)
  {mapeiam as tabelas do banco (SQLAlchemy)};
\node[align=center, text=verdeok, font=\scriptsize\itshape] at (7.5,-13.45)
  {Fonte única das regras de negócio};

% ─── SQL ───
\draw[seta] (2.5,-13.9) -- (2.5,-14.7);
\node[anchor=west, text=corcinza, font=\scriptsize] at (2.8,-14.30) {SQL};

% ─── 3. dados ───
\draw[camada, draw=marromborda, fill=marromfundo] (0,-14.8) rectangle (15,-16.7);
\node[anchor=west, text=marromtexto, font=\footnotesize\bfseries]
  at (0.4,-15.25) {3. CAMADA DE DADOS};
\node[anchor=west, text=marromtexto, font=\scriptsize] at (0.4,-15.78)
  {PostgreSQL, 18 tabelas, com integridade referencial e restrições de
   verificação no próprio esquema};
\node[anchor=west, text=marromtexto, font=\scriptsize] at (0.4,-16.28)
  {Multilocação por linha: cada registro é vinculado ao usuário
   proprietário, e toda consulta filtra pelo autenticado};
\end{tikzpicture}
\end{center}"""


# ═══════════════════════════════════════════════════════
# ESCAPE
# ═══════════════════════════════════════════════════════
_SIMBOLOS = {
    "—": "---", "–": "--", "…": r"\ldots{}",
    "“": "``", "”": "''", "‘": "`", "’": "'",
    "₀": r"\textsubscript{0}", "₂": r"\textsubscript{2}",
    "₃": r"\textsubscript{3}", "⁻": r"\textsuperscript{-}",
    "º": r"\textordmasculine{}", "ª": r"\textordfeminine{}",
    "×": r"$\times$", "·": r"$\cdot$", "≤": r"$\leq$", "≥": r"$\geq$",
    "¹": r"\textsuperscript{1}",
}


_NEGRITO = re.compile(r"\*\*(.+?)\*\*")


def sem_negrito(t: str) -> str:
    """Descarta a marcacao de negrito, preservando o texto.

    O negrito de enfase nao existe no modelo aprovado, e a NBR 14724 nao
    o prescreve em lugar nenhum do corpo. Vale para o texto corrido, para
    os itens de lista e para as celulas dos quadros.
    """
    return _NEGRITO.sub(r"\1", t)


def negrito_em_italico(t: str) -> str:
    """Troca negrito por italico nas referencias.

    A NBR 6023 exige destaque no titulo da obra, e admite negrito,
    italico ou sublinhado desde que o mesmo recurso seja usado em toda a
    lista. O modelo aprovado destaca em italico; segue-se ele.
    """
    return _NEGRITO.sub(r"*\1*", t)


def inline(t: str) -> str:
    """Aplica negrito e itálico antes de escapar, para não perder a marcação."""
    t = re.sub(r"\*\*(.+?)\*\*", lambda m: "\x01" + m.group(1) + "\x02", t)
    t = re.sub(r"\*([^*]+?)\*", lambda m: "\x03" + m.group(1) + "\x04", t)

    guardadas = []

    def guardar(mo):
        guardadas.append(mo.group(0))
        return f"\x05{len(guardadas) - 1}\x06"

    t = re.sub(r"https?://[^\s)>,;]+", guardar, t)   # URL escapa depois, em \url

    # A ordem importa, e inverter custou um erro de compilação: alguns
    # símbolos são traduzidos para modo matemático ($\times$), e escapar
    # o cifrão depois disso o transformava em \$\times\$, que o LaTeX
    # recusa. Escapa-se primeiro o que veio do texto; só então entram as
    # traduções, que já saem prontas.
    for de, para in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                     ("_", r"\_")]:
        t = t.replace(de, para)
    for de, para in _SIMBOLOS.items():
        t = t.replace(de, para)

    t = t.replace("\x01", r"\textbf{").replace("\x02", "}")
    t = t.replace("\x03", r"\textit{").replace("\x04", "}")

    def repor(mo):
        return r"\url{" + guardadas[int(mo.group(1))].rstrip(".") + "}"

    return re.sub(r"\x05(\d+)\x06", repor, t)


# ═══════════════════════════════════════════════════════
# LEITURA DO MARKDOWN
# ═══════════════════════════════════════════════════════
def blocos(caminho):
    linhas = open(caminho, encoding="utf-8").read().split("\n")
    i = 0
    while i < len(linhas):
        crua = linhas[i].strip()

        if not crua or crua == "---":
            i += 1
            continue

        if crua.startswith("|") and i + 1 < len(linhas) and \
           re.fullmatch(r"\|[\s:\-|]+\|", linhas[i + 1].strip()):
            tab = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                tab.append([c.strip() for c in linhas[i].strip().strip("|").split("|")])
                i += 1
            del tab[1]
            yield "quadro", tab
            continue

        fig = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", crua)
        if fig:
            yield "figura", fig.group(2)
            i += 1
            continue

        if crua.startswith("#"):
            n = len(crua) - len(crua.lstrip("#"))
            yield "titulo", (n, crua[n:].strip())
            i += 1
            continue

        if re.match(r"^[-*] ", crua):
            yield "item", crua[2:]
            i += 1
            continue
        if re.match(r"^\d+\. ", crua):
            yield "item_num", re.sub(r"^\d+\. ", "", crua)
            i += 1
            continue

        yield "paragrafo", crua
        i += 1


def _palavras(celula: str):
    """Palavras da celula, sem a marcacao do Markdown.

    O que interessa aqui e a largura que o texto vai ocupar; asteriscos
    de negrito e italico nao chegam ao PDF e nao devem contar.
    """
    return re.findall(r"[^\s*_`|]+", celula) or [""]


def larguras(tabela):
    """
    Distribui a largura entre as colunas conforme o conteudo.

    Duas restricoes se somam. A primeira e a mancha: o `p{}` declara so a
    area de texto, e cada coluna ainda gasta dois `tabcolsep` de respiro
    mais a espessura do filete. Sem descontar isso a soma estoura a
    margem -- aconteceu na primeira geracao, com tres colunas somando
    16,5 cm num texto de 15,5 cm.

    A segunda e a palavra mais longa. Distribuir so pela media do
    conteudo levava colunas de rotulo curto ao piso de 1,1 cm, estreito
    demais para o proprio cabecalho: "Dimensao" saia quebrado no meio.
    Cada coluna passa a ter piso proprio, do tamanho da maior palavra que
    precisa caber, com teto para que uma unica palavra comprida nao
    engula a tabela.
    """
    n = len(tabela[0])
    respiro = n * 0.45 + 0.05          # 2 x tabcolsep + filete, por coluna
    disponivel = LARGURA_TEXTO - respiro

    medias, pisos = [], []
    for c in range(n):
        celulas = [linha[c] for linha in tabela if c < len(linha)]
        tam = [len(x) for x in celulas]
        medias.append(max(sum(tam) / len(tam), 4))
        maior = max(len(p) for cel in celulas for p in _palavras(cel))
        pisos.append(min(TETO_DO_PISO, max(PISO_MINIMO, CM_POR_CARACTERE * maior)))

    # se os pisos ja nao cabem, encolhe todos na mesma proporcao
    if sum(pisos) > disponivel:
        fator = disponivel / sum(pisos)
        pisos = [v * fator for v in pisos]

    bruto = [max(disponivel * v / sum(medias), p) for v, p in zip(medias, pisos)]
    # o piso pode ter inflado o total; devolve o excedente a quem tem folga
    excedente = sum(bruto) - disponivel
    if excedente > 0:
        folgadas = [i for i, v in enumerate(bruto) if v > pisos[i] + 0.01]
        sobra = sum(bruto[i] - pisos[i] for i in folgadas)
        if sobra > 0:
            for i in folgadas:
                bruto[i] -= excedente * (bruto[i] - pisos[i]) / sobra
    return bruto


# ═══════════════════════════════════════════════════════
# CONVERSÃO
# ═══════════════════════════════════════════════════════
NIVEL = {2: "section", 3: "subsection", 4: "subsubsection"}


def converter(origem, destino):
    saida = [PREAMBULO]
    lista = None
    estado = "inicio"        # inicio | resumo | abstract | corpo | referencias
    resumo, abstract = [], []
    n_quadros = n_figuras = 0

    def fechar_lista():
        nonlocal lista
        if lista:
            saida.append(f"\\end{{{lista}}}")
            lista = None

    for tipo, dado in blocos(origem):

        # O título, os autores e a afiliação do Markdown são descartados:
        # o comando de titulo do abntex2 ja os monta pelo preambulo.
        if estado == "inicio" and tipo != "titulo":
            continue

        # ── listas ──
        if tipo in ("item", "item_num"):
            amb = "itemize" if tipo == "item" else "enumerate"
            if lista != amb:
                fechar_lista()
                saida.append(f"\\begin{{{amb}}}")
                lista = amb
            saida.append(f"  \\item {inline(sem_negrito(dado))}")
            continue
        fechar_lista()

        # ── títulos ──
        if tipo == "titulo":
            nivel, texto = dado

            if texto == "Resumo":
                estado = "resumo"
                continue
            if texto == "Abstract":
                estado = "abstract"
                continue

            # O título do trabalho, que abre o Markdown, é descartado:
            # quem compõe o cabeçalho é o bloco montado no preâmbulo.
            # Com ele saem os autores e a afiliação, que vêm logo abaixo
            # em parágrafos soltos e são descartados pelo `continue` do
            # topo do laço enquanto o estado for "inicio".
            if nivel == 1:
                continue

            # Quem encerra a capa é o primeiro título de seção, e não o
            # título "Resumo": sem essa distinção, um documento sem
            # resumo perdia o corpo inteiro, e um documento cujo estado
            # saísse cedo demais publicava a folha de rosto do Markdown.
            if estado == "inicio":
                estado = "corpo"
                # sem `continue`: este título é o da Introdução e precisa
                # ser emitido pelos ramos abaixo

            # Basta ter passado pelos títulos: o bloco sai mesmo vazio,
            # porque o autor quer a estrutura pronta e o texto depois.
            if estado in ("resumo", "abstract"):
                # fecha o bloco de resumo antes do primeiro título de seção
                # O ambiente `abstract` da memoir centraliza o titulo e o
                # compoe em corpo menor. No modelo aprovado "Resumo" e
                # "Abstract" sao negrito 12 pt encostados na margem
                # esquerda, com o texto em entrelinha simples e sem recuo.
                saida.append(r"\begingroup\SingleSpacing")
                saida.append(r"\setlength{\parindent}{0pt}")
                saida.append(r"\noindent\textbf{Resumo}\par\vspace{6pt}")
                saida += resumo
                # O \par fecha a linha de Palavras-chave. Sem ele o
                # rotulo Abstract sai grudado no fim dela.
                saida.append(r"\par\vspace{12pt}")
                saida.append(r"\noindent\textbf{Abstract}\par\vspace{6pt}")
                saida += abstract
                saida.append(r"\endgroup")
                estado = "corpo"

            rotulo = re.sub(r"^\d+(\.\d+)*\.?\s*", "", texto)   # o LaTeX numera
            antes, estado = estado, ("referencias"
                                     if rotulo.startswith("Referências")
                                     else "corpo")

            # A lista de referencias corre dentro de um grupo proprio, com
            # a formatacao da NBR 6023. Ele abre no titulo Referencias e
            # fecha no titulo seguinte, que e o primeiro apendice.
            if antes == "referencias" and estado != "referencias":
                saida.append(r"\endgroup")

            if rotulo.startswith("Referências") or rotulo.startswith("Apêndice"):
                saida.append(f"\n\\section*{{{inline(rotulo)}}}")
            elif nivel == 3 and estado == "corpo" and rotulo.startswith(("A.", "B.")):
                saida.append(f"\n\\subsection*{{{inline(rotulo)}}}")
            else:
                saida.append(f"\n\\{NIVEL.get(nivel, 'subsubsection')}{{{inline(rotulo)}}}")

            if estado == "referencias":
                # Entrada alinhada a esquerda, entrelinha simples dentro
                # da entrada e um espaco de 12 pt entre elas.
                saida.append(r"\begingroup\SingleSpacing\raggedright")
                saida.append(r"\setlength{\parindent}{0pt}")
                saida.append(r"\setlength{\parskip}{12pt}")
            continue

        # ── quadro ──
        if tipo == "quadro":
            cab, *corpo = dado
            larg = larguras(dado)
            # `\raggedright` em vez do padrão justificado: numa coluna
            # estreita o LaTeX estica os espaços até o limite e emite
            # centenas de avisos de Underfull. Texto de tabela não precisa
            # de margem alinhada; o `\arraybackslash` devolve ao `\\` o
            # sentido de fim de linha, que o `\raggedright` sobrescreve.
            colunas = "|" + "|".join(
                f">{{\\raggedright\\arraybackslash}}p{{{v:.1f}cm}}" for v in larg
            ) + "|"
            # A longtable NAO vai dentro de `center`. Ela quebra entre
            # paginas por conta propria, e o `center` a torna um bloco
            # indivisivel, alem de somar \topsep acima e abaixo --
            # origem de boa parte dos avisos de espacamento. Centralizar
            # ja e o padrao dela (\LTleft e \LTright valem \fill);
            # o que se faz aqui e zerar a folga vertical e trocar o corpo.
            #
            # Corpo 10 e entrelinha simples em todos os quadros: a NBR
            # 14724 admite fonte menor em ilustracoes, e a entrelinha de
            # 1,5 do texto deixaria cada celula alta demais.
            saida.append(r"{\footnotesize\SingleSpacing")
            # Respiro nas celulas: sem ele o texto encosta no filete e o
            # quadro fica com cara de planilha apertada. O extrarowheight
            # abre acima da linha; os 2 pt no fim de cada linha abrem
            # abaixo, antes do filete seguinte.
            saida.append(r"\setlength{\LTpre}{0pt}\setlength{\LTpost}{0pt}")
            saida.append(r"\setlength{\extrarowheight}{3pt}")
            saida.append(f"\\begin{{longtable}}{{{colunas}}}")
            saida.append(r"\hline")
            # O cabecalho do quadro sai em negrito, como no modelo; as
            # celulas, nao. O sem_negrito evita dobrar a marcacao caso
            # a celula do Markdown ja venha com asteriscos.
            saida.append(" & ".join(f"\\textbf{{{inline(sem_negrito(c))}}}" for c in cab) +
                         r" \\[2pt] \hline \endhead")
            for linha in corpo:
                celulas = [inline(sem_negrito(c)) for c in linha] + [""] * (len(cab) - len(linha))
                saida.append(" & ".join(celulas[: len(cab)]) + r" \\[2pt] \hline")
            saida.append(r"\end{longtable}}")
            n_quadros += 1
            continue

        # ── figura ──
        # O diagrama vai desenhado em TikZ, e nao como imagem externa: o
        # PNG dependia de ser enviado ao editor junto com o .tex, e o PDF
        # compilado veio com zero imagens. Em TikZ o desenho viaja dentro
        # do arquivo.
        if tipo == "figura":
            if FIGURA_EM_TIKZ:
                saida.append(FIGURA_ARQUITETURA)
            else:
                saida.append(r"\begin{center}")
                saida.append(f"\\includegraphics[width=\\textwidth]"
                             f"{{{ARQUIVO_DA_FIGURA}}}")
                saida.append(r"\end{center}")
            n_figuras += 1
            continue

        # ── parágrafos ──
        # Negrito so sobrevive onde o modelo aprovado o usa. No resumo e
        # no abstract isso vale pelos rotulos "Palavras-chave:" e
        # "Keywords:"; nas referencias o destaque do titulo da obra passa
        # a italico; no resto do corpo o negrito simplesmente cai.
        if estado == "referencias":
            texto = inline(negrito_em_italico(dado))
        elif estado in ("resumo", "abstract"):
            texto = inline(dado)
        else:
            texto = inline(sem_negrito(dado))

        if estado == "resumo":
            if dado.startswith("**Palavras-chave:**"):
                resumo.append(r"\medskip" + "\n" + r"\noindent " + texto)
            else:
                resumo.append(texto + "\n")
            continue
        if estado == "abstract":
            if dado.startswith("**Keywords:**"):
                abstract.append(r"\medskip" + "\n" + r"\noindent " + texto)
            else:
                abstract.append(texto + "\n")
            continue

        if estado == "referencias":
            saida.append(texto + "\n")
            continue

        # Legenda acima do elemento e fonte logo abaixo, pelos comandos
        # declarados no preambulo: centralizadas, corpo 10, entrelinha
        # simples. Antes saiam como paragrafo comum, herdando o recuo de
        # 1,25 cm e a entrelinha de 1,5 do corpo do texto.
        if re.match(r"^\*\*(Quadro|Figura) ", dado):
            # A legenda sai em redondo no modelo. O negrito que a envolve
            # no Markdown e so marcacao de leitura da fonte, e nao deve
            # chegar ao PDF; o italico interno de "Strings" continua.
            saida.append(r"\legendaabnt{" + inline(dado.strip("*")) + "}")
        elif dado.startswith("Fonte:"):
            saida.append(r"\fonteabnt{" + texto + "}")
        else:
            saida.append(texto + "\n")

    fechar_lista()

    # a declaração exigida pelo modelo entra antes das referências
    corpo_final = "\n".join(saida)
    marca = "\n\\section*{Refer"
    if marca in corpo_final:
        i = corpo_final.index(marca)
        corpo_final = corpo_final[:i] + "\n" + DECLARACAO_IA + corpo_final[i:]

    corpo_final += "\n\n\\end{document}\n"
    open(destino, "w", encoding="utf-8").write(corpo_final)

    print(f"gerado: {destino}")
    print(f"  quadros: {n_quadros} | figuras: {n_figuras}")
    print(f"  linhas:  {corpo_final.count(chr(10))}")


if __name__ == "__main__":
    converter(sys.argv[1], sys.argv[2])
