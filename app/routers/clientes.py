from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def listar_clientes():
    return {"mensagem": "Módulo Clientes — em desenvolvimento"}


