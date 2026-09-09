import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decodificar_token
from app.database import get_db
from app.models.usuario import Usuario

# Lê o header: Authorization: Bearer <token>
security = HTTPBearer()


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    erro_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decodificar_token(credenciais.credentials)
    if payload is None:
        raise erro_credenciais

    usuario_id = payload.get("sub")
    if usuario_id is None:
        raise erro_credenciais

    try:
        usuario_uuid = uuid.UUID(usuario_id)
    except ValueError:
        raise erro_credenciais

    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_uuid, Usuario.ativo == True)  # noqa: E712
        .first()
    )

    if usuario is None:
        raise erro_credenciais

    return usuario