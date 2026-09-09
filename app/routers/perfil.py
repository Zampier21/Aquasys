import base64
import binascii
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.core.documento import formatar_documento, tipo_documento, somente_digitos
from app.core.security import hash_senha, verificar_senha
from app.database import get_db
from app.models.usuario import Usuario

router = APIRouter()
TAMANHO_MAXIMO_AVATAR = 400 * 1024
_ASSINATURAS = (
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
)


# ═══════════════════════════════════════════════════════
# CONTRATOS
# ═══════════════════════════════════════════════════════
class PerfilResponse(BaseModel):
    nome: str
    documento: str          # com máscara, só para exibir
    documento_tipo: str     # 'cpf' | 'cnpj'
    tipo: str               # 'dono' | 'cliente'
    email: Optional[str] = None
    avatar: Optional[str] = None


class PerfilUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=150)
    email: Optional[str] = Field(default=None, max_length=150)


class SenhaUpdate(BaseModel):
    senha_atual: str = Field(..., min_length=1)
    senha_nova: str = Field(..., min_length=6, max_length=100)


class AvatarUpdate(BaseModel):
    imagem: str = Field(..., min_length=1)


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def _montar(usuario: Usuario) -> PerfilResponse:
    digitos = somente_digitos(usuario.cpf_cnpj)
    return PerfilResponse(
        nome=usuario.nome,
        documento=formatar_documento(digitos),
        documento_tipo=tipo_documento(digitos) or "cpf",
        tipo=usuario.tipo,
        email=usuario.email,
        avatar=usuario.avatar,
    )


def _validar_imagem(bruto: str) -> str:
    conteudo = bruto.strip()
    if conteudo.startswith("data:"):
        _, _, conteudo = conteudo.partition(",")

    try:
        binario = base64.b64decode(conteudo, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "A imagem enviada está corrompida"
        )

    if len(binario) > TAMANHO_MAXIMO_AVATAR:
        limite = TAMANHO_MAXIMO_AVATAR // 1024
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Imagem muito grande. O limite é {limite} KB",
        )

    if not any(binario.startswith(a) for a, _ in _ASSINATURAS):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Formato não aceito. Envie uma imagem JPG, PNG ou GIF",
        )

    return conteudo


# ═══════════════════════════════════════════════════════
# ROTAS
# ═══════════════════════════════════════════════════════
@router.get("/", response_model=PerfilResponse)
def meu_perfil(usuario: Usuario = Depends(get_usuario_atual)):
    """Dados da conta logada, para a tela de Configurações."""
    return _montar(usuario)


@router.patch("/", response_model=PerfilResponse)
def editar_perfil(
    dados: PerfilUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Muda o nome exibido e o e-mail de contato."""
    campos = dados.model_dump(exclude_unset=True)

    if "nome" in campos:
        nome = (campos["nome"] or "").strip()
        if not nome:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "O nome não pode ficar em branco"
            )
        usuario.nome = nome

    if "email" in campos:
        email = (campos["email"] or "").strip()
        # Campo opcional: apagar é uma edição válida, não um erro.
        usuario.email = email or None

    if campos:
        usuario.atualizado_em = datetime.utcnow()
        db.commit()
        db.refresh(usuario)

    return _montar(usuario)


@router.put("/senha", status_code=status.HTTP_204_NO_CONTENT)
def trocar_senha(
    dados: SenhaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "A senha atual está incorreta"
        )

    if verificar_senha(dados.senha_nova, usuario.senha_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "A nova senha é igual à atual"
        )

    usuario.senha_hash = hash_senha(dados.senha_nova)
    usuario.atualizado_em = datetime.utcnow()
    db.commit()
    return None


@router.put("/avatar", response_model=PerfilResponse)
def trocar_avatar(
    dados: AvatarUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Grava a foto de perfil da conta — a logo, no caso da loja."""
    usuario.avatar = _validar_imagem(dados.imagem)
    usuario.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(usuario)
    return _montar(usuario)


@router.delete("/avatar", status_code=status.HTTP_204_NO_CONTENT)
def remover_avatar(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Volta ao ícone padrão."""
    usuario.avatar = None
    usuario.atualizado_em = datetime.utcnow()
    db.commit()
    return None
