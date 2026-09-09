"""
Saída de terminal que não quebra no Windows.

O console do Windows costuma vir em cp1252, que não tem "→", "—" nem
emoji. Um `print` com esses caracteres levanta UnicodeEncodeError e
derruba o script no meio — já aconteceu de um seed morrer por causa do
"₂" de CO₂ vindo de um título de vídeo.

Chame `preparar()` na primeira linha de qualquer script de linha de
comando. Em terminal moderno o texto sai correto; em console antigo, o
caractere vira "?" — mas o script termina o trabalho.
"""

import sys


def preparar() -> None:
    """Põe stdout e stderr em UTF-8 tolerante a caractere sem tradução."""
    for fluxo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(fluxo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(encoding="utf-8", errors="replace")
