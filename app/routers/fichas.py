from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def listar_fichas():
    return {"mensagem": "Módulo Fichas — em desenvolvimento"}