from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_usuario_atual
from app.database import get_db
from app.models.curso import Aula, Curso, ProgressoAula, ProgressoCurso
from app.models.usuario import Usuario
from app.schemas.curso import (
    AulaCreate, AulaResponse, PlaylistImportar,
    CursoCreate, CursoResponse, CursoResumo,
)
from app.services import youtube

router = APIRouter()


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def _loja_do_usuario(usuario: Usuario) -> UUID | None:
    return usuario.id if usuario.tipo == "dono" else usuario.dono_id


def _visiveis_para(usuario: Usuario, db: Session):
    """Consulta base: cursos globais + os da loja do usuário."""
    loja = _loja_do_usuario(usuario)
    consulta = db.query(Curso).filter(Curso.ativo.is_(True))

    if loja is None:
        return consulta.filter(Curso.dono_id.is_(None))
    return consulta.filter(
        (Curso.dono_id.is_(None)) | (Curso.dono_id == loja)
    )


def _concluidas_por_curso(usuario: Usuario, db: Session) -> dict:
    """{curso_id: quantas aulas o usuário concluiu} numa consulta só."""
    linhas = (
        db.query(Aula.curso_id, func.count(ProgressoAula.id))
        .join(ProgressoAula, ProgressoAula.aula_id == Aula.id)
        .filter(
            ProgressoAula.usuario_id == usuario.id,
            ProgressoAula.concluida.is_(True),
        )
        .group_by(Aula.curso_id)
        .all()
    )
    return {curso_id: total for curso_id, total in linhas}


def _percentual(concluidas: int, total: int) -> int:
    return round(concluidas * 100 / total) if total else 0


def _montar_resumo(curso: Curso, concluidas: int) -> CursoResumo:
    total = len(curso.aulas)
    return CursoResumo(
        id=curso.id,
        titulo=curso.titulo,
        descricao=curso.descricao,
        categoria=curso.categoria,
        # Sem capa própria, usa a miniatura da primeira aula.
        miniatura_url=curso.miniatura_url
        or (curso.aulas[0].miniatura_url if curso.aulas else None),
        curso_global=curso.dono_id is None,
        total_aulas=total,
        aulas_concluidas=concluidas,
        percentual=_percentual(concluidas, total),
    )


def _buscar_curso_visivel(curso_id: UUID, usuario: Usuario, db: Session) -> Curso:
    curso = (
        _visiveis_para(usuario, db)
        .options(selectinload(Curso.aulas))
        .filter(Curso.id == curso_id)
        .first()
    )
    if curso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso não encontrado",
        )
    return curso


def _buscar_curso_da_loja(curso_id: UUID, usuario: Usuario, db: Session) -> Curso:
    if usuario.tipo != "dono":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas contas empresariais podem gerenciar cursos",
        )

    curso = (
        db.query(Curso)
        .options(selectinload(Curso.aulas))
        .filter(Curso.id == curso_id, Curso.dono_id == usuario.id)
        .first()
    )
    if curso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso não encontrado entre os seus",
        )
    return curso


def _recalcular_progresso(curso: Curso, usuario: Usuario, db: Session) -> int:
    """Atualiza o cache em progresso_curso e devolve o percentual."""
    ids_aulas = [a.id for a in curso.aulas]

    concluidas = 0
    if ids_aulas:
        concluidas = (
            db.query(func.count(ProgressoAula.id))
            .filter(
                ProgressoAula.usuario_id == usuario.id,
                ProgressoAula.aula_id.in_(ids_aulas),
                ProgressoAula.concluida.is_(True),
            )
            .scalar()
        ) or 0

    percentual = _percentual(concluidas, len(ids_aulas))

    registro = (
        db.query(ProgressoCurso)
        .filter(
            ProgressoCurso.usuario_id == usuario.id,
            ProgressoCurso.curso_id == curso.id,
        )
        .first()
    )
    if registro is None:
        registro = ProgressoCurso(usuario_id=usuario.id, curso_id=curso.id)
        db.add(registro)

    registro.percentual = percentual
    registro.atualizado_em = datetime.utcnow()
    return percentual


# ═══════════════════════════════════════════════════════
# LISTAR
# ═══════════════════════════════════════════════════════
@router.get("/", response_model=List[CursoResumo])
def listar_cursos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Cursos globais mais os da loja, com o progresso de quem está logado."""
    cursos = (
        _visiveis_para(usuario, db)
        .options(selectinload(Curso.aulas))
        .order_by(Curso.dono_id.is_(None).desc(), Curso.titulo)
        .all()
    )
    concluidas = _concluidas_por_curso(usuario, db)

    return [_montar_resumo(c, concluidas.get(c.id, 0)) for c in cursos]


# ═══════════════════════════════════════════════════════
# DETALHAR
# ═══════════════════════════════════════════════════════
@router.get("/{curso_id}", response_model=CursoResponse)
def detalhar_curso(
    curso_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    curso = _buscar_curso_visivel(curso_id, usuario, db)

    concluidas_ids = {
        linha[0]
        for linha in db.query(ProgressoAula.aula_id)
        .filter(
            ProgressoAula.usuario_id == usuario.id,
            ProgressoAula.concluida.is_(True),
        )
        .all()
    }

    aulas = [
        AulaResponse(
            id=a.id,
            titulo=a.titulo,
            youtube_id=a.youtube_id,
            canal=a.canal,
            miniatura_url=a.miniatura_url,
            ordem=a.ordem,
            concluida=a.id in concluidas_ids,
        )
        for a in curso.aulas
    ]

    resumo = _montar_resumo(curso, sum(1 for a in aulas if a.concluida))
    return CursoResponse(
        **resumo.model_dump(),
        aulas=aulas,
        publicado_em=curso.publicado_em,
    )


# ═══════════════════════════════════════════════════════
# PROGRESSO
# ═══════════════════════════════════════════════════════
@router.patch("/aulas/{aula_id}/concluida")
def marcar_aula(
    aula_id: UUID,
    concluida: bool = True,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Marca ou desmarca uma aula e devolve o progresso novo do curso."""
    aula = db.query(Aula).filter(Aula.id == aula_id).first()
    if aula is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada"
        )

    # Confirma que o curso da aula é visível para este usuário.
    curso = _buscar_curso_visivel(aula.curso_id, usuario, db)

    registro = (
        db.query(ProgressoAula)
        .filter(
            ProgressoAula.usuario_id == usuario.id,
            ProgressoAula.aula_id == aula_id,
        )
        .first()
    )
    if registro is None:
        registro = ProgressoAula(usuario_id=usuario.id, aula_id=aula_id)
        db.add(registro)

    registro.concluida = concluida
    registro.atualizado_em = datetime.utcnow()
    db.flush()

    percentual = _recalcular_progresso(curso, usuario, db)
    db.commit()

    return {"aula_id": str(aula_id), "concluida": concluida, "percentual": percentual}


# ═══════════════════════════════════════════════════════
# GESTÃO PELA LOJA
# ═══════════════════════════════════════════════════════
@router.post("/", response_model=CursoResponse, status_code=status.HTTP_201_CREATED)
def criar_curso(
    dados: CursoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Cria um curso próprio da loja. Cursos globais não saem por aqui."""
    if usuario.tipo != "dono":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas contas empresariais podem criar cursos",
        )

    curso = Curso(dono_id=usuario.id, ativo=True, **dados.model_dump())
    db.add(curso)
    db.commit()
    db.refresh(curso)

    return detalhar_curso(curso.id, db, usuario)


@router.delete("/{curso_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_curso(
    curso_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Exclusão lógica: o curso sai das listas e o progresso permanece.

    Apagar a linha levaria junto as aulas e, com elas, o progresso de
    cada aluno que já tinha assistido. A coluna `ativo` já existia e já
    era filtrada na listagem; faltava usá-la aqui.
    """
    curso = _buscar_curso_da_loja(curso_id, usuario, db)
    curso.ativo = False
    db.commit()
    return None


@router.post("/{curso_id}/restaurar")
def restaurar_curso(
    curso_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Devolve o curso às listas, com as aulas e o progresso intactos."""
    curso = _buscar_curso_da_loja(curso_id, usuario, db)
    if not curso.ativo:
        curso.ativo = True
        db.commit()
        db.refresh(curso)
    return detalhar_curso(curso.id, db, usuario)


# ═══════════════════════════════════════════════════════
# AULAS
# ═══════════════════════════════════════════════════════
@router.post(
    "/{curso_id}/aulas",
    response_model=AulaResponse,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_aula(
    curso_id: UUID,
    dados: AulaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    curso = _buscar_curso_da_loja(curso_id, usuario, db)

    try:
        meta = youtube.buscar_metadados(dados.url)
    except youtube.VideoInvalido as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)
        ) from erro

    if any(a.youtube_id == meta["youtube_id"] for a in curso.aulas):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse vídeo já está neste curso",
        )

    aula = Aula(
        curso_id=curso.id,
        titulo=dados.titulo or meta["titulo"],
        youtube_id=meta["youtube_id"],
        canal=meta["canal"],
        miniatura_url=meta["miniatura_url"],
        ordem=len(curso.aulas),
    )
    db.add(aula)
    db.commit()
    db.refresh(aula)

    return AulaResponse.model_validate(aula)


@router.post(
    "/{curso_id}/aulas/playlist",
    response_model=CursoResponse,
    status_code=status.HTTP_201_CREATED,
)
def importar_playlist(
    curso_id: UUID,
    dados: PlaylistImportar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    curso = _buscar_curso_da_loja(curso_id, usuario, db)

    try:
        playlist = youtube.buscar_playlist(dados.url)
    except youtube.PlaylistInvalida as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)
        ) from erro

    existentes = {a.youtube_id for a in curso.aulas}
    proxima_ordem = len(curso.aulas)

    for video in playlist["videos"]:
        if video["youtube_id"] in existentes:
            continue

        db.add(Aula(
            curso_id=curso.id,
            titulo=video["titulo"],
            youtube_id=video["youtube_id"],
            canal=video["canal"],
            miniatura_url=video["miniatura_url"],
            ordem=proxima_ordem,
        ))
        existentes.add(video["youtube_id"])
        proxima_ordem += 1

    db.commit()
    return detalhar_curso(curso_id, db, usuario)


@router.delete("/{curso_id}/aulas/{aula_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_aula(
    curso_id: UUID,
    aula_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    curso = _buscar_curso_da_loja(curso_id, usuario, db)

    aula = next((a for a in curso.aulas if a.id == aula_id), None)
    if aula is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada"
        )

    db.delete(aula)
    db.flush()

    # Fecha o buraco na numeração para a ordem não ficar com saltos.
    for posicao, restante in enumerate(
        sorted((a for a in curso.aulas if a.id != aula_id), key=lambda a: a.ordem)
    ):
        restante.ordem = posicao

    db.commit()
    return None
