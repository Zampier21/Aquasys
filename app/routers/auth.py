from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import limitador
from app.core.config import settings
from app.core.documento import somente_digitos, tipo_documento
from app.core.security import (
    criar_refresh,
    criar_token,
    hash_do_refresh,
    hash_senha,
    verificar_senha,
)
from app.database import get_db
from app.models.sessao import Sessao
from app.models.usuario import Usuario

router = APIRouter()

# Hash descartável, conferido quando o documento não existe. Sem ele, a
# resposta para conta inexistente volta em microssegundos e a de senha
# errada leva o tempo do bcrypt: a diferença diz de fora quais CPF e
# CNPJ estão cadastrados. Calculado uma vez, na importação do módulo.
_HASH_DE_DESCARTE = hash_senha("conta-que-nao-existe")


class LoginInput(BaseModel):
    # Campo a mais no corpo é recusado: o cliente que manda o que a
    # rota não pede está desalinhado do contrato, e engolir em silêncio
    # esconde o erro.
    model_config = ConfigDict(extra="forbid")

    cpf_cnpj: str = Field(..., max_length=32)
    senha: str = Field(..., max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    # Vai junto no login e em toda renovação. O aparelho guarda e usa
    # para pedir um novo acesso quando o atual vencer, sem senha.
    refresh_token: str
    token_type: str = "bearer"
    tipo_usuario: str
    nome: str
    documento: str
    avatar: str | None = None


class RenovarInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., max_length=200)


def abrir_sessao(db: Session, usuario: Usuario) -> str:
    """Cria uma sessão e devolve o token de renovação em texto puro.

    É a única vez que o token existe fora do aparelho. Daqui em diante
    o servidor só conhece o hash.
    """
    token, hash_token = criar_refresh()
    db.add(Sessao(
        usuario_id=usuario.id,
        hash=hash_token,
        expira_em=datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    ))
    return token


def resposta_de_entrada(
    db: Session, usuario: Usuario, documento: str
) -> TokenResponse:
    """Monta o par de tokens. Serve ao login e à renovação."""
    return TokenResponse(
        access_token=criar_token({
            "sub": str(usuario.id),
            "tipo": usuario.tipo,
        }),
        refresh_token=abrir_sessao(db, usuario),
        tipo_usuario=usuario.tipo,
        nome=usuario.nome,
        documento=documento,
        avatar=usuario.avatar,
    )


def buscar_por_documento(db: Session, documento: str) -> Usuario | None:
    digitos = somente_digitos(documento)
    if not digitos:
        return None

    # regexp_replace do Postgres tira a máscara do lado do banco.
    cpf_cnpj_limpo = func.regexp_replace(Usuario.cpf_cnpj, r"\D", "", "g")

    return (
        db.query(Usuario)
        .filter(cpf_cnpj_limpo == digitos, Usuario.ativo.is_(True))
        .first()
    )


@router.post("/login", response_model=TokenResponse)
def login(
    dados: LoginInput,
    request: Request,
    db: Session = Depends(get_db),
):
    digitos = somente_digitos(dados.cpf_cnpj)
    tipo = tipo_documento(digitos)

    # O teto é conferido antes de qualquer trabalho, e vale também para
    # o documento malformado: caso contrário bastaria mandar lixo para
    # medir o servidor de graça.
    limitador.conferir_login(request, digitos or None)

    if tipo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe um CPF (11 dígitos) ou CNPJ (14 dígitos)",
        )

    usuario = buscar_por_documento(db, digitos)

    # A senha é sempre conferida, mesmo sem usuário, para que as duas
    # respostas custem o mesmo tempo.
    confere = verificar_senha(
        dados.senha, usuario.senha_hash if usuario else _HASH_DE_DESCARTE
    )

    if not usuario or not confere:
        # A mensagem não diz qual dos dois errou. Dizer "esse CPF não
        # existe" entregaria a lista de clientes da loja a quem
        # tentasse documentos em sequência.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF/CNPJ ou senha incorretos",
        )

    limitador.perdoar_login(request, digitos)

    resposta = resposta_de_entrada(db, usuario, tipo)
    db.commit()
    return resposta


@router.post("/renovar", response_model=TokenResponse)
def renovar(dados: RenovarInput, db: Session = Depends(get_db)):
    """Troca um token de renovação válido por um par novo.

    A sessão é rotacionada a cada uso: o token apresentado é marcado
    como usado e um novo é emitido. Isso encurta a janela de um token
    que vaze e, principalmente, torna o reúso detectável.

    Se chegar um token que já foi usado ou revogado, existem duas
    cópias dele em circulação e não há como saber qual é a do dono.
    A resposta é derrubar todas as sessões daquela conta: o usuário
    legítimo refaz o login, e quem copiou fica de fora.
    """
    sessao = (
        db.query(Sessao)
        .filter(Sessao.hash == hash_do_refresh(dados.refresh_token))
        .first()
    )

    recusa = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão expirada. Faça login novamente.",
    )

    if sessao is None:
        raise recusa

    if sessao.usado_em is not None or sessao.revogado_em is not None:
        agora = datetime.utcnow()
        db.query(Sessao).filter(
            Sessao.usuario_id == sessao.usuario_id,
            Sessao.revogado_em.is_(None),
        ).update({"revogado_em": agora}, synchronize_session=False)
        db.commit()
        raise recusa

    if sessao.expira_em <= datetime.utcnow():
        raise recusa

    usuario = db.query(Usuario).filter(
        Usuario.id == sessao.usuario_id, Usuario.ativo.is_(True)
    ).first()
    if usuario is None:
        # Conta desativada depois de a sessão ser aberta.
        raise recusa

    sessao.usado_em = datetime.utcnow()
    resposta = resposta_de_entrada(
        db, usuario, tipo_documento(somente_digitos(usuario.cpf_cnpj)) or ""
    )
    db.commit()
    return resposta


@router.post("/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair(dados: RenovarInput, db: Session = Depends(get_db)):
    """Encerra a sessão daquele aparelho.

    Não exige token de acesso: quem está saindo pode justamente estar
    com o acesso vencido, que é quando sair importa. Apresentar o
    token de renovação já prova a posse da sessão, e o efeito é só
    invalidá-la.

    Responde 204 mesmo para token desconhecido. Dizer "essa sessão não
    existe" permitiria sondar tokens de fora.
    """
    db.query(Sessao).filter(
        Sessao.hash == hash_do_refresh(dados.refresh_token),
        Sessao.revogado_em.is_(None),
    ).update({"revogado_em": datetime.utcnow()}, synchronize_session=False)
    db.commit()
    return None
