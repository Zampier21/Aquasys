import 'api.dart';

/// Dados da tela inicial — números, alertas e dicas numa requisição.
class PainelService {
  static Future<Map<String, dynamic>> carregar() => Api.get('/painel/');

  /// Dispensa um alerta. Ele volta na próxima medição que continuar
  /// fora da faixa.
  static Future<bool> marcarLido(String alertaId) async {
    final r = await Api.patch('/painel/alertas/$alertaId/lido');
    return r['sucesso'] == true;
  }
}
