from app.models.alerta import Alerta
from app.models.curso import Aula, Curso, ProgressoAula, ProgressoCurso
from app.models.dica import Dica
from app.models.sessao import Sessao
from app.models.usuario import Usuario
from app.models.aquario import Aquario, ParametrosAgua
from app.models.especie import (
    AquarioEspecie,
    CompatibEspecie,
    Especie,
)
from app.models.ficha import (
    ChecklistEquipamento,
    ClienteManutencao,
    DescricaoManutencao,
    FichaManutencao,
    TesteAgua,
)

__all__ = [
    "Usuario",
    "Sessao",
    "Alerta",
    "Dica",
    "Curso",
    "Aula",
    "ProgressoAula",
    "ProgressoCurso",
    "Aquario",
    "ParametrosAgua",
    "Especie",
    "CompatibEspecie",
    "AquarioEspecie",
    "FichaManutencao",
    "ClienteManutencao",
    "ChecklistEquipamento",
    "TesteAgua",
    "DescricaoManutencao",
]
