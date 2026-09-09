from app.core.console import preparar

preparar()

from sqlalchemy import func

from app.core.documento import formatar_documento, somente_digitos
from app.core.security import hash_senha
from app.database import SessionLocal
from app.models.aquario import Aquario, ParametrosAgua
from app.models.especie import AquarioEspecie, Especie
from app.models.ficha import ClienteManutencao, FichaManutencao
from app.models.usuario import Usuario
from app.routers.aquarios import regerar_alertas

LOJA = {
    "nome": "AquaVida Aquarismo",
    "documento": "11222333000181",
    "senha": "aquasys123",
}

CLIENTE = {
    "nome": "Weslley Zampier",
    "documento": "12345678909",
    "senha": "cliente123",
    "email": "cliente@aquasys.com",
}

# (nome, tipo, litros, temperatura, ph, amonia, nitrito, nitrato, peixes)
AQUARIOS_LOJA = [
    ("Display da Loja", "comunitario", 200, 26.0, 6.8, 0, 0, 10,
     [("Neon Tetra", 12), ("Coridora Panda", 6)]),
    ("Marinho Exposição", "marinho", 300, 26.0, 8.2, 0, 0, 5,
     [("Palhaço", 2)]),
]

AQUARIOS_CLIENTE = [
    # pH 7,3 num comunitário fica fora da faixa (6,5–7,0): gera alerta.
    ("Meu Comunitário", "comunitario", 100, 26.0, 7.3, 0, 0, 15,
     [("Neon Tetra", 8), ("Betta", 1)]),
    ("Plantado da Sala", "plantado", 60, 25.0, 6.5, 0, 0, 20,
     [("Molinésia", 4)]),
]


def garantir_loja(db) -> Usuario:
    limpo = func.regexp_replace(Usuario.cpf_cnpj, r"\D", "", "g")
    loja = db.query(Usuario).filter(limpo == LOJA["documento"]).first()

    if loja is None:
        loja = Usuario(
            nome=LOJA["nome"],
            cpf_cnpj=formatar_documento(LOJA["documento"]),
            senha_hash=hash_senha(LOJA["senha"]),
            tipo="dono",
            dono_id=None,
            ativo=True,
        )
        db.add(loja)
        db.flush()
        print(f'+ loja "{loja.nome}" ({loja.cpf_cnpj})')
    else:
        print(f'  loja "{loja.nome}" já existe')
    return loja


def garantir_cliente(db, loja: Usuario) -> Usuario:
    limpo = func.regexp_replace(Usuario.cpf_cnpj, r"\D", "", "g")
    cliente = db.query(Usuario).filter(limpo == CLIENTE["documento"]).first()

    if cliente is None:
        cliente = Usuario(
            nome=CLIENTE["nome"],
            cpf_cnpj=formatar_documento(CLIENTE["documento"]),
            senha_hash=hash_senha(CLIENTE["senha"]),
            tipo="cliente",
            dono_id=loja.id,  # o CHECK do banco exige dono para 'cliente'
            email=CLIENTE["email"],
            ativo=True,
        )
        db.add(cliente)
        db.flush()
        print(f'+ cliente "{cliente.nome}" ({cliente.cpf_cnpj})')
    else:
        print(f'  cliente "{cliente.nome}" já existe')
    return cliente


def garantir_aquarios(db, dono: Usuario, receitas: list) -> int:
    especies = {e.nome_comum: e for e in db.query(Especie).all()}
    criados = 0

    for (nome, tipo, litros, temp, ph, amonia,
         nitrito, nitrato, peixes) in receitas:
        existente = (
            db.query(Aquario)
            .filter(Aquario.usuario_id == dono.id, Aquario.nome == nome)
            .first()
        )
        if existente is not None:
            continue

        aquario = Aquario(
            usuario_id=dono.id,
            nome=nome,
            tipo=tipo,
            volume_litros=litros,
            temperatura=temp,
            ph=ph,
        )
        db.add(aquario)
        db.flush()

        db.add(ParametrosAgua(
            aquario_id=aquario.id,
            amonia_ppm=amonia,
            nitrito_ppm=nitrito,
            nitrato_ppm=nitrato,
        ))
        db.flush()

        for nome_especie, quantidade in peixes:
            especie = especies.get(nome_especie)
            if especie is None:
                print(f"  ! espécie '{nome_especie}' não existe — rode seed_especies.py")
                continue
            db.add(AquarioEspecie(
                aquario_id=aquario.id,
                especie_id=especie.id,
                quantidade=quantidade,
            ))

        db.flush()
        db.refresh(aquario)
        regerar_alertas(aquario, db)

        criados += 1
        print(f"    + aquário {nome} ({tipo}, {litros}L)")

    return criados


def garantir_manutencao(db, loja: Usuario) -> None:
    """Um cliente de manutenção com uma visita, para a aba não abrir vazia."""
    cliente = (
        db.query(ClienteManutencao)
        .filter(
            ClienteManutencao.dono_id == loja.id,
            func.lower(ClienteManutencao.nome) == "dona marta",
        )
        .first()
    )
    if cliente is not None:
        return

    cliente = ClienteManutencao(
        dono_id=loja.id,
        nome="Dona Marta",
        telefone="(41) 99876-5432",
        endereco="Rua das Acácias, 45 — Curitiba",
        tipo_instalacao="aquario",
        volume_litros=150,
        agua_doce=True,
        ativo=True,
    )
    db.add(cliente)
    db.flush()

    db.add(FichaManutencao(
        dono_id=loja.id,
        cliente_id=cliente.id,
        nome_cliente=cliente.nome,
        nome_empresa=LOJA["nome"],
        horario_chegada="14:00",
        horario_saida="15:30",
        tipo_instalacao=cliente.tipo_instalacao,
        volume_litros=cliente.volume_litros,
        agua_doce=cliente.agua_doce,
    ))
    print("    + cliente de manutenção Dona Marta, com 1 visita")


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Especie).count() == 0:
            print("Nenhuma espécie no banco. Rode antes:  python seed_especies.py")
            return

        loja = garantir_loja(db)
        cliente = garantir_cliente(db, loja)

        print("\nConteúdo da loja:")
        garantir_aquarios(db, loja, AQUARIOS_LOJA)
        garantir_manutencao(db, loja)

        print("\nConteúdo do cliente:")
        garantir_aquarios(db, cliente, AQUARIOS_CLIENTE)

        db.commit()

        print(
            "\n"
            "Pronto. Entre no app com:\n"
            f"  LOJA     {formatar_documento(LOJA['documento'])}   senha {LOJA['senha']}\n"
            f"  CLIENTE  {formatar_documento(CLIENTE['documento'])}      senha {CLIENTE['senha']}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
