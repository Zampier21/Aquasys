from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_usuario_atual
from app.database import get_db
from app.models.alerta import Alerta
from app.models.aquario import Aquario, ParametrosAgua
from app.models.usuario import Usuario
from app.services import parametros as svc_parametros
from app.schemas.aquario import (
    AquarioCreate, AquarioResponse, AquarioUpdate,
    ParametrosCreate, ParametrosResponse,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def _montar_resposta(aquario: Aquario) -> AquarioResponse:
    ultima_medicao = aquario.parametros[0] if aquario.parametros else None
    habitantes = aquario.habitantes
    problemas, _ = svc_parametros.avaliar(aquario, ultima_medicao, habitantes)

    return AquarioResponse(
        id=aquario.id,
        nome=aquario.nome,
        volume_litros=aquario.volume_litros,
        temperatura=aquario.temperatura,
        ph=aquario.ph,
        tipo=aquario.tipo,
        amonia_ppm=ultima_medicao.amonia_ppm if ultima_medicao else 0,
        nitrito_ppm=ultima_medicao.nitrito_ppm if ultima_medicao else 0,
        nitrato_ppm=ultima_medicao.nitrato_ppm if ultima_medicao else 0,
        medido_em=ultima_medicao.registrado_em if ultima_medicao else None,
        problemas=[p["parametro"] for p in problemas],
        faixas=svc_parametros.faixas_em_texto(aquario, habitantes),
        explicacoes=svc_parametros.explicar(aquario, ultima_medicao, habitantes),
        escala_ph=svc_parametros.ESCALA_PH,
        criado_em=aquario.criado_em,
    )


def _buscar_aquario_do_usuario(
    aquario_id: UUID, usuario: Usuario, db: Session
) -> Aquario:
    aquario = (
        db.query(Aquario)
        .filter(Aquario.id == aquario_id, Aquario.usuario_id == usuario.id)
        .first()
    )
    if aquario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquário não encontrado",
        )
    return aquario


def regerar_alertas(aquario: Aquario, db: Session) -> None:
    db.query(Alerta).filter(Alerta.aquario_id == aquario.id).delete(
        synchronize_session=False
    )

    medicao = aquario.parametros[0] if aquario.parametros else None
    problemas, _ = svc_parametros.avaliar(aquario, medicao, aquario.habitantes)

    for problema in problemas:
        db.add(
            Alerta(
                aquario_id=aquario.id,
                usuario_id=aquario.usuario_id,
                mensagem=problema["mensagem"],
                tipo="parametro",
                lido=False,
            )
        )


# ═══════════════════════════════════════════════════════
# LISTAR
# ═══════════════════════════════════════════════════════
@router.get("/", response_model=List[AquarioResponse])
def listar_aquarios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Lista todos os aquários do usuário logado."""
    aquarios = (
        db.query(Aquario)
        .options(selectinload(Aquario.habitantes))
        .filter(Aquario.usuario_id == usuario.id)
        .order_by(Aquario.criado_em)
        .all()
    )
    return [_montar_resposta(a) for a in aquarios]


# ═══════════════════════════════════════════════════════
# DETALHAR
# ═══════════════════════════════════════════════════════
@router.get("/{aquario_id}", response_model=AquarioResponse)
def detalhar_aquario(
    aquario_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    aquario = _buscar_aquario_do_usuario(aquario_id, usuario, db)
    return _montar_resposta(aquario)


# ═══════════════════════════════════════════════════════
# CRIAR
# ═══════════════════════════════════════════════════════
@router.post("/", response_model=AquarioResponse, status_code=status.HTTP_201_CREATED)
def criar_aquario(
    dados: AquarioCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Cria o aquário e já registra a primeira medição de parâmetros."""
    aquario = Aquario(
        usuario_id=usuario.id,
        nome=dados.nome,
        volume_litros=dados.volume_litros,
        temperatura=dados.temperatura,
        ph=dados.ph,
        tipo=dados.tipo,
    )
    db.add(aquario)
    db.flush()  # gera o id do aquário sem fechar a transação

    medicao = ParametrosAgua(
        aquario_id=aquario.id,
        amonia_ppm=dados.amonia_ppm,
        nitrito_ppm=dados.nitrito_ppm,
        nitrato_ppm=dados.nitrato_ppm,
    )
    db.add(medicao)
    db.flush()
    db.refresh(aquario)
    regerar_alertas(aquario, db)

    db.commit()
    db.refresh(aquario)
    return _montar_resposta(aquario)


# ═══════════════════════════════════════════════════════
# EDITAR
# ═══════════════════════════════════════════════════════
@router.put("/{aquario_id}", response_model=AquarioResponse)
def editar_aquario(
    aquario_id: UUID,
    dados: AquarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    aquario = _buscar_aquario_do_usuario(aquario_id, usuario, db)

    # Atualiza só os campos enviados
    campos_aquario = dados.model_dump(
        exclude_unset=True,
        exclude={"amonia_ppm", "nitrito_ppm", "nitrato_ppm"},
    )
    for campo, valor in campos_aquario.items():
        setattr(aquario, campo, valor)

    if campos_aquario:
        aquario.atualizado_em = datetime.utcnow()

    # Parâmetros químicos geram uma NOVA medição, preservando o histórico
    quimicos = dados.model_dump(
        exclude_unset=True,
        include={"amonia_ppm", "nitrito_ppm", "nitrato_ppm"},
    )
    if quimicos:
        anterior = aquario.parametros[0] if aquario.parametros else None
        db.add(
            ParametrosAgua(
                aquario_id=aquario.id,
                amonia_ppm=quimicos.get(
                    "amonia_ppm", anterior.amonia_ppm if anterior else 0
                ),
                nitrito_ppm=quimicos.get(
                    "nitrito_ppm", anterior.nitrito_ppm if anterior else 0
                ),
                nitrato_ppm=quimicos.get(
                    "nitrato_ppm", anterior.nitrato_ppm if anterior else 0
                ),
            )
        )

    db.flush()
    db.refresh(aquario)
    regerar_alertas(aquario, db)

    db.commit()
    db.refresh(aquario)
    return _montar_resposta(aquario)


# ═══════════════════════════════════════════════════════
# EXCLUIR
# ═══════════════════════════════════════════════════════
@router.delete("/{aquario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_aquario(
    aquario_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Exclui o aquário. Parâmetros, histórico e alertas caem junto (CASCADE)."""
    aquario = _buscar_aquario_do_usuario(aquario_id, usuario, db)
    db.delete(aquario)
    db.commit()
    return None


# ═══════════════════════════════════════════════════════
# MEDIÇÕES
# ═══════════════════════════════════════════════════════
@router.get("/{aquario_id}/parametros", response_model=List[ParametrosResponse])
def historico_parametros(
    aquario_id: UUID,
    limite: int = 30,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Histórico de medições, da mais recente para a mais antiga."""
    _buscar_aquario_do_usuario(aquario_id, usuario, db)
    return (
        db.query(ParametrosAgua)
        .filter(ParametrosAgua.aquario_id == aquario_id)
        .order_by(ParametrosAgua.registrado_em.desc())
        .limit(limite)
        .all()
    )
