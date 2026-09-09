from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.core.documento import formatar_documento
from app.core.security import hash_senha
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import ClienteCreate, ClienteResponse, ClienteUpdate

router = APIRouter()


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def exigir_dono(usuario: Usuario) -> Usuario:
    """Só a conta empresarial administra acessos de clientes."""
    if usuario.tipo != "dono":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas contas empresariais podem gerenciar clientes",
        )
    return usuario


def _montar_resposta(cliente: Usuario) -> ClienteResponse:
    return ClienteResponse(
        id=cliente.id,
        nome=cliente.nome,
        cpf_cnpj=formatar_documento(cliente.cpf_cnpj),
        email=cliente.email,
        ativo=cliente.ativo,
        criado_em=cliente.criado_em,
    )


def _buscar_cliente_do_dono(cliente_id: UUID, dono: Usuario, db: Session) -> Usuario:
    """Busca sempre filtrando pelo dono — ninguém acessa cliente de outra loja."""
    cliente = (
        db.query(Usuario)
        .filter(
            Usuario.id == cliente_id,
            Usuario.dono_id == dono.id,
            Usuario.tipo == "cliente",
        )
        .first()
    )
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    return cliente


def _documento_em_uso(db: Session, digitos: str) -> bool:
    cpf_cnpj_limpo = func.regexp_replace(Usuario.cpf_cnpj, r"\D", "", "g")
    return db.query(Usuario).filter(cpf_cnpj_limpo == digitos).first() is not None


# ═══════════════════════════════════════════════════════
# LISTAR
# ═══════════════════════════════════════════════════════
@router.get("/", response_model=List[ClienteResponse])
def listar_clientes(
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Lista os clientes cadastrados pela loja logada."""
    dono = exigir_dono(usuario)

    consulta = db.query(Usuario).filter(
        Usuario.dono_id == dono.id,
        Usuario.tipo == "cliente",
    )
    if not incluir_inativos:
        consulta = consulta.filter(Usuario.ativo.is_(True))

    clientes = consulta.order_by(Usuario.nome).all()
    return [_montar_resposta(c) for c in clientes]


# ═══════════════════════════════════════════════════════
# DETALHAR
# ═══════════════════════════════════════════════════════
@router.get("/{cliente_id}", response_model=ClienteResponse)
def detalhar_cliente(
    cliente_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    dono = exigir_dono(usuario)
    return _montar_resposta(_buscar_cliente_do_dono(cliente_id, dono, db))


# ═══════════════════════════════════════════════════════
# CRIAR
# ═══════════════════════════════════════════════════════
@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    dados: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Cria o acesso do cliente com a senha inicial definida pela loja."""
    dono = exigir_dono(usuario)

    if _documento_em_uso(db, dados.cpf_cnpj):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um acesso com esse CPF/CNPJ",
        )

    cliente = Usuario(
        nome=dados.nome.strip(),
        cpf_cnpj=formatar_documento(dados.cpf_cnpj),
        senha_hash=hash_senha(dados.senha_inicial),
        tipo="cliente",
        dono_id=dono.id,
        email=dados.email,
        ativo=True,
    )

    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return _montar_resposta(cliente)


# ═══════════════════════════════════════════════════════
# EDITAR
# ═══════════════════════════════════════════════════════
@router.put("/{cliente_id}", response_model=ClienteResponse)
def editar_cliente(
    cliente_id: UUID,
    dados: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Atualiza nome, e-mail, status ou redefine a senha do cliente."""
    dono = exigir_dono(usuario)
    cliente = _buscar_cliente_do_dono(cliente_id, dono, db)

    campos = dados.model_dump(exclude_unset=True)
    senha = campos.pop("senha", None)

    for campo, valor in campos.items():
        setattr(cliente, campo, valor)

    if senha:
        cliente.senha_hash = hash_senha(senha)

    if campos or senha:
        cliente.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(cliente)
    return _montar_resposta(cliente)


# ═══════════════════════════════════════════════════════
# EXCLUIR
# ═══════════════════════════════════════════════════════
@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_cliente(
    cliente_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    dono = exigir_dono(usuario)
    cliente = _buscar_cliente_do_dono(cliente_id, dono, db)

    cliente.ativo = False
    cliente.atualizado_em = datetime.utcnow()
    db.commit()
    return None
