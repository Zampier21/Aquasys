import 'api.dart';
import '../utils/documento.dart';

/// Acessos de clientes — só a conta empresarial usa estas rotas.
class ClienteService {
  static Future<Map<String, dynamic>> listar({bool incluirInativos = false}) =>
      Api.get('/clientes/', query: {'incluir_inativos': incluirInativos});

  static Future<Map<String, dynamic>> criar({
    required String nome,
    required String cpf,
    required String senhaInicial,
    String? email,
  }) =>
      Api.post('/clientes/', corpo: {
        'nome': nome,
        // A API compara só os dígitos; a máscara é assunto da tela.
        'cpf_cnpj': somenteDigitos(cpf),
        'senha_inicial': senhaInicial,
        if (email != null && email.isNotEmpty) 'email': email,
      });

  static Future<Map<String, dynamic>> editar({
    required String id,
    String? nome,
    String? email,
    String? senha,
    bool? ativo,
  }) =>
      Api.put('/clientes/$id', corpo: {
        'nome': ?nome,
        'email': ?email,
        if (senha != null && senha.isNotEmpty) 'senha': senha,
        'ativo': ?ativo,
      });

  /// Desativa o acesso. Os aquários e o histórico do cliente ficam.
  static Future<Map<String, dynamic>> desativar(String id) =>
      Api.delete('/clientes/$id');
}
