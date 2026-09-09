import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Lembretes diários dos alertas de aquário, no próprio aparelho.
///
/// A camada é **agnóstica de origem**: ela recebe uma lista de alertas
/// já prontos e agenda. Não sabe (nem precisa saber) se vieram da API ou
/// de um banco local — é isso que faz o dia do modo offline não mexer
/// aqui dentro.
///
/// O agendamento é diário e se repete enquanto o alerta existir. Some
/// quando o parâmetro é corrigido ou o aviso é dispensado, porque a
/// sincronização apaga o que não veio na lista nova.
class NotificacaoService {
  static final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  static const String _canalId = 'alertas_aquario';
  static const String _canalNome = 'Alertas dos aquários';
  static const String _canalDescricao =
      'Lembretes diários sobre parâmetros fora da faixa ideal';

  /// Horário do lembrete. 9h da manhã: cedo o bastante para dar tempo de
  /// agir no aquário, tarde o bastante para não acordar ninguém.
  static const int _horaLembrete = 9;
  static const int _minutoLembrete = 0;

  static bool _iniciado = false;

  /// Chamado quando o usuário toca na notificação.
  static void Function(String aquarioId)? aoTocar;

  // ═══════════════════════════════════════════════════
  // INICIALIZAÇÃO
  // ═══════════════════════════════════════════════════
  static Future<void> iniciar() async {
    if (_iniciado) return;

    // Notificação agendada precisa de fuso horário: sem isso, "9h" não
    // tem significado. O pacote timezone não lê o fuso do sistema
    // sozinho, então usamos o horário local do aparelho.
    tzdata.initializeTimeZones();

    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    // As permissões do iOS são pedidas em `pedirPermissao`, no momento
    // certo — não no primeiro segundo do app.
    const ios = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );

    await _plugin.initialize(
      settings: const InitializationSettings(android: android, iOS: ios),
      onDidReceiveNotificationResponse: (resposta) {
        final payload = resposta.payload;
        if (payload != null && payload.isNotEmpty) aoTocar?.call(payload);
      },
    );

    _iniciado = true;
  }

  // ═══════════════════════════════════════════════════
  // PERMISSÃO
  // ═══════════════════════════════════════════════════
  /// Pede autorização para notificar.
  ///
  /// No Android 13+ isso abre o diálogo de POST_NOTIFICATIONS; em versões
  /// anteriores a permissão já vem concedida. No iOS abre o diálogo do
  /// sistema. Chame quando existir algo a notificar, não na abertura.
  static Future<bool> pedirPermissao() async {
    await iniciar();

    if (defaultTargetPlatform == TargetPlatform.android) {
      final android = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      return await android?.requestNotificationsPermission() ?? false;
    }

    if (defaultTargetPlatform == TargetPlatform.iOS) {
      final ios = _plugin.resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin>();
      return await ios?.requestPermissions(alert: true, badge: true, sound: true) ??
          false;
    }

    return false;
  }

  // ═══════════════════════════════════════════════════
  // SINCRONIZAÇÃO
  // ═══════════════════════════════════════════════════
  /// Reflete no aparelho exatamente a lista de alertas recebida.
  ///
  /// Cada item precisa de `id`, `aquario` e `mensagem`; `aquario_id` é
  /// opcional e serve para o toque abrir o aquário certo.
  ///
  /// Cancela tudo antes de reagendar: assim alerta resolvido some sem
  /// precisar rastrear o que mudou. São poucas notificações, o custo é
  /// irrelevante perto da simplicidade.
  static Future<void> sincronizar(List<dynamic> alertas) async {
    await iniciar();
    await _plugin.cancelAll();

    if (alertas.isEmpty) return;

    for (final alerta in alertas) {
      final mensagem = alerta['mensagem']?.toString();
      if (mensagem == null || mensagem.isEmpty) continue;

      await _plugin.zonedSchedule(
        id: idNumerico(alerta['id']?.toString() ?? mensagem),
        title: alerta['aquario']?.toString().isNotEmpty == true
            ? 'Atenção: ${alerta['aquario']}'
            : 'Atenção no seu aquário',
        body: mensagem,
        scheduledDate: proximoLembrete(tz.TZDateTime.now(tz.local)),
        payload: alerta['aquario_id']?.toString() ?? '',
        notificationDetails: const NotificationDetails(
          android: AndroidNotificationDetails(
            _canalId,
            _canalNome,
            channelDescription: _canalDescricao,
            importance: Importance.defaultImportance,
            priority: Priority.defaultPriority,
            styleInformation: BigTextStyleInformation(''),
          ),
          iOS: DarwinNotificationDetails(),
        ),
        // Repete todo dia no mesmo horário enquanto não for cancelada.
        matchDateTimeComponents: DateTimeComponents.time,
        // Inexato de propósito: lembrete de aquário não precisa de
        // precisão de segundo, e o modo exato exige a permissão
        // SCHEDULE_EXACT_ALARM, que o Google restringe a alarmes e
        // agenda — pedi-la aqui seria motivo de recusa na Play Store.
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    }
  }

  /// Remove todos os lembretes — usado no logout.
  static Future<void> limpar() async {
    await iniciar();
    await _plugin.cancelAll();
  }

  /// Quantos lembretes estão agendados. Serve para conferir em teste.
  static Future<int> agendados() async {
    await iniciar();
    final pendentes = await _plugin.pendingNotificationRequests();
    return pendentes.length;
  }

  // ═══════════════════════════════════════════════════
  // AUXILIARES
  // ═══════════════════════════════════════════════════
  /// Próxima ocorrência do horário do lembrete. Se já passou das 9h
  /// hoje, agenda para amanhã — senão o primeiro disparo só viria no
  /// dia seguinte por acaso.
  ///
  /// Recebe o "agora" em vez de consultar o relógio para poder ser
  /// testada sem depender da hora em que o teste roda.
  @visibleForTesting
  static tz.TZDateTime proximoLembrete(tz.TZDateTime agora) {
    var quando = tz.TZDateTime(
      tz.local,
      agora.year,
      agora.month,
      agora.day,
      _horaLembrete,
      _minutoLembrete,
    );

    if (!quando.isAfter(agora)) {
      quando = quando.add(const Duration(days: 1));
    }
    return quando;
  }

  /// O plugin identifica notificação por int de 32 bits, mas o alerta
  /// tem id UUID. O hash do UUID dá um número estável — o mesmo alerta
  /// sempre cai na mesma notificação.
  @visibleForTesting
  static int idNumerico(String chave) => chave.hashCode & 0x7FFFFFFF;
}
