from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def listar_cursos():
    return {"mensagem": "Módulo Cursos — em desenvolvimento"}