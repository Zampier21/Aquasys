from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.core.security import verificar_senha, criar_token
from app.models.usuario import Usuario

router = APIRouter()
class LoginInput(BaseModel):
    cpf_cnpj: str
    senha: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tipo_usuario: str

@router.post("/login", response_model=TokenResponse)
def login(dados: LoginInput, db: Session = Depends(get_db)):
    from app.models.usuario import Usuario

    # Busca o usuário pelo CPF/CNPJ
    usuario = db.query(Usuario).filter(
        Usuario.cpf_cnpj == dados.cpf_cnpj,
        Usuario.ativo == True
    ).first()

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
    )