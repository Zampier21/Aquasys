from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.database import get_db
from app.models.aquario import Aquario
from app.models.especie import CompatibEspecie, Especie
from app.models.usuario import Usuario
from app.schemas.especie import (
    AnaliseResponse, CompatividadeResumo, EspecieCreate, EspecieResponse,
)
from app.services.compatibilidade import (
    MOTIVOS_IMPEDITIVOS, Nivel, avaliar_adicao, avaliar_especie_no_aquario,
)

router = APIRouter()


def _carregar_excecoes(db: Session) -> dict:
    """Indexa as exceções curadas por par ordenado de IDs."""
    excecoes = {}
    for c in db.query(CompatibEspecie).all():
        chave = tuple(sorted([str(c.especie_a_id), str(c.especie_b_id)]))
        excecoes[chave] = {
            "nivel": c.nivel,
            "motivo": c.motivo,
            "observacao": c.observacao,
        }
    return excecoes


def _buscar_aquario(aquario_id: UUID, usuario: Usuario, db: Session) -> Aquario:
    """Busca filtrando pelo usuário logado — impede acesso cruzado."""
    aquario = (
        db.query(Aquario)
        .filter(Aquario.id == aquario_id, Aquario.usuario_id == usuario.id)
        .first()
    )
    if aquario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aquário não encontrado")
    return aquario


def _habitantes(aquario_id: UUID, db: Session) -> List[tuple]:
    """Espécies já presentes no aquário, com quantidade."""
    linhas = db.execute(
        text(
            "SELECT especie_id, quantidade "
            "FROM aquario_especie WHERE aquario_id = :aq"
        ),
        {"aq": str(aquario_id)},
    ).fetchall()

    resultado = []
    for especie_id, quantidade in linhas:
        especie = db.query(Especie).filter(Especie.id == especie_id).first()
        if especie:
            resultado.append((especie, quantidade))
    return resultado


# ═══════════════════════════════════════════════════════
# CATÁLOGO
# ═══════════════════════════════════════════════════════
@router.get("/", response_model=List[EspecieResponse])
def listar_especies(
    busca: Optional[str] = Query(default=None, description="Nome comum ou científico"),
    tipo_agua: Optional[str] = Query(default=None, description="doce | salobra | marinho"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Catálogo de espécies, com busca opcional."""
    query = db.query(Especie).filter(Especie.ativo == True)  # noqa: E712

    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                Especie.nome_comum.ilike(termo),
                Especie.nome_cientifico.ilike(termo),
            )
        )

    if tipo_agua:
        query = query.filter(Especie.tipo_agua == tipo_agua)

    return query.order_by(Especie.nome_comum).all()


@router.get("/{especie_id}", response_model=EspecieResponse)
def detalhar_especie(
    especie_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    especie = db.query(Especie).filter(Especie.id == especie_id).first()
    if especie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espécie não encontrada")
    return especie


@router.post("/", response_model=EspecieResponse, status_code=status.HTTP_201_CREATED)
def criar_especie(
    dados: EspecieCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Cadastro de espécie — restrito ao perfil dono."""
    if usuario.tipo != "dono":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Apenas o perfil empresarial pode cadastrar espécies",
        )

    especie = Especie(**dados.model_dump())
    db.add(especie)
    db.commit()
    db.refresh(especie)
    return especie


# ═══════════════════════════════════════════════════════
# COMPATIBILIDADE
# ═══════════════════════════════════════════════════════
@router.get("/{especie_id}/aquario/{aquario_id}", response_model=AnaliseResponse)
def compatibilidade_com_aquario(
    especie_id: UUID,
    aquario_id: UUID,
    quantidade: int = Query(default=1, gt=0),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Analisa se a espécie pode entrar no aquário.

    Considera parâmetros da água, volume, cardume, lotação e o
    confronto com cada espécie já presente. Devolve uma das três
    decisões: liberado, requer_confirmacao ou bloqueado.
    """
    especie = db.query(Especie).filter(Especie.id == especie_id).first()
    if especie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espécie não encontrada")

    aquario = _buscar_aquario(aquario_id, usuario, db)

    return avaliar_adicao(
        nova=especie,
        quantidade=quantidade,
        aquario=aquario,
        habitantes=_habitantes(aquario_id, db),
        excecoes=_carregar_excecoes(db),
    )


@router.get("/compativeis/{aquario_id}", response_model=List[CompatividadeResumo])
def especies_compativeis(
    aquario_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Percorre o catálogo e classifica cada espécie para este aquário.

    É o que alimenta os selos Ideal / Atenção / Evitar na tela de Peixes.
    """
    aquario = _buscar_aquario(aquario_id, usuario, db)

    resposta = []
    for especie in db.query(Especie).filter(Especie.ativo == True).all():  # noqa: E712
        analise = avaliar_especie_no_aquario(especie, aquario)

        tem_fatal = any(a.nivel == Nivel.FATAL for a in analise.achados)
        tem_impeditivo = any(
            a.nivel == Nivel.RUIM and a.motivo in MOTIVOS_IMPEDITIVOS
            for a in analise.achados
        )

        if tem_fatal or tem_impeditivo:
            decisao = "bloqueado"
        elif analise.achados:
            decisao = "requer_confirmacao"
        else:
            decisao = "liberado"

        resposta.append(
            CompatividadeResumo(
                especie_id=str(especie.id),
                nome_comum=especie.nome_comum,
                nivel=analise.nivel.value,
                decisao=decisao,
                avisos=analise.mensagens,
            )
        )

    return resposta