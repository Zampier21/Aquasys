import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:aquasys_app/Services/auth_service.dart';

/// Monta um JWT de mentira com o `exp` pedido.
///
/// Só a parte do meio importa: é dela que o app lê a expiração, sem
/// precisar de pacote nem conversar com o servidor.
String tokenCom({DateTime? expira, bool comExp = true}) {
  final cabecalho = base64Url
      .encode(utf8.encode(jsonEncode({'alg': 'HS256', 'typ': 'JWT'})))
      .replaceAll('=', '');

  final corpo = <String, dynamic>{'sub': 'abc', 'tipo': 'dono'};
  if (comExp) {
    corpo['exp'] = (expira!.millisecondsSinceEpoch / 1000).round();
  }

  final meio =
      base64Url.encode(utf8.encode(jsonEncode(corpo))).replaceAll('=', '');
  return '$cabecalho.$meio.assinatura-falsa';
}

void main() {
  group('Expiração do token', () {
    test('token que vence daqui a uma hora está válido', () {
      final token = tokenCom(
        expira: DateTime.now().toUtc().add(const Duration(hours: 1)),
      );
      expect(AuthService.tokenExpirado(token), isFalse);
    });

    test('token vencido é reconhecido como expirado', () {
      final token = tokenCom(
        expira: DateTime.now().toUtc().subtract(const Duration(minutes: 5)),
      );
      expect(AuthService.tokenExpirado(token), isTrue);
    });

    test('token a segundos do fim já conta como expirado', () {
      // A folga de um minuto evita a sessão morrer no meio de uma
      // requisição que já saiu.
      final token = tokenCom(
        expira: DateTime.now().toUtc().add(const Duration(seconds: 30)),
      );
      expect(AuthService.tokenExpirado(token), isTrue);
    });

    test('token com folga maior que um minuto ainda vale', () {
      final token = tokenCom(
        expira: DateTime.now().toUtc().add(const Duration(minutes: 5)),
      );
      expect(AuthService.tokenExpirado(token), isFalse);
    });
  });

  group('Token malformado', () {
    test('texto que não é JWT é tratado como expirado', () {
      // Melhor mandar para o login do que abrir a Home e quebrar com 401.
      for (final lixo in ['', 'abc', 'a.b', 'a.b.c.d', 'não é token']) {
        expect(AuthService.tokenExpirado(lixo), isTrue, reason: lixo);
      }
    });

    test('token sem campo exp é tratado como expirado', () {
      expect(AuthService.tokenExpirado(tokenCom(comExp: false)), isTrue);
    });

    test('payload que não é JSON é tratado como expirado', () {
      final meio = base64Url.encode(utf8.encode('isso não é json'));
      expect(AuthService.tokenExpirado('cabecalho.$meio.assinatura'), isTrue);
    });
  });
}
