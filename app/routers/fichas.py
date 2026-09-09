"""
Fichas técnicas de manutenção.

A ficha registra um atendimento presencial. O nome do cliente é digitado
à mão de propósito: quem contrata manutenção nem sempre tem acesso ao app,
então a ficha não se prende à lista de acessos cadastrados.
"""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_usuario_atual
from app.database import get_db
from app.models.ficha import (
    ChecklistEquipamento,
    ClienteManutencao,
    DescricaoManutencao,
    FichaManutencao,
    TesteAgua,
)
from app.models.usuario import Usuario
from app.routers.clientes import exigir_dono
from app.schemas.ficha import (
    ClienteManutencaoCreate, ClienteManutencaoResponse, ClienteManutencaoUpdate,
    FichaCreate, FichaResponse, FichaResumo, FichaUpdate,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════
# CATÁLOGOS PADRÃO — o que a tela mostra pré-marcável
# ═══════════════════════════════════════════════════════
MAQUINARIOS_PADRAO = [
    "Aquecedor",
    "Bomba de circulação (wave maker)",
    "Bomba de dosagem",
    "Bomba Submersa/Recalque",
    "Chiller",
    "Compressor de ar",
    "Coolers",
    "Esterilizador UV",
    "Filtro",
    "Luminária",
    "Ozônio",
]

# O banco guarda o código curto; o rótulo longo é só para a tela.
# (codigo, rotulo, unidade sugerida)
TESTES_PADRAO = [
    ("pH",   "PH",                               ""),
    ("KH",   "KH (Dureza de carbonatos)",        "dKH"),
    ("GH",   "GH (Dureza total)",                "dGH"),
    ("Cl",   "Cloro (Cl₂)",                      "ppm"),
    ("PO4",  "Fosfato (PO₄)",                    "ppm"),
    ("Ca",   "Cálcio (Ca)",                      "ppm"),
    ("Mg",   "Magnésio (Mg)",                    "ppm"),
    ("Fe",   "Ferro (Fe)",                       "ppm"),
    ("SiO2", "Silicato (SiO₂)",                  "ppm"),
    ("TDS",  "TDS (Sólidos Totais Dissolvidos)", "ppm"),
    ("Cu",   "Cobre (Cu)",                       "ppm"),
]


@router.get("/catalogos")
def catalogos(usuario: Usuario = Depends(get_usuario_atual)):
    """Listas padrão de maquinários e testes usadas na ficha."""
    exigir_dono(usuario)
    return {
        "maquinarios": MAQUINARIOS_PADRAO,
        "testes": [
            {"parametro": c, "rotulo": r, "unidade": u}
            for c, r, u in TESTES_PADRAO
        ],
    }


# ═══════════════════════════════════════════════════════
# CLIENTES DE MANUTENÇÃO
#
# Quem a loja visita em casa. Cadastro leve, sem login: existe para
# o técnico não redigitar contato e dados do aquário a cada visita.
# ═══════════════════════════════════════════════════════
def _buscar_cliente(cliente_id: UUID, dono: Usuario, db: Session) -> ClienteManutencao:
    cliente = (
        db.query(ClienteManutencao)
        .filter(
            ClienteManutencao.id == cliente_id,
            ClienteManutencao.dono_id == dono.id,
        )
        .first()
    )
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente de manutenção não encontrado",
        )
    return cliente


def _montar_cliente(cliente: ClienteManutencao, db: Session) -> ClienteManutencaoResponse:
    resumo = (
        db.query(
            func.count(FichaManutencao.id),
            func.max(FichaManutencao.data_atendimento),
        )
        .filter(FichaManutencao.cliente_id == cliente.id)
        .one()
    )

    return ClienteManutencaoResponse(
        id=cliente.id,
        nome=cliente.nome,
        telefone=cliente.telefone,
        endereco=cliente.endereco,
        tipo_instalacao=cliente.tipo_instalacao,
        volume_litros=cliente.volume_litros,
        agua_doce=cliente.agua_doce,
        observacoes=cliente.observacoes,
        ativo=cliente.ativo,
        criado_em=cliente.criado_em,
        total_fichas=resumo[0] or 0,
        ultima_visita=resumo[1],
    )


@router.get("/clientes", response_model=List[ClienteManutencaoResponse])
def listar_clientes_manutencao(
    busca: str | None = Query(default=None, description="Filtra pelo nome"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Clientes que a loja atende em manutenção."""
    dono = exigir_dono(usuario)

    consulta = db.query(ClienteManutencao).filter(
        ClienteManutencao.dono_id == dono.id,
        ClienteManutencao.ativo.is_(True),
    )
    if busca:
        consulta = consulta.filter(ClienteManutencao.nome.ilike(f"%{busca}%"))

    return [
        _montar_cliente(c, db)
        for c in consulta.order_by(ClienteManutencao.nome).all()
    ]


@router.post(
    "/clientes",
    response_model=ClienteManutencaoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_cliente_manutencao(
    dados: ClienteManutencaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    dono = exigir_dono(usuario)

    repetido = (
        db.query(ClienteManutencao)
        .filter(
            ClienteManutencao.dono_id == dono.id,
            func.lower(ClienteManutencao.nome) == dados.nome.strip().lower(),
        )
        .first()
    )
    if repetido is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Você já tem um cliente chamado "{repetido.nome}"',
        )

    cliente = ClienteManutencao(dono_id=dono.id, ativo=True, **dados.model_dump())
    cliente.nome = cliente.nome.strip()
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return _montar_cliente(cliente, db)


@router.put("/clientes/{cliente_id}", response_model=ClienteManutencaoResponse)
def editar_cliente_manutencao(
    cliente_id: UUID,
    dados: ClienteManutencaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    dono = exigir_dono(usuario)
    cliente = _buscar_cliente(cliente_id, dono, db)

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    cliente.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(cliente)
    return _montar_cliente(cliente, db)


@router.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_cliente_manutencao(
    cliente_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Tira o cliente da lista sem apagar as fichas dele.

    As visitas já registradas continuam valendo — elas guardam o nome
    do dia do atendimento e não dependem mais do cadastro.
    """
    dono = exigir_dono(usuario)
    cliente = _buscar_cliente(cliente_id, dono, db)

    cliente.ativo = False
    cliente.atualizado_em = datetime.utcnow()
    db.commit()
    return None


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def _buscar_ficha_do_dono(ficha_id: UUID, dono: Usuario, db: Session) -> FichaManutencao:
    ficha = (
        db.query(FichaManutencao)
        .options(
            selectinload(FichaManutencao.equipamentos),
            selectinload(FichaManutencao.testes),
            selectinload(FichaManutencao.descricao),
        )
        .filter(FichaManutencao.id == ficha_id, FichaManutencao.dono_id == dono.id)
        .first()
    )
    if ficha is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada",
        )
    return ficha


def _aplicar_filhos(ficha: FichaManutencao, dados) -> None:
    """
    Regrava as listas filhas da ficha.

    Só mexe no que veio no corpo: uma lista ausente fica como está,
    uma lista presente substitui a anterior por inteiro.
    """
    if dados.equipamentos is not None:
        ficha.equipamentos = [
            ChecklistEquipamento(
                equipamento=e.equipamento,
                presente=e.presente,
            )
            for e in dados.equipamentos
        ]

    if dados.testes is not None:
        ficha.testes = [
            TesteAgua(
                parametro=t.parametro,
                valor=t.valor,
                unidade=t.unidade or None,
            )
            for t in dados.testes
        ]

    if dados.descricao is not None:
        ficha.descricao = DescricaoManutencao(**dados.descricao.model_dump())


# ═══════════════════════════════════════════════════════
# LISTAR
# ═══════════════════════════════════════════════════════
@router.get("/", response_model=List[FichaResumo])
def listar_fichas(
    cliente: str | None = Query(default=None, description="Filtra pelo nome do cliente"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Fichas da loja logada, da mais recente para a mais antiga."""
    dono = exigir_dono(usuario)

    consulta = db.query(FichaManutencao).filter(FichaManutencao.dono_id == dono.id)
    if cliente:
        consulta = consulta.filter(FichaManutencao.nome_cliente.ilike(f"%{cliente}%"))

    return consulta.order_by(FichaManutencao.criado_em.desc()).all()


# ═══════════════════════════════════════════════════════
# DETALHAR
# ═══════════════════════════════════════════════════════
@router.get("/{ficha_id}", response_model=FichaResponse)
def detalhar_ficha(
    ficha_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    dono = exigir_dono(usuario)
    return _buscar_ficha_do_dono(ficha_id, dono, db)


# ═══════════════════════════════════════════════════════
# CRIAR
# ═══════════════════════════════════════════════════════
@router.post("/", response_model=FichaResponse, status_code=status.HTTP_201_CREATED)
def criar_ficha(
    dados: FichaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Registra um atendimento.

    Com `cliente_id`, o que ficar em branco é copiado do cadastro: nome,
    tipo de instalação, litros e tipo de água. Assim a segunda visita ao
    mesmo cliente só precisa do que mudou — data, horário e o serviço.
    """
    dono = exigir_dono(usuario)

    campos = dados.model_dump(exclude={"equipamentos", "testes", "descricao"})

    if dados.cliente_id is not None:
        cliente = _buscar_cliente(dados.cliente_id, dono, db)
        for campo in (
            "nome_cliente",
            "tipo_instalacao",
            "volume_litros",
            "agua_doce",
        ):
            if campos.get(campo) is None:
                origem = "nome" if campo == "nome_cliente" else campo
                campos[campo] = getattr(cliente, origem)

    if not campos.get("nome_cliente"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Escolha um cliente cadastrado ou informe o nome",
        )

    ficha = FichaManutencao(dono_id=dono.id, **campos)
    _aplicar_filhos(ficha, dados)

    db.add(ficha)
    db.commit()
    db.refresh(ficha)
    return ficha


# ═══════════════════════════════════════════════════════
# EDITAR
# ═══════════════════════════════════════════════════════
@router.put("/{ficha_id}", response_model=FichaResponse)
def editar_ficha(
    ficha_id: UUID,
    dados: FichaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    dono = exigir_dono(usuario)
    ficha = _buscar_ficha_do_dono(ficha_id, dono, db)

    campos = dados.model_dump(
        exclude_unset=True,
        exclude={"equipamentos", "testes", "descricao"},
    )
    for campo, valor in campos.items():
        setattr(ficha, campo, valor)

    _aplicar_filhos(ficha, dados)
    ficha.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(ficha)
    return ficha


# ═══════════════════════════════════════════════════════
# EXCLUIR
# ═══════════════════════════════════════════════════════
@router.delete("/{ficha_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_ficha(
    ficha_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Exclui a ficha. Check-list, testes e descrição caem junto."""
    dono = exigir_dono(usuario)
    ficha = _buscar_ficha_do_dono(ficha_id, dono, db)
    db.delete(ficha)
    db.commit()
    return None
