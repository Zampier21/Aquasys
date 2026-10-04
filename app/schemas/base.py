"""Base dos contratos de entrada.

O padrão do Pydantic é descartar em silêncio o campo que o modelo não
declara. Numa rota que grava, isso é o começo da atribuição em massa:
o cliente manda `{"nome": "x", "tipo": "dono", "plano": "ilimitado"}`,
o modelo ignora os dois últimos hoje, e no dia em que alguém declarar
um campo com esse nome a requisição antiga passa a escrevê-lo.

Recusar o campo desconhecido fecha essa porta antes de ela existir, e
de quebra transforma erro de digitação do aplicativo em 422 na hora do
teste, em vez de em campo que nunca chegou.

As respostas seguem sem isto de propósito: elas são montadas por nós, e
o risco ali é o oposto — devolver campo demais, que se resolve
declarando só o que a tela precisa.
"""

from pydantic import BaseModel, ConfigDict


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
