import re

_NAO_DIGITO = re.compile(r"\D")


def somente_digitos(valor: str) -> str:
    """Remove pontos, barras, hífens e espaços."""
    return _NAO_DIGITO.sub("", valor or "")


def tipo_documento(valor: str) -> str | None:
    """Devolve 'cpf', 'cnpj' ou None, decidindo pelo número de dígitos."""
    digitos = somente_digitos(valor)
    if len(digitos) == 11:
        return "cpf"
    if len(digitos) == 14:
        return "cnpj"
    return None


def validar_cpf(valor: str) -> bool:
    d = somente_digitos(valor)
    if len(d) != 11 or d == d[0] * 11:
        return False

    def digito(quantidade: int) -> int:
        soma = sum(int(d[i]) * (quantidade + 1 - i) for i in range(quantidade))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    return digito(9) == int(d[9]) and digito(10) == int(d[10])


def validar_cnpj(valor: str) -> bool:
    d = somente_digitos(valor)
    if len(d) != 14 or d == d[0] * 14:
        return False

    def digito(pesos: list[int]) -> int:
        soma = sum(int(d[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    return digito(pesos1) == int(d[12]) and digito(pesos2) == int(d[13])


def documento_valido(valor: str) -> bool:
    """Valida CPF ou CNPJ, escolhendo a regra pelo tamanho."""
    tipo = tipo_documento(valor)
    if tipo == "cpf":
        return validar_cpf(valor)
    if tipo == "cnpj":
        return validar_cnpj(valor)
    return False


def formatar_documento(valor: str) -> str:
    """Aplica a máscara de CPF ou CNPJ. Sem tamanho válido, devolve os dígitos."""
    d = somente_digitos(valor)
    if len(d) == 11:
        return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    if len(d) == 14:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    return d
