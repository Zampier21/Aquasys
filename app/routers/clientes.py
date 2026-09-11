from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import planos
from app.core.deps import get_usuario_atual
from app.core.documento import formatar_documento
from app.core.security import hash_senha
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import (
    ClienteCreate, ClienteResponse, ClienteUpdate, PlanoResponse,
)

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


def _acessos_ativos(db: Session, dono: Usuario) -> int:
    """Quantos acessos da loja estão ocupando vaga neste momento.

    Só o ativo conta. Desativar um cliente devolve a vaga — do contrário
    a loja pagaria para sempre por quem deixou de ser cliente.
    """
    return (
        db.query(func.count(Usuario.id))
        .filter(Usuario.dono_id == dono.id, Usuario.ativo.is_(True))
        .scalar()
        or 0
    )


def _exigir_vaga(db: Session, dono: Usuario) -> None:
    """Barra a criação ou a reativação quando o plano já está cheio.

    O teto é da assinatura, não da tela: verificar aqui é o que impede
    que uma requisição montada fora do aplicativo o contorne.
    """
    ativos = _acessos_ativos(db, dono)
    if planos.cabe_mais_um(dono.plano, ativos):
        return

    teto = planos.limite(dono.plano)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            f"O plano {planos.rotulo(dono.plano)} permite {teto} acessos "
            f"ativos, e todos estão em uso. Desative um acesso que não "
            f"esteja mais em atendimento ou fale com a AquaSys para "
            f"ampliar o plano."
        ),
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
# PLANO
# ═══════════════════════════════════════════════════════
# Declarada ANTES de /{cliente_id}: o FastAPI casa as rotas na ordem em
# que são escritas, e "plano" seria engolido como identificador.
@router.get("/plano", response_model=PlanoResponse)
def plano_da_loja(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Plano da assinatura e quantos acessos ainda cabem nele."""
    dono = exigir_dono(usuario)
    ativos = _acessos_ativos(db, dono)
    teto = planos.limite(dono.plano)

    return PlanoResponse(
        plano=dono.plano or planos.PLANO_PADRAO,
        rotulo=planos.rotulo(dono.plano),
        ativos=ativos,
        limite=teto,
        restantes=planos.restantes(dono.plano, ativos),
        ilimitado=teto is None,
    )


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
    _exigir_vaga(db, dono)

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

    # Reativar volta a ocupar vaga, então passa pela mesma verificação da
    # criação. Sem isto o teto seria contornável: bastaria desativar,
    # criar outro e reativar o primeiro.
    if campos.get("ativo") is True and not cliente.ativo:
        _exigir_vaga(db, dono)

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
