from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import limitador
from app.core.documento import somente_digitos, tipo_documento
from app.core.security import criar_token, hash_senha, verificar_senha
from app.database import get_db
from app.models.usuario import Usuario

router = APIRouter()

# Hash descartável, conferido quando o documento não existe. Sem ele, a
# resposta para conta inexistente volta em microssegundos e a de senha
# errada leva o tempo do bcrypt: a diferença diz de fora quais CPF e
# CNPJ estão cadastrados. Calculado uma vez, na importação do módulo.
_HASH_DE_DESCARTE = hash_senha("conta-que-nao-existe")


class LoginInput(BaseModel):
    # Campo a mais no corpo é recusado: o cliente que manda o que a
    # rota não pede está desalinhado do contrato, e engolir em silêncio
    # esconde o erro.
    model_config = ConfigDict(extra="forbid")

    cpf_cnpj: str = Field(..., max_length=32)
    senha: str = Field(..., max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tipo_usuario: str
    nome: str
    documento: str 
    avatar: str | None = None


def buscar_por_documento(db: Session, documento: str) -> Usuario | None:
    digitos = somente_digitos(documento)
    if not digitos:
        return None

    # regexp_replace do Postgres tira a máscara do lado do banco.
    cpf_cnpj_limpo = func.regexp_replace(Usuario.cpf_cnpj, r"\D", "", "g")

    return (
        db.query(Usuario)
        .filter(cpf_cnpj_limpo == digitos, Usuario.ativo.is_(True))
        .first()
    )


@router.post("/login", response_model=TokenResponse)
def login(
    dados: LoginInput,
    request: Request,
    db: Session = Depends(get_db),
):
    digitos = somente_digitos(dados.cpf_cnpj)
    tipo = tipo_documento(digitos)

    # O teto é conferido antes de qualquer trabalho, e vale também para
    # o documento malformado: caso contrário bastaria mandar lixo para
    # medir o servidor de graça.
    limitador.conferir_login(request, digitos or None)

    if tipo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe um CPF (11 dígitos) ou CNPJ (14 dígitos)",
        )

    usuario = buscar_por_documento(db, digitos)

    # A senha é sempre conferida, mesmo sem usuário, para que as duas
    # respostas custem o mesmo tempo.
    confere = verificar_senha(
        dados.senha, usuario.senha_hash if usuario else _HASH_DE_DESCARTE
    )

    if not usuario or not confere:
        # A mensagem não diz qual dos dois errou. Dizer "esse CPF não
        # existe" entregaria a lista de clientes da loja a quem
        # tentasse documentos em sequência.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF/CNPJ ou senha incorretos",
        )

    limitador.perdoar_login(request, digitos)

    token = criar_token({
        "sub": str(usuario.id),
        "tipo": usuario.tipo,
    })

    return TokenResponse(
        access_token=token,
        tipo_usuario=usuario.tipo,
        nome=usuario.nome,
        documento=tipo,
        avatar=usuario.avatar,
    )
