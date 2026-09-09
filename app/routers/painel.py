"""
Painel da tela inicial.

Uma requisição só devolve tudo que a Home mostra: os três números do
topo, os alertas abertos e as dicas. Antes esses valores eram texto fixo
no app.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.database import get_db
from app.models.alerta import Alerta
from app.models.aquario import Aquario
from app.models.dica import Dica
from app.models.especie import AquarioEspecie, Especie
from app.models.usuario import Usuario
from app.services import dicas as svc_dicas
from app.services import parametros as svc_parametros

router = APIRouter()


class AlertaResponse(BaseModel):
    id: UUID
    aquario_id: UUID
    aquario: str
    mensagem: str
    tipo: Optional[str] = None
    lido: bool


class DicaResponse(BaseModel):
    # Dica de situação nasce do estado do aquário, não da tabela `dica`,
    # então não tem id. O app usa o índice na lista como chave.
    id: Optional[UUID] = None
    conteudo: str
    categoria: Optional[str] = None


class PainelResponse(BaseModel):
    total_aquarios: int
    total_peixes: int
    # Percentual de parâmetros dentro da faixa ideal. None quando ainda
    # não há aquário nenhum — a tela mostra "—" em vez de fingir 100%.
    saude_geral: Optional[int] = None
    alertas: List[AlertaResponse]
    dicas: List[DicaResponse]


@router.get("/", response_model=PainelResponse)
def painel(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Resumo da conta logada — os aquários dela, nada de terceiros."""
    aquarios = (
        db.query(Aquario)
        .filter(Aquario.usuario_id == usuario.id)
        .order_by(Aquario.criado_em)
        .all()
    )
    ids = [a.id for a in aquarios]

    # ─── Total de peixes ──────────────────────────────
    total_peixes = 0
    if ids:
        total_peixes = (
            db.query(func.coalesce(func.sum(AquarioEspecie.quantidade), 0))
            .filter(AquarioEspecie.aquario_id.in_(ids))
            .scalar()
        ) or 0

    # ─── Saúde geral ──────────────────────────────────
    # Percentual das checagens aprovadas somando todos os aquários:
    # 2 aquários × 5 parâmetros = 10 checagens; 1 fora = 90%.
    povoamento = _povoamento(ids, db)

    aprovadas = 0
    avaliadas = 0
    for aquario in aquarios:
        medicao = aquario.parametros[0] if aquario.parametros else None
        habitantes = [e for e, _ in povoamento.get(aquario.id, [])]
        problemas, total = svc_parametros.avaliar(aquario, medicao, habitantes)
        aprovadas += total - len(problemas)
        avaliadas += total

    saude = round(aprovadas * 100 / avaliadas) if avaliadas else None

    # ─── Alertas abertos ──────────────────────────────
    nome_por_id = {a.id: a.nome for a in aquarios}
    alertas = []
    if ids:
        alertas = (
            db.query(Alerta)
            .filter(Alerta.aquario_id.in_(ids), Alerta.lido.is_(False))
            .order_by(Alerta.criado_em.desc())
            .all()
        )

    return PainelResponse(
        total_aquarios=len(aquarios),
        total_peixes=int(total_peixes),
        saude_geral=saude,
        alertas=[
            AlertaResponse(
                id=a.id,
                aquario_id=a.aquario_id,
                aquario=nome_por_id.get(a.aquario_id, ""),
                mensagem=a.mensagem,
                tipo=a.tipo,
                lido=a.lido,
            )
            for a in alertas
        ],
        dicas=_dicas_para(aquarios, povoamento, ids, db),
    )


# A Home do Figma mostra três dicas.
_QUANTAS_DICAS = 3


def _povoamento(ids_aquarios: list, db: Session) -> dict:
    """{id do aquário: [(Especie, quantidade), ...]} numa consulta só."""
    if not ids_aquarios:
        return {}

    linhas = (
        db.query(AquarioEspecie, Especie)
        .join(Especie, Especie.id == AquarioEspecie.especie_id)
        .filter(AquarioEspecie.aquario_id.in_(ids_aquarios))
        .all()
    )

    mapa: dict = {}
    for item, especie in linhas:
        mapa.setdefault(item.aquario_id, []).append((especie, item.quantidade))
    return mapa


def _dicas_para(
    aquarios: list, povoamento: dict, ids_aquarios: list, db: Session
) -> List[DicaResponse]:
    """
    Três dicas, da mais pessoal para a mais genérica.

    1. Situação: lidas do estado atual dos aquários desta conta.
    2. Espécie: o `especie_id` da tabela existe para isso — a dica sobre
       cardume de tetra neon só aparece para quem tem tetra neon.
    3. Geral: preenche o que sobrar, para a Home nunca ficar vazia.

    A ordem importa: antes, as três vagas eram ocupadas pelas gerais e o
    cliente via sempre o mesmo texto, sem relação com o aquário dele.
    """
    escolhidas = [
        DicaResponse(conteudo=d["conteudo"], categoria=d["categoria"])
        for d in svc_dicas.situacionais(aquarios, povoamento)
    ][:_QUANTAS_DICAS]

    faltam = _QUANTAS_DICAS - len(escolhidas)
    if faltam <= 0:
        return escolhidas

    especies = {e.id for lista in povoamento.values() for e, _ in lista}

    consulta = db.query(Dica).filter(Dica.ativa.is_(True))
    if especies:
        consulta = consulta.filter(
            (Dica.especie_id.is_(None)) | (Dica.especie_id.in_(especies))
        )
    else:
        consulta = consulta.filter(Dica.especie_id.is_(None))

    # `especie_id IS NULL` ordena False (específica) antes de True (geral).
    curadas = consulta.order_by(Dica.especie_id.is_(None)).limit(faltam).all()

    return escolhidas + [
        DicaResponse(id=d.id, conteudo=d.conteudo, categoria=d.categoria)
        for d in curadas
    ]


@router.patch("/alertas/{alerta_id}/lido", status_code=204)
def marcar_lido(
    alerta_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Dispensa um alerta sem que o parâmetro tenha sido corrigido.

    Ele volta na próxima medição que continuar fora da faixa — é o que
    impede o lembrete diário de virar incômodo permanente.
    """
    (
        db.query(Alerta)
        .filter(Alerta.id == alerta_id, Alerta.usuario_id == usuario.id)
        .update({"lido": True}, synchronize_session=False)
    )
    db.commit()
    return None
