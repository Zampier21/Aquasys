import 'package:flutter/services.dart';

enum TipoDocumento { cpf, cnpj, invalido }

/// Remove pontos, barras, hífens e espaços.
String somenteDigitos(String texto) => texto.replaceAll(RegExp(r'[^0-9]'), '');

/// Classifica pelo número de dígitos.
TipoDocumento tipoDocumento(String texto) {
  final d = somenteDigitos(texto);
  if (d.length == 11) return TipoDocumento.cpf;
  if (d.length == 14) return TipoDocumento.cnpj;
  return TipoDocumento.invalido;
}

/// Aplica a máscara correspondente ao tamanho atual.
String formatarDocumento(String texto) {
  final d = somenteDigitos(texto);

  if (d.length <= 11) {
    // 999.999.999-99
    final buffer = StringBuffer();
    for (var i = 0; i < d.length; i++) {
      if (i == 3 || i == 6) buffer.write('.');
      if (i == 9) buffer.write('-');
      buffer.write(d[i]);
    }
    return buffer.toString();
  }

  // 99.999.999/9999-99
  final limitado = d.length > 14 ? d.substring(0, 14) : d;
  final buffer = StringBuffer();
  for (var i = 0; i < limitado.length; i++) {
    if (i == 2 || i == 5) buffer.write('.');
    if (i == 8) buffer.write('/');
    if (i == 12) buffer.write('-');
    buffer.write(limitado[i]);
  }
  return buffer.toString();
}

/// Valida os dígitos verificadores do CPF.
bool cpfValido(String texto) {
  final d = somenteDigitos(texto);
  if (d.length != 11) return false;
  // Sequências repetidas (000.000.000-00, 111...) passam na conta mas não existem.
  if (RegExp(r'^(\d)\1{10}$').hasMatch(d)) return false;

  int calcularDigito(int quantidade) {
    var soma = 0;
    for (var i = 0; i < quantidade; i++) {
      soma += int.parse(d[i]) * (quantidade + 1 - i);
    }
    final resto = (soma * 10) % 11;
    return resto == 10 ? 0 : resto;
  }

  return calcularDigito(9) == int.parse(d[9]) &&
      calcularDigito(10) == int.parse(d[10]);
}

/// Valida os dígitos verificadores do CNPJ.
bool cnpjValido(String texto) {
  final d = somenteDigitos(texto);
  if (d.length != 14) return false;
  if (RegExp(r'^(\d)\1{13}$').hasMatch(d)) return false;

  int calcularDigito(List<int> pesos) {
    var soma = 0;
    for (var i = 0; i < pesos.length; i++) {
      soma += int.parse(d[i]) * pesos[i];
    }
    final resto = soma % 11;
    return resto < 2 ? 0 : 11 - resto;
  }

  const pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  return calcularDigito(pesos1) == int.parse(d[12]) &&
      calcularDigito(pesos2) == int.parse(d[13]);
}

/// Valida CPF **ou** CNPJ, decidindo pelo tamanho.
bool documentoValido(String texto) {
  switch (tipoDocumento(texto)) {
    case TipoDocumento.cpf:
      return cpfValido(texto);
    case TipoDocumento.cnpj:
      return cnpjValido(texto);
    case TipoDocumento.invalido:
      return false;
  }
}

/// Mensagem de erro pronta para o `validator` do formulário.
/// Retorna `null` quando está tudo certo.
String? validarDocumento(String? texto, {bool exigirDigitoVerificador = true}) {
  if (texto == null || texto.trim().isEmpty) {
    return 'Informe o CPF ou CNPJ';
  }

  final d = somenteDigitos(texto);
  if (d.length < 11) {
    return 'CPF incompleto — informe 11 dígitos';
  }
  if (d.length > 11 && d.length < 14) {
    return 'CNPJ incompleto — informe 14 dígitos';
  }
  if (d.length != 11 && d.length != 14) {
    return 'Documento inválido';
  }

  if (exigirDigitoVerificador && !documentoValido(texto)) {
    return tipoDocumento(texto) == TipoDocumento.cpf
        ? 'CPF inválido'
        : 'CNPJ inválido';
  }

  return null;
}

/// `TextInputFormatter` que aplica a máscara certa a cada tecla
/// e trava a entrada em 14 dígitos.
class CpfCnpjInputFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue anterior,
    TextEditingValue novo,
  ) {
    final digitos = somenteDigitos(novo.text);
    if (digitos.length > 14) return anterior;

    final formatado = formatarDocumento(digitos);
    return TextEditingValue(
      text: formatado,
      // Mantém o cursor sempre no fim do texto formatado.
      selection: TextSelection.collapsed(offset: formatado.length),
    );
  }
}
