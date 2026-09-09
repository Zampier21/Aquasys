from app.core.console import preparar

preparar()

import sys

from app.core.documento import (
    documento_valido,
    formatar_documento,
    somente_digitos,
    tipo_documento,
)
from app.core.security import hash_senha
from app.database import SessionLocal
from app.models.usuario import Usuario
from sqlalchemy import func

USO = (
    'Uso: python criar_dono.py "<nome>" <cnpj-ou-cpf> <senha>\n\n'
    'Exemplo:\n'
    '  python criar_dono.py "Minha Loja" 12.345.678/0001-90 minhasenha\n'
)


def main(argumentos: list) -> int:
    if len(argumentos) != 3:
        print(USO)
        return 1

    nome, documento, senha = argumentos
    nome = nome.strip()
    digitos = somente_digitos(documento)

    # ─── Validação, antes de tocar no banco ────────────
    if len(nome) < 2:
        print("Erro: informe o nome da empresa.")
        return 1

    if len(senha) < 6:
        print("Erro: a senha precisa de pelo menos 6 caracteres.")
        return 1

    tipo = tipo_documento(digitos)
    if tipo == "cpf":
        print(
            "Erro: conta de assinante exige CNPJ, e você informou um CPF.\n"
            "\n"
            "       Pessoa física não assina o AquaSys: ela entra como\n"
            "       cliente de uma loja, e é a loja que cria esse acesso\n"
            "       pelo app, em Clientes → Acessos para clientes."
        )
        return 1

    if tipo is None:
        print(
            f'Erro: "{documento}" não é um CNPJ.\n'
            f"       Informe 14 dígitos — recebi {len(digitos)}."
        )
        return 1

    if not documento_valido(digitos):
        print("Erro: CNPJ inválido — confira os dígitos verificadores.")
        return 1

    db = SessionLocal()
    try:
        # Compara só os dígitos: o banco pode ter o documento com máscara.
        limpo = func.regexp_replace(Usuario.cpf_cnpj, r"\D", "", "g")
        existente = db.query(Usuario).filter(limpo == digitos).first()

        if existente is not None:
            print(
                f'Erro: já existe um usuário com esse documento '
                f'("{existente.nome}", tipo {existente.tipo}).'
            )
            return 1

        usuario = Usuario(
            nome=nome,
            cpf_cnpj=formatar_documento(digitos),
            senha_hash=hash_senha(senha),
            tipo="dono",       # conta empresarial
            dono_id=None,      # o CHECK do banco exige nulo para 'dono'
            ativo=True,
        )
        db.add(usuario)
        db.commit()

        print(
            f"Conta empresarial criada.\n"
            f"  nome  : {usuario.nome}\n"
            f"  acesso: {usuario.cpf_cnpj}\n\n"
            f"Entre no app com esse CNPJ e a senha que você definiu."
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
