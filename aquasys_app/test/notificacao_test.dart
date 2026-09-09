import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import 'package:aquasys_app/Services/notificacao_service.dart';

void main() {
  setUpAll(() {
    tzdata.initializeTimeZones();
    // Fuso fixo para o teste não depender de onde ele roda.
    tz.setLocalLocation(tz.getLocation('America/Sao_Paulo'));
  });

  tz.TZDateTime em(int dia, int hora, int minuto) =>
      tz.TZDateTime(tz.local, 2026, 9, dia, hora, minuto);

  group('Horário do lembrete diário', () {
    test('antes das 9h agenda para hoje', () {
      final quando = NotificacaoService.proximoLembrete(em(4, 7, 30));

      expect(quando.day, 4);
      expect(quando.hour, 9);
      expect(quando.minute, 0);
    });

    test('depois das 9h agenda para amanhã', () {
      final quando = NotificacaoService.proximoLembrete(em(4, 14, 0));

      expect(quando.day, 5);
      expect(quando.hour, 9);
    });

    test('exatamente 9h joga para amanhã, não dispara no mesmo instante', () {
      final quando = NotificacaoService.proximoLembrete(em(4, 9, 0));

      expect(quando.day, 5);
    });

    test('vira o mês corretamente', () {
      final ultimoDia = tz.TZDateTime(tz.local, 2026, 9, 30, 22, 0);
      final quando = NotificacaoService.proximoLembrete(ultimoDia);

      expect(quando.month, 10);
      expect(quando.day, 1);
    });
  });

  group('Id da notificação', () {
    test('o mesmo alerta sempre cai na mesma notificação', () {
      const uuid = 'a04a0929-cf16-4073-a485-14dd7675a7c0';

      expect(
        NotificacaoService.idNumerico(uuid),
        NotificacaoService.idNumerico(uuid),
      );
    });

    test('alertas diferentes não colidem', () {
      expect(
        NotificacaoService.idNumerico('a04a0929-cf16-4073-a485-14dd7675a7c0'),
        isNot(NotificacaoService.idNumerico(
            'b15b1a3a-df27-5184-b596-25ee8786b8d1')),
      );
    });

    test('cabe no int de 32 bits que o plugin aceita', () {
      for (final chave in [
        'a04a0929-cf16-4073-a485-14dd7675a7c0',
        'pH do aquário "Comunitário" está 0.3 acima do ideal',
        '',
      ]) {
        final id = NotificacaoService.idNumerico(chave);
        expect(id, greaterThanOrEqualTo(0));
        expect(id, lessThanOrEqualTo(0x7FFFFFFF));
      }
    });
  });
}
