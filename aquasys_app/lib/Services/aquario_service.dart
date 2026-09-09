import 'api.dart';

/// Aquários do usuário logado.
class AquarioService {
  static Future<Map<String, dynamic>> listar() => Api.get('/aquarios/');

  static Future<Map<String, dynamic>> criar({
    required String nome,
    required double volumeLitros,
    required double temperatura,
    required double ph,
    String? tipo,
    double amonia = 0,
    double nitrito = 0,
    double nitrato = 0,
  }) =>
      Api.post('/aquarios/', corpo: {
        'nome': nome,
        'volume_litros': volumeLitros,
        'temperatura': temperatura,
        'ph': ph,
        'tipo': ?tipo,
        'amonia_ppm': amonia,
        'nitrito_ppm': nitrito,
        'nitrato_ppm': nitrato,
      });

  /// Envia só o que foi preenchido — a API usa `exclude_unset`.
  static Future<Map<String, dynamic>> editar({
    required String id,
    String? nome,
    double? volumeLitros,
    double? temperatura,
    double? ph,
    String? tipo,
    double? amonia,
    double? nitrito,
    double? nitrato,
  }) =>
      Api.put('/aquarios/$id', corpo: {
        'nome': ?nome,
        'volume_litros': ?volumeLitros,
        'temperatura': ?temperatura,
        'ph': ?ph,
        'tipo': ?tipo,
        'amonia_ppm': ?amonia,
        'nitrito_ppm': ?nitrito,
        'nitrato_ppm': ?nitrato,
      });

  /// Exclui o aquário. Parâmetros e alertas caem junto (CASCADE).
  static Future<Map<String, dynamic>> excluir(String id) =>
      Api.delete('/aquarios/$id');

  /// Histórico de medições, da mais recente para a mais antiga.
  static Future<Map<String, dynamic>> historicoParametros(String id) =>
      Api.get('/aquarios/$id/parametros');
}
