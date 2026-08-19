import unicodedata
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.database import get_db
from app.models.aquario import Aquario
from app.models.especie import AquarioEspecie, CompatibEspecie, Especie
from app.models.usuario import Usuario
from app.schemas.especie import (
    AnaliseResponse, CompatividadeResumo, EspecieCreate, EspecieResponse,
    HabitanteResponse, PovoamentoCreate, PovoamentoUpdate,
)
from app.services.compatibilidade import (
    MOTIVOS_IMPEDITIVOS, Nivel, avaliar_adicao, avaliar_especie_no_aquario,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════
# BUSCA TOLERANTE
# ═══════════════════════════════════════════════════════
def _normalizar(texto: str) -> str:
    """
    Deixa o texto em minúsculas e remove acentos.

    'Acará Bandeira' vira 'acara bandeira', permitindo que o cliente
    encontre a espécie mesmo digitando sem acento.
    """
    sem_acento = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def _filtro_busca(query, termo_bruto: str):
    """
    Aplica busca por palavras soltas, em qualquer ordem.

    Cada palavra digitada precisa aparecer em algum dos campos de nome.
    Assim 'tetra neon', 'neon tetra' e 'neon' encontram a mesma espécie.
    """
    termos = [t for t in _normalizar(termo_bruto).split() if t]
    if not termos:
        return query

    # Junta os três campos de nome num único texto pesquisável
    campo = func.unaccent(
        func.lower(
            func.concat_ws(
                " ",
                Especie.nome_comum,
                Especie.nome_cientifico,
                Especie.nomes_alternativos,
            )
        )
    )

    condicoes = [campo.like(f"%{termo}%") for termo in termos]
    return query.filter(and_(*condicoes))


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
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


def _buscar_especie(especie_id: UUID, db: Session) -> Especie:
    especie = db.query(Especie).filter(Especie.id == especie_id).first()
    if especie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espécie não encontrada")
    return especie


def _habitantes(aquario_id: UUID, db: Session, ignorar: Optional[UUID] = None):
    """
    Espécies presentes no aquário como lista de (Especie, quantidade).

    `ignorar` exclui uma espécie da análise — usado ao editar a quantidade
    de uma espécie que já está no aquário, para não comparar com ela mesma.
    """
    query = (
        db.query(AquarioEspecie, Especie)
        .join(Especie, Especie.id == AquarioEspecie.especie_id)
        .filter(AquarioEspecie.aquario_id == aquario_id)
    )
    if ignorar:
        query = query.filter(AquarioEspecie.especie_id != ignorar)

    return [(especie, item.quantidade) for item, especie in query.all()]


def _montar_habitante(item: AquarioEspecie, especie: Especie) -> HabitanteResponse:
    return HabitanteResponse(
        id=item.id,
        especie_id=especie.id,
        nome_comum=especie.nome_comum,
        nome_cientifico=especie.nome_cientifico,
        quantidade=item.quantidade,
        tamanho_adulto_cm=especie.tamanho_adulto_cm,
        comportamento=especie.comportamento,
        adicionado_em=item.adicionado_em,
    )


# ═══════════════════════════════════════════════════════
# CATÁLOGO
# ═══════════════════════════════════════════════════════
@router.get("/", response_model=List[EspecieResponse])
def listar_especies(
    busca: Optional[str] = Query(
        default=None,
        description="Nome comum, científico ou popular. Aceita palavras em qualquer ordem e sem acento.",
    ),
    tipo_agua: Optional[str] = Query(
        default=None, description="doce | salobra | marinho"
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Catálogo de espécies, com busca tolerante a variações de escrita."""
    query = db.query(Especie).filter(Especie.ativo == True)  # noqa: E712

    if busca:
        query = _filtro_busca(query, busca)

    if tipo_agua and tipo_agua.strip():
        # Comparação sem depender de maiúsculas nem acentos
        query = query.filter(
            func.unaccent(func.lower(Especie.tipo_agua)) == _normalizar(tipo_agua)
        )

    return query.order_by(Especie.nome_comum).all()


# ═══════════════════════════════════════════════════════
# POVOAMENTO — habitantes de cada aquário
# Declarado antes de /{especie_id} para não haver conflito de rota
# ═══════════════════════════════════════════════════════
@router.get("/aquario/{aquario_id}", response_model=List[HabitanteResponse])
def listar_habitantes(
    aquario_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Espécies que já vivem neste aquário."""
    _buscar_aquario(aquario_id, usuario, db)

    linhas = (
        db.query(AquarioEspecie, Especie)
        .join(Especie, Especie.id == AquarioEspecie.especie_id)
        .filter(AquarioEspecie.aquario_id == aquario_id)
        .order_by(Especie.nome_comum)
        .all()
    )

    return [_montar_habitante(item, especie) for item, especie in linhas]


@router.post(
    "/aquario/{aquario_id}",
    response_model=HabitanteResponse,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_ao_aquario(
    aquario_id: UUID,
    dados: PovoamentoCreate,
    confirmar: bool = Query(
        default=False,
        description="Necessário quando a análise devolve requer_confirmacao",
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Adiciona uma espécie ao aquário.

    A análise de compatibilidade roda antes de gravar:

      bloqueado           → HTTP 409, não grava de jeito nenhum
      requer_confirmacao  → HTTP 409 se confirmar=false; grava se confirmar=true
      liberado            → grava direto
    """
    aquario = _buscar_aquario(aquario_id, usuario, db)
    especie = _buscar_especie(dados.especie_id, db)

    ja_existe = (
        db.query(AquarioEspecie)
        .filter(
            AquarioEspecie.aquario_id == aquario_id,
            AquarioEspecie.especie_id == dados.especie_id,
        )
        .first()
    )
    if ja_existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta espécie já está no aquário. Edite a quantidade.",
        )

    analise = avaliar_adicao(
        nova=especie,
        quantidade=dados.quantidade,
        aquario=aquario,
        habitantes=_habitantes(aquario_id, db),
        excecoes=_carregar_excecoes(db),
    )

    if analise["decisao"] == "bloqueado":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "mensagem": "Espécie incompatível com este aquário",
                "decisao": "bloqueado",
                "motivos": analise["motivos_bloqueio"],
            },
        )

    if analise["decisao"] == "requer_confirmacao" and not confirmar:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "mensagem": "Existem ressalvas — confirme para prosseguir",
                "decisao": "requer_confirmacao",
                "ressalvas": analise["ressalvas"],
            },
        )

    item = AquarioEspecie(
        aquario_id=aquario_id,
        especie_id=dados.especie_id,
        quantidade=dados.quantidade,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return _montar_habitante(item, especie)


@router.put("/aquario/{aquario_id}/{item_id}", response_model=HabitanteResponse)
def atualizar_quantidade(
    aquario_id: UUID,
    item_id: UUID,
    dados: PovoamentoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Ajusta a quantidade de uma espécie já presente no aquário."""
    _buscar_aquario(aquario_id, usuario, db)

    item = (
        db.query(AquarioEspecie)
        .filter(
            AquarioEspecie.id == item_id,
            AquarioEspecie.aquario_id == aquario_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espécie não está neste aquário")

    item.quantidade = dados.quantidade
    db.commit()
    db.refresh(item)

    return _montar_habitante(item, _buscar_especie(item.especie_id, db))


@router.delete("/aquario/{aquario_id}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_do_aquario(
    aquario_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Remove uma espécie do aquário."""
    _buscar_aquario(aquario_id, usuario, db)

    item = (
        db.query(AquarioEspecie)
        .filter(
            AquarioEspecie.id == item_id,
            AquarioEspecie.aquario_id == aquario_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espécie não está neste aquário")

    db.delete(item)
    db.commit()
    return None


# ═══════════════════════════════════════════════════════
# COMPATIBILIDADE
# ═══════════════════════════════════════════════════════
@router.get("/compativeis/{aquario_id}", response_model=List[CompatividadeResumo])
def especies_compativeis(
    aquario_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Percorre o catálogo e classifica cada espécie para este aquário.

    Alimenta os selos Ideal / Atenção / Evitar na tela de Peixes.
    Considera também as espécies já presentes no aquário.
    """
    aquario = _buscar_aquario(aquario_id, usuario, db)
    habitantes = _habitantes(aquario_id, db)
    excecoes = _carregar_excecoes(db)

    resposta = []
    for especie in db.query(Especie).filter(Especie.ativo == True).all():  # noqa: E712
        analise = avaliar_adicao(
            nova=especie,
            quantidade=especie.cardume_minimo or 1,
            aquario=aquario,
            habitantes=habitantes,
            excecoes=excecoes,
        )
        resposta.append(
            CompatividadeResumo(
                especie_id=str(especie.id),
                nome_comum=especie.nome_comum,
                nivel=analise["nivel"],
                decisao=analise["decisao"],
                avisos=[a["mensagem"] for a in analise["avisos"]],
            )
        )

    return resposta


@router.get("/{especie_id}/aquario/{aquario_id}", response_model=AnaliseResponse)
def compatibilidade_com_aquario(
    especie_id: UUID,
    aquario_id: UUID,
    quantidade: int = Query(default=1, gt=0),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """
    Analisa se a espécie pode entrar no aquário, na quantidade informada.

    Devolve uma das três decisões: liberado, requer_confirmacao ou bloqueado.
    """
    especie = _buscar_especie(especie_id, db)
    aquario = _buscar_aquario(aquario_id, usuario, db)

    return avaliar_adicao(
        nova=especie,
        quantidade=quantidade,
        aquario=aquario,
        habitantes=_habitantes(aquario_id, db, ignorar=especie_id),
        excecoes=_carregar_excecoes(db),
    )


@router.get("/{especie_id}", response_model=EspecieResponse)
def detalhar_especie(
    especie_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    return _buscar_especie(especie_id, db)


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