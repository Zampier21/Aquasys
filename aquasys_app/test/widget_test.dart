import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:aquasys_app/utils/documento.dart';

TextEditingValue _digitar(String texto) => TextEditingValue(
      text: texto,
      selection: TextSelection.collapsed(offset: texto.length),
    );

void main() {
  group('Detecção CPF x CNPJ', () {
    test('11 dígitos viram CPF, 14 viram CNPJ', () {
      expect(tipoDocumento('123.456.789-09'), TipoDocumento.cpf);
      expect(tipoDocumento('12345678909'), TipoDocumento.cpf);
      expect(tipoDocumento('11.222.333/0001-81'), TipoDocumento.cnpj);
      expect(tipoDocumento('11222333000181'), TipoDocumento.cnpj);
    });

    test('tamanhos intermediários não são documento válido', () {
      expect(tipoDocumento('123456'), TipoDocumento.invalido);
      expect(tipoDocumento('123456789012'), TipoDocumento.invalido);
    });

    test('pontuação não interfere na comparação', () {
      expect(somenteDigitos('000.000.000-00'), '00000000000');
      expect(somenteDigitos('11.222.333/0001-81'), '11222333000181');
    });
  });

  group('Máscara automática', () {
    test('troca de CPF para CNPJ ao passar de 11 dígitos', () {
      expect(formatarDocumento('12345678909'), '123.456.789-09');
      expect(formatarDocumento('112223330001'), '11.222.333/0001');
      expect(formatarDocumento('11222333000181'), '11.222.333/0001-81');
    });

    test('formatter trava em 14 dígitos', () {
      final formatter = CpfCnpjInputFormatter();

      final quatorze = formatter.formatEditUpdate(
        const TextEditingValue(),
        _digitar('11222333000181'),
      );
      expect(quatorze.text, '11.222.333/0001-81');

      // O 15º dígito é recusado: o valor anterior é mantido.
      final quinze = formatter.formatEditUpdate(
        quatorze,
        _digitar('112223330001812'),
      );
      expect(quinze.text, '11.222.333/0001-81');
    });
  });

  group('Dígitos verificadores', () {
    test('CPF válido e inválido', () {
      expect(cpfValido('123.456.789-09'), isTrue);
      expect(cpfValido('123.456.789-00'), isFalse);
      expect(cpfValido('111.111.111-11'), isFalse);
    });

    test('CNPJ válido e inválido', () {
      expect(cnpjValido('11.222.333/0001-81'), isTrue);
      expect(cnpjValido('11.222.333/0001-00'), isFalse);
    });
  });

  group('Validação do formulário', () {
    test('mensagem específica para documento incompleto', () {
      expect(validarDocumento('123'), 'CPF incompleto — informe 11 dígitos');
      expect(
        validarDocumento('112223330001'),
        'CNPJ incompleto — informe 14 dígitos',
      );
    });

    test('no login, o dígito verificador não é exigido', () {
      // O acesso de teste 000.000.000-00 precisa continuar entrando.
      expect(
        validarDocumento('000.000.000-00', exigirDigitoVerificador: false),
        isNull,
      );
      expect(validarDocumento('000.000.000-00'), 'CPF inválido');
    });
  });
}
