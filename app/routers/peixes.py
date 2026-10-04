import unicodedata
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, Header, HTTPException, Query, Request, Response, status,
)
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.database import get_db
from app.routers.aquarios import regerar_alertas
from app.models.aquario import Aquario
from app.models.especie import (
    AquarioEspecie, CompatibEspecie, Especie, EspecieImagem,
)
from app.models.usuario import Usuario
from app.schemas.especie import (
    AnaliseResponse, CandidatoImportacao, CompatividadeResumo, EspecieCreate,
    EspecieResponse, ImportacaoResponse, ItemImportado, ResumoGravacao,
    VariedadeResumo,
    HabitanteResponse, PovoamentoCreate, PovoamentoUpdate,
)
from app.services import importacao as svc_importacao
from app.services import variedades as svc_variedades
from app.services.compatibilidade import (
    MOTIVOS_IMPEDITIVOS, Nivel, avaliar_adicao, avaliar_especie_no_aquario,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════
# BUSCA TOLERANTE
# ═══════════════════════════════════════════════════════
def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


# Comparação sem acento do lado do banco, por `translate` em vez da
# extensão `unaccent`.
#
# A extensão fazia o mesmo e de forma mais geral, mas custava uma
# dependência de instalação: todo banco novo precisava de
# `CREATE EXTENSION unaccent`, o que exige privilégio de superusuário e
# é um passo a mais em cada ambiente. Pior, ela é uma biblioteca
# carregada pelo servidor, e no Windows com Controle Inteligente de
# Aplicativos ligado o `unaccent.dll` não tem assinatura e é barrado:
# a busca do catálogo respondia erro 500 na máquina de desenvolvimento
# enquanto funcionava em produção.
#
# O `translate` é função embutida do PostgreSQL, sem biblioteca externa
# e sem extensão. Cobre menos que a extensão, que trata todo o Unicode,
# e cobre o que existe aqui: nome popular em português e nome
# científico em latim. As duas caixas entram no mapa porque `lower()`
# sob localidade C não rebaixa letra acentuada.
_COM_ACENTO = (
    "áàâãäåéèêëíìîïóòôõöøúùûüçñýÿ"
    "ÁÀÂÃÄÅÉÈÊËÍÌÎÏÓÒÔÕÖØÚÙÛÜÇÑÝŸ"
)
_SEM_ACENTO = (
    "aaaaaaeeeeiiiioooooouuuucnyy"
    "aaaaaaeeeeiiiioooooouuuucnyy"
)


def _sem_acento(coluna):
    """A coluna em minúsculas e sem acento, para comparar com o termo."""
    return func.translate(func.lower(coluna), _COM_ACENTO, _SEM_ACENTO)


def _filtro_busca(query, termo_bruto: str):
    termos = [t for t in _normalizar(termo_bruto).split() if t]
    if not termos:
        return query

    # Junta os três campos de nome num único texto pesquisável
    campo = _sem_acento(
        func.concat_ws(
            " ",
            Especie.nome_comum,
            Especie.nome_cientifico,
            Especie.nomes_alternativos,
        )
    )

    condicoes = [campo.like(f"%{termo}%") for termo in termos]
    return query.filter(and_(*condicoes))


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
_CACHE_DA_IMAGEM = "public, max-age=2592000"


def _creditos_das_imagens(db: Session, ids=None) -> dict:
    consulta = db.query(
        EspecieImagem.especie_id, EspecieImagem.autor, EspecieImagem.licenca
    )
    if ids is not None:
        if not ids:
            return {}
        consulta = consulta.filter(EspecieImagem.especie_id.in_(ids))

    return {
        especie_id: (autor, licenca)
        for especie_id, autor, licenca in consulta.all()
    }


def _tem_imagem(especie_id, db: Session) -> bool:
    return (
        db.query(EspecieImagem.especie_id)
        .filter(EspecieImagem.especie_id == especie_id)
        .first()
        is not None
    )


def _credito_em_texto(autor, licenca):
    if not autor and not licenca:
        return None
    if not autor:
        return licenca
    if not licenca:
        return autor
    return f"{autor} ({licenca})"


def _url_imagem(especie_id, miniatura: bool = False) -> str:
    sufixo = "?tamanho=miniatura" if miniatura else ""
    return f"/peixes/{especie_id}/imagem{sufixo}"


def _montar_variedade(
    variedade: Especie, base: Especie, creditos: dict
) -> VariedadeResumo:
    """Variedade como ela aparece dentro do card da base."""
    resumo = VariedadeResumo(
        id=variedade.id,
        nome_comum=variedade.nome_comum,
        nome_curto=svc_variedades.nome_curto(variedade, base),
    )
    credito = creditos.get(variedade.id)
    if credito is not None:
        resumo.imagem = _url_imagem(variedade.id)
        resumo.imagem_miniatura = _url_imagem(variedade.id, miniatura=True)
        resumo.imagem_credito = _credito_em_texto(*credito)
    return resumo


def _montar_especie(
    especie: Especie, creditos: dict, variedades: Optional[list] = None
) -> EspecieResponse:
    """Espécie do catálogo, com os caminhos da foto quando ela existe."""
    resposta = EspecieResponse.model_validate(especie)

    credito = creditos.get(especie.id)
    if credito is not None:
        resposta.imagem = _url_imagem(especie.id)
        resposta.imagem_miniatura = _url_imagem(especie.id, miniatura=True)
        resposta.imagem_credito = _credito_em_texto(*credito)

    # As variedades vêm de fora porque quem lista o catálogo já as
    # carregou em bloco, junto com os créditos das fotos — buscá-las
    # aqui, uma espécie por vez, traria de volta o N+1 que a listagem
    # existe para evitar.
    resposta.variedades = [
        _montar_variedade(v, especie, creditos) for v in (variedades or [])
    ]
    return resposta


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
        .filter(
            Aquario.id == aquario_id,
            Aquario.usuario_id == usuario.id,
            Aquario.ativo.is_(True),
        )
        .first()
    )
    if aquario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aquário não encontrado")
    return aquario


def _loja_do_usuario(usuario: Usuario):
    """A loja a que a conta pertence: ela mesma, se for empresarial."""
    return usuario.id if usuario.tipo == "dono" else usuario.dono_id


def _visiveis_para(usuario: Usuario):
    """Catálogo curado mais o rascunho da loja do usuário.

    O cliente enxerga o que a sua loja importou, e é esse o ponto de a
    loja subir a lista: o aquarista ver o que ela tem antes de escolher.
    """
    loja = _loja_do_usuario(usuario)
    if loja is None:
        return Especie.dono_id.is_(None)
    return (Especie.dono_id.is_(None)) | (Especie.dono_id == loja)


def _buscar_especie(especie_id: UUID, db: Session) -> Especie:
    especie = db.query(Especie).filter(Especie.id == especie_id).first()
    if especie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espécie não encontrada")
    return especie


def _habitantes(aquario_id: UUID, db: Session, ignorar: Optional[UUID] = None):
    query = (
        db.query(AquarioEspecie, Especie)
        .join(Especie, Especie.id == AquarioEspecie.especie_id)
        .filter(AquarioEspecie.aquario_id == aquario_id)
    )
    if ignorar:
        query = query.filter(AquarioEspecie.especie_id != ignorar)

    return [(especie, item.quantidade) for item, especie in query.all()]


def _reavaliar(aquario, db: Session) -> None:
    db.flush()
    db.expire(aquario, ["habitantes"])
    regerar_alertas(aquario, db)


def _montar_habitante(
    item: AquarioEspecie, especie: Especie, tem_imagem: bool = False
) -> HabitanteResponse:
    return HabitanteResponse(
        id=item.id,
        especie_id=especie.id,
        nome_comum=especie.nome_comum,
        nome_cientifico=especie.nome_cientifico,
        quantidade=item.quantidade,
        tamanho_adulto_cm=especie.tamanho_adulto_cm,
        comportamento=especie.comportamento,
        imagem_miniatura=(
            _url_imagem(especie.id, miniatura=True) if tem_imagem else None
        ),
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
    """Catálogo de espécies, com busca tolerante a variações de escrita.

    Lista apenas as espécies-base. As variedades — Tetra Neon Negro
    Albino, Acará Bandeira Leopardo Azul — vão dentro do card da base,
    para que oito acarás-bandeira não ocupem oito linhas de uma lista
    que o usuário percorre com o polegar.
    """
    query = db.query(Especie).filter(
        Especie.ativo == True,  # noqa: E712
        Especie.variante_de_id.is_(None),
        _visiveis_para(usuario),
    )

    if busca:
        query = _filtro_busca(query, busca)

    if tipo_agua and tipo_agua.strip():
        # Comparação sem depender de maiúsculas nem acentos
        query = query.filter(
            _sem_acento(Especie.tipo_agua) == _normalizar(tipo_agua)
        )

    especies = query.order_by(Especie.nome_comum).all()

    # Buscar "albino" tem que achar alguma coisa. Como a variedade não
    # aparece na lista, procura-se também entre elas e devolve-se a base
    # correspondente — quem procurou encontra o card certo, já com a
    # variedade dentro.
    if busca:
        das_variedades = _filtro_busca(
            db.query(Especie).filter(
                Especie.ativo == True,  # noqa: E712
                Especie.variante_de_id.isnot(None),
            ),
            busca,
        ).all()
        ja_listadas = {e.id for e in especies}
        faltando = {
            v.variante_de_id for v in das_variedades
            if v.variante_de_id not in ja_listadas
        }
        if faltando:
            especies += (
                db.query(Especie)
                .filter(Especie.id.in_(faltando), Especie.ativo == True)  # noqa: E712
                .all()
            )
            especies.sort(key=lambda e: (e.nome_comum or "").lower())

    # As variedades de todas as espécies numa consulta só, e não uma por
    # card: é o mesmo motivo pelo qual os créditos das fotos são
    # carregados em bloco logo abaixo.
    por_base = {}
    if especies:
        variedades = (
            db.query(Especie)
            .filter(
                Especie.variante_de_id.in_([e.id for e in especies]),
                Especie.ativo == True,  # noqa: E712
            )
            .order_by(Especie.nome_comum)
            .all()
        )
        for v in variedades:
            por_base.setdefault(v.variante_de_id, []).append(v)

    todos_ids = [e.id for e in especies] + [
        v.id for lista in por_base.values() for v in lista
    ]
    creditos = _creditos_das_imagens(db, todos_ids)
    return [
        _montar_especie(e, creditos, por_base.get(e.id))
        for e in especies
    ]


# ═══════════════════════════════════════════════════════
# IMAGENS DO CATÁLOGO
# ═══════════════════════════════════════════════════════
@router.post("/importar", response_model=ImportacaoResponse)
async def importar_lista(
    request: Request,
    aplicar: bool = Query(
        default=False,
        description="Falso só confere; verdadeiro grava a lista da loja.",
    ),
    buscar: bool = Query(
        default=True,
        description="Procurar o nome científico dos peixes desconhecidos.",
    ),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Confere uma lista de peixes em CSV contra o catálogo.

    O corpo da requisição é o arquivo em si, sem envelope de formulário:
    evita a dependência de multipart e deixa a detecção de codificação
    aqui, que é onde dá para tentar UTF-8, UTF-8 com marcador do Excel e
    as tabelas do Windows em ordem.

    Com `aplicar` falso, nada é gravado: volta só o relatório do que
    casou, do que ficou ambíguo e do que não existe. É o que a tela
    mostra antes de a loja confirmar.

    Com `aplicar` verdadeiro, o que casou entra no estoque da loja e o
    que faltava vira espécie dela, marcada como não revisada. O ambíguo
    fica de fora: escolher entre Acará Bandeira e Acará Disco por conta
    própria colocaria no estoque um peixe que a loja não vende.
    """
    if usuario.tipo != "dono":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas contas empresariais podem importar listas",
        )

    try:
        nomes = svc_importacao.ler_nomes(await request.body())
        casados = svc_importacao.casar(nomes, db, dono=usuario)
    except svc_importacao.ArquivoInvalido as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)
        )

    gravacao = None
    if aplicar:
        gravacao = svc_importacao.aplicar(casados, db, usuario, buscar=buscar)

    itens = []
    for c in casados:
        base = c.especie.base if c.especie is not None else None
        itens.append(
            ItemImportado(
                linha=c.linha,
                nome_lido=c.nome_lido,
                vezes=c.vezes,
                situacao=c.situacao,
                como=c.como,
                especie_id=c.especie.id if c.especie else None,
                nome_comum=c.especie.nome_comum if c.especie else None,
                nome_cientifico=c.especie.nome_cientifico if c.especie else None,
                variedade_de=base.nome_comum if base is not None else None,
                candidatos=[
                    CandidatoImportacao(
                        id=e.id,
                        nome_comum=e.nome_comum,
                        nome_cientifico=e.nome_cientifico,
                    )
                    for e in c.candidatos
                ],
                sugestoes=c.sugestoes,
            )
        )

    def quantos(situacao: str) -> int:
        return sum(1 for i in itens if i.situacao == situacao)

    return ImportacaoResponse(
        total_linhas=len(nomes),
        total_nomes=len(itens),
        encontrados=quantos("encontrado"),
        ambiguos=quantos("ambiguo"),
        nao_encontrados=quantos("nao_encontrado"),
        criados=quantos("criado"),
        aplicado=aplicar,
        gravacao=ResumoGravacao(**gravacao) if gravacao else None,
        itens=itens,
    )


@router.get("/{especie_id}/imagem")
def imagem_da_especie(
    especie_id: UUID,
    tamanho: str = Query(
        default="completa",
        pattern="^(completa|miniatura)$",
        description="miniatura = quadrada, para a lista; completa = card aberto",
    ),
    if_none_match: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    imagem = (
        db.query(EspecieImagem)
        .filter(EspecieImagem.especie_id == especie_id)
        .first()
    )
    if imagem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espécie sem foto")
    etag = f'"{imagem.hash}-{tamanho}"'
    cabecalhos = {"ETag": etag, "Cache-Control": _CACHE_DA_IMAGEM}

    if if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=cabecalhos)

    conteudo = imagem.miniatura if tamanho == "miniatura" else imagem.completa
    return Response(
        content=bytes(conteudo),
        media_type=imagem.mime,
        headers=cabecalhos,
    )


# ═══════════════════════════════════════════════════════
# POVOAMENTO — habitantes de cada aquário
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

    com_foto = _creditos_das_imagens(db, [especie.id for _, especie in linhas])
    return [
        _montar_habitante(item, especie, especie.id in com_foto)
        for item, especie in linhas
    ]


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
    _reavaliar(aquario, db)
    db.commit()
    db.refresh(item)

    return _montar_habitante(item, especie, _tem_imagem(especie.id, db))


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

    especie = _buscar_especie(item.especie_id, db)
    return _montar_habitante(item, especie, _tem_imagem(especie.id, db))


@router.delete("/aquario/{aquario_id}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_do_aquario(
    aquario_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Remove uma espécie do aquário."""
    aquario = _buscar_aquario(aquario_id, usuario, db)

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
    _reavaliar(aquario, db)
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
    aquario = _buscar_aquario(aquario_id, usuario, db)
    habitantes = _habitantes(aquario_id, db)
    excecoes = _carregar_excecoes(db)

    resposta = []
    # Só as bases: a variedade tem a mesma biologia e produziria uma
    # linha idêntica na lista de compatíveis.
    candidatas = db.query(Especie).filter(
        Especie.ativo == True,  # noqa: E712
        Especie.variante_de_id.is_(None),
    ).all()
    for especie in candidatas:
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
    """Cadastro manual de espécie, no catálogo da própria loja.

    A espécie nasce com dono. Antes da migração 012 não havia catálogo
    por loja e tudo era global, então esta rota gravava `dono_id` nulo:
    depois de 012, isso seria uma loja escrevendo no catálogo que todas
    as outras enxergam. O caminho da importação já cria com dono, e
    este passa a fazer o mesmo.

    Promover uma espécie da loja para o catálogo curado é decisão de
    quem mantém o AquaSys, e não acontece por aqui.
    """
    if usuario.tipo != "dono":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Apenas o perfil empresarial pode cadastrar espécies",
        )

    especie = Especie(**dados.model_dump(), dono_id=usuario.id)
    db.add(especie)
    db.commit()
    db.refresh(especie)
    return especie