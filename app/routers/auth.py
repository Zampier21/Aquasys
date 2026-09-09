from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.documento import somente_digitos, tipo_documento
from app.core.security import criar_token, verificar_senha
from app.database import get_db
from app.models.usuario import Usuario

router = APIRouter()


class LoginInput(BaseModel):
    cpf_cnpj: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tipo_usuario: str
    nome: str
    documento: str  # 'cpf' ou 'cnpj' — como o login foi reconhecido
    # Foto/logo em base64. Vem já no login para o cabeçalho abrir com a
    # imagem certa, sem uma segunda requisição só para isso.
    avatar: str | None = None


def buscar_por_documento(db: Session, documento: str) -> Usuario | None:
    """
    Busca o usuário comparando apenas os dígitos.

    Assim tanto faz o app mandar "00000000000" e o banco ter
    "000.000.000-00" — ou o contrário.
    """
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
def login(dados: LoginInput, db: Session = Depends(get_db)):
    digitos = somente_digitos(dados.cpf_cnpj)
    tipo = tipo_documento(digitos)

    # 11 dígitos = CPF (pessoa física), 14 = CNPJ (empresa). Qualquer
    # outro tamanho nem chega a consultar o banco.
    if tipo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe um CPF (11 dígitos) ou CNPJ (14 dígitos)",
        )

    usuario = buscar_por_documento(db, digitos)

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF/CNPJ ou senha incorretos",
        )

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
