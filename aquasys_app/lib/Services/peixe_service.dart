import 'api.dart';

/// Catálogo de espécies e povoamento dos aquários.
class PeixeService {
  /// Catálogo, opcionalmente filtrado por nome.
  static Future<Map<String, dynamic>> listarEspecies({String? busca}) =>
      Api.get('/peixes/', query: {
        if (busca != null && busca.trim().isNotEmpty) 'busca': busca.trim(),
      });

  /// Confere uma lista de peixes em CSV contra o catálogo.
  ///
  /// Com `aplicar` falso devolve só o relatório. Com verdadeiro, grava:
  /// o que casou entra no estoque da loja e o que faltava vira espécie
  /// dela, marcada como não revisada.
  static Future<Map<String, dynamic>> importarLista(
    List<int> bytes, {
    bool aplicar = false,
  }) =>
      Api.postArquivo('/peixes/importar', bytes,
          query: {'aplicar': aplicar});

  /// Procura foto para as espécies da loja que ainda não têm.
  ///
  /// Trabalha por rodadas, e não de uma vez: cada foto leva uns 3,5
  /// segundos entre procurar no Wikimedia Commons, baixar e gerar as
  /// duas versões. Uma lista de 58 peixes numa requisição só estouraria
  /// o tempo do servidor. A tela repete enquanto `restantes` cair.
  static Future<Map<String, dynamic>> buscarFotos({int limite = 5}) =>
      Api.post('/peixes/fotos/buscar',
          query: {'limite': limite}, esperado: 200);

  /// Ficha completa de uma espécie.
  ///
  /// A lista de incompletas devolve só o que falta, e não os valores
  /// que já existem. O formulário de revisão precisa dos dois para não
  /// mostrar campo vazio onde já há dado gravado.
  static Future<Map<String, dynamic>> detalhar(String especieId) =>
      Api.get('/peixes/$especieId');

  /// Fichas da loja que a importação deixou pela metade.
  ///
  /// Cada item traz, em `faltam`, os rótulos do que ainda não foi
  /// preenchido. A lista vem do próprio motor de compatibilidade, que é
  /// quem sabe do que precisa para dar resposta inteira.
  static Future<Map<String, dynamic>> incompletas() =>
      Api.get('/peixes/incompletas');

  /// Grava a correção da ficha.
  ///
  /// Mandar `revisada: true` só é aceito quando nada essencial estiver
  /// faltando; do contrário a API responde 422 dizendo o que falta.
  static Future<Map<String, dynamic>> revisar(
    String especieId,
    Map<String, dynamic> dados,
  ) =>
      Api.put('/peixes/$especieId', corpo: dados);

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
