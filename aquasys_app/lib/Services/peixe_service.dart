import 'api.dart';

/// Catálogo de espécies e povoamento dos aquários.
class PeixeService {
  /// Catálogo, opcionalmente filtrado por nome.
  static Future<Map<String, dynamic>> listarEspecies({String? busca}) =>
      Api.get('/peixes/', query: {
        if (busca != null && busca.trim().isNotEmpty) 'busca': busca.trim(),
      });

  /// Compatibilidade de todo o catálogo com um aquário.
  ///
  /// A API devolve uma lista; a tela consulta por espécie a cada card,
  /// então o resultado sai daqui já indexado por `especie_id`.
  static Future<Map<String, dynamic>> compatibilidades(String aquarioId) async {
    final resposta = await Api.get('/peixes/compativeis/$aquarioId');
    if (resposta['sucesso'] != true) return resposta;

    final mapa = <String, Map<String, dynamic>>{};
    for (final item in Api.lista(resposta)) {
      mapa['${item['especie_id']}'] = item;
    }
    return {'sucesso': true, 'dados': mapa};
  }

  /// Análise de uma espécie específica, na quantidade pretendida.
  static Future<Map<String, dynamic>> analisar({
    required String especieId,
    required String aquarioId,
    required int quantidade,
  }) =>
      Api.get('/peixes/$especieId/aquario/$aquarioId',
          query: {'quantidade': quantidade});

  static Future<Map<String, dynamic>> habitantes(String aquarioId) =>
      Api.get('/peixes/aquario/$aquarioId');

  /// Adiciona a espécie ao aquário.
  ///
  /// Combinação arriscada volta 409 com o motivo; repetir com
  /// `confirmar: true` grava mesmo assim.
  static Future<Map<String, dynamic>> adicionar({
    required String aquarioId,
    required String especieId,
    required int quantidade,
    bool confirmar = false,
  }) =>
      Api.post(
        '/peixes/aquario/$aquarioId',
        query: {'confirmar': confirmar},
        corpo: {'especie_id': especieId, 'quantidade': quantidade},
      );

  static Future<Map<String, dynamic>> atualizarQuantidade({
    required String aquarioId,
    required String itemId,
    required int quantidade,
  }) =>
      Api.put('/peixes/aquario/$aquarioId/$itemId',
          corpo: {'quantidade': quantidade});

  static Future<Map<String, dynamic>> remover({
    required String aquarioId,
    required String itemId,
  }) =>
      Api.delete('/peixes/aquario/$aquarioId/$itemId');
}
