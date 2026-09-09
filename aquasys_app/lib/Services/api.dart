import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';
import 'auth_service.dart';

class Api {
  static const String baseUrl = Config.apiUrl;

  // ─── Verbos ─────────────────────────────────────────
  static Future<Map<String, dynamic>> get(
    String rota, {
    Map<String, dynamic>? query,
  }) =>
      _enviar('GET', rota, query: query);

  static Future<Map<String, dynamic>> post(
    String rota, {
    Object? corpo,
    Map<String, dynamic>? query,
  }) =>
      _enviar('POST', rota, corpo: corpo, query: query, esperado: 201);

  static Future<Map<String, dynamic>> put(String rota, {Object? corpo}) =>
      _enviar('PUT', rota, corpo: corpo);

  static Future<Map<String, dynamic>> patch(
    String rota, {
    Object? corpo,
    Map<String, dynamic>? query,
  }) =>
      _enviar('PATCH', rota, corpo: corpo, query: query);

  static Future<Map<String, dynamic>> delete(String rota) =>
      _enviar('DELETE', rota, esperado: 204);

  // ─── Motor ──────────────────────────────────────────
  static Future<Map<String, dynamic>> _enviar(
    String metodo,
    String rota, {
    Object? corpo,
    Map<String, dynamic>? query,
    int esperado = 200,
  }) async {
    try {
      var uri = Uri.parse('$baseUrl$rota');
      if (query != null && query.isNotEmpty) {
        uri = uri.replace(
          queryParameters: {
            for (final e in query.entries)
              if (e.value != null) e.key: '${e.value}',
          },
        );
      }

      final cabecalhos = await AuthService.headers();
      final json = corpo == null ? null : jsonEncode(corpo);

      final resposta = switch (metodo) {
        'POST' => await http.post(uri, headers: cabecalhos, body: json),
        'PUT' => await http.put(uri, headers: cabecalhos, body: json),
        'PATCH' => await http.patch(uri, headers: cabecalhos, body: json),
        'DELETE' => await http.delete(uri, headers: cabecalhos),
        _ => await http.get(uri, headers: cabecalhos),
      };

      // 200 e 201 são ambos sucesso: POST devolve 201, mas nem toda rota
      // segue isso à risca, e a tela não deveria se importar.
      final ok = resposta.statusCode == esperado ||
          (esperado == 200 && resposta.statusCode == 201) ||
          (esperado == 201 && resposta.statusCode == 200) ||
          resposta.statusCode == 204;

      if (!ok) {
        return {'sucesso': false, 'erro': _traduzirErro(resposta)};
      }

      if (resposta.bodyBytes.isEmpty) {
        return {'sucesso': true, 'dados': null};
      }
      return {
        'sucesso': true,
        'dados': jsonDecode(utf8.decode(resposta.bodyBytes)),
      };
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  /// Transforma o corpo de erro da API em frase que serve para a tela.
  static String _traduzirErro(http.Response resposta) {
    try {
      final corpo = jsonDecode(utf8.decode(resposta.bodyBytes));
      final detalhe = corpo['detail'];

      if (detalhe is String) return detalhe;

      // Erro de validação do Pydantic vem como lista de campos.
      if (detalhe is List && detalhe.isNotEmpty) {
        final msg = detalhe.first['msg']?.toString() ?? 'Dados inválidos.';
        // "Value error, CPF inválido" → "CPF inválido"
        return msg.replaceFirst(RegExp(r'^Value error,\s*'), '');
      }
    } catch (_) {}

    if (resposta.statusCode == 401) {
      return 'Sessão expirada. Faça login novamente.';
    }
    return 'Erro ${resposta.statusCode}. Tente novamente.';
  }

  /// Lista tipada a partir de uma resposta de sucesso.
  static List<Map<String, dynamic>> lista(Map<String, dynamic> resultado) {
    final dados = resultado['dados'];
    if (dados is! List) return const [];
    return dados.map((e) => e as Map<String, dynamic>).toList();
  }
}
