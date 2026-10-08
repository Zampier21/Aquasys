"""Senha e token: as duas primitivas em que o resto confia.

A biblioteca de JWT é a PyJWT, e não a python-jose. A troca não foi de
gosto: a jose arrasta a `ecdsa` como dependência obrigatória, e a
`ecdsa` carrega uma falha de canal lateral (PYSEC-2026-1325) que os
mantenedores declararam que não vão corrigir. O AquaSys assina com
HS256, que é HMAC e não usa curva elíptica nenhuma, então o pacote
vulnerável estava instalado sem sequer ser chamado. Sair dele custou
este arquivo e deixou a auditoria de dependências limpa.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# O custo é o número de rodadas do bcrypt: cada unidade dobra o tempo.
# Doze é o padrão da passlib e continua sendo a recomendação — some
# dezenas de milissegundos ao login e multiplica por milhares o custo
# de quem tenta quebrar o banco inteiro.
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12
)

# O bcrypt trunca em 72 bytes e, nas versões novas, estoura em vez de
# truncar em silêncio. Recusar antes é mais honesto do que aceitar uma
# senha da qual só parte é conferida.
LIMITE_DE_SENHA_BYTES = 72


class SenhaLonga(ValueError):
    pass


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt de uma senha em texto puro."""
    if len(senha.encode("utf-8")) > LIMITE_DE_SENHA_BYTES:
        raise SenhaLonga(
            f"A senha passa de {LIMITE_DE_SENHA_BYTES} bytes, que é o "
            f"máximo que o bcrypt confere."
        )
    return pwd_context.hash(senha)


def verificar_senha(senha_pura: str, senha_hash: str) -> bool:
    """Verifica se a senha em texto puro bate com o hash armazenado."""
    try:
        return pwd_context.verify(senha_pura, senha_hash)
    except (ValueError, TypeError):
        # Hash gravado em formato que a passlib não reconhece, ou senha
        # longa demais. Nos dois casos a resposta é "não bate", e não
        # um erro 500 que diria ao atacante que achou algo diferente.
        return False


def criar_token(dados: dict) -> str:
    """Gera um JWT com os dados fornecidos e tempo de expiração configurado."""
    agora = datetime.now(timezone.utc)
    payload = dados.copy()
    payload.update({
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    })
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict | None:
    """Decodifica e valida um JWT. Retorna None se inválido ou expirado.

    O algoritmo aceito é passado explicitamente. Sem essa lista, um
    token forjado com `alg: none` ou assinado com um algoritmo mais
    fraco seria aceito — é a falha clássica de implementação de JWT.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError:
        return None


# ═══════════════════════════════════════════════════════
# Token de renovação
# ═══════════════════════════════════════════════════════
# Diferente do token de acesso, este não é um JWT e não carrega nada
# dentro: é um número aleatório. Não precisa carregar, porque o que ele
# significa está na tabela `sessao`, e é lá que se confere. Um JWT aqui
# seria pior — traria de volta justamente o que se quer evitar, que é um
# token válido por si só, impossível de revogar.
BYTES_DO_REFRESH = 32


def criar_refresh() -> tuple[str, str]:
    """Sorteia um token de renovação e devolve (token, hash).

    O token vai para o aparelho e some daqui; o hash é o que se grava.
    Quem puser as mãos no banco encontra só o hash, que não serve para
    renovar sessão nenhuma.
    """
    token = secrets.token_urlsafe(BYTES_DO_REFRESH)
    return token, hash_do_refresh(token)


def hash_do_refresh(token: str) -> str:
    """SHA-256 em hexadecimal, que é o que a coluna `hash` guarda.

    SHA-256 puro basta, e bcrypt seria errado aqui: o bcrypt é lento de
    propósito para resistir a quem adivinha senha humana, e este token
    tem 256 bits de entropia — não há o que adivinhar. Lentidão só
    custaria tempo em toda renovação.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
