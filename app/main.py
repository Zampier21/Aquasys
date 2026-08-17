from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, aquarios, peixes, clientes, fichas, cursos

# ─── Criação da aplicação ─────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API do sistema AquaSys — gerenciamento de aquários e serviços de manutenção",
    docs_url="/docs",       
    redoc_url="/redoc",     
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #Lembrete, substituir pelo domonio quando tiver
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Registro dos routers ─────────────────────────────
app.include_router(auth.router,      prefix="/auth",      tags=["Autenticação"])
app.include_router(aquarios.router,  prefix="/aquarios",  tags=["Aquários"])
app.include_router(peixes.router,    prefix="/peixes",    tags=["Peixes"])
app.include_router(clientes.router,  prefix="/clientes",  tags=["Clientes"])
app.include_router(fichas.router,    prefix="/fichas",    tags=["Fichas de Manutenção"])
app.include_router(cursos.router,    prefix="/cursos",    tags=["Cursos"])


# ─── Rota raiz — health check ─────────────────────────
@app.get("/", tags=["Status"])
def root():
    return {
        "app": settings.APP_NAME,
        "versao": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
    }