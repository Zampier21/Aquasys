import 'api.dart';

/// Fichas técnicas de manutenção.
class FichaService {
  /// Listas padrão de maquinários e testes usadas na ficha.
  static Future<Map<String, dynamic>> catalogos() async {
    final r = await Api.get('/fichas/catalogos');
    if (r['sucesso'] != true) return r;

    final d = r['dados'] as Map<String, dynamic>;
    return {
      'sucesso': true,
      'maquinarios': List<String>.from(d['maquinarios']),
      'testes': List<Map<String, dynamic>>.from(d['testes']),
    };
  }

  static Future<Map<String, dynamic>> listar({String? cliente}) =>
      Api.get('/fichas/', query: {'cliente': cliente});

  static Future<Map<String, dynamic>> detalhar(String id) =>
      Api.get('/fichas/$id');

  static Future<Map<String, dynamic>> criar(Map<String, dynamic> ficha) =>
      Api.post('/fichas/', corpo: ficha);

  static Future<Map<String, dynamic>> editar(
    String id,
    Map<String, dynamic> ficha,
  ) =>
      Api.put('/fichas/$id', corpo: ficha);

  static Future<Map<String, dynamic>> excluir(String id) =>
      Api.delete('/fichas/$id');

  // ═══════════════════════════════════════════════════
  // CLIENTES DE MANUTENÇÃO
  //
  // Quem a loja visita em casa. Cadastro leve, sem login: existe para
  // o técnico não redigitar contato e dados do aquário a cada visita.
  // ═══════════════════════════════════════════════════
  static Future<Map<String, dynamic>> listarClientes({String? busca}) =>
      Api.get('/fichas/clientes', query: {'busca': busca});

  static Future<Map<String, dynamic>> criarCliente({
    required String nome,
    String? telefone,
    String? endereco,
    String? tipoInstalacao,
    int? volumeLitros,
    bool? aguaDoce,
  }) =>
      Api.post('/fichas/clientes', corpo: {
        'nome': nome,
        'telefone': ?telefone,
        'endereco': ?endereco,
        'tipo_instalacao': ?tipoInstalacao,
        'volume_litros': ?volumeLitros,
        'agua_doce': ?aguaDoce,
      });

  static Future<Map<String, dynamic>> editarCliente(
    String id,
    Map<String, dynamic> dados,
  ) =>
      Api.put('/fichas/clientes/$id', corpo: dados);

  /// Tira da lista sem apagar as fichas já registradas.
  static Future<Map<String, dynamic>> removerCliente(String id) =>
      Api.delete('/fichas/clientes/$id');
}
