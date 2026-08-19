import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class PeixeService {
  static const String _baseUrl = 'http://127.0.0.1:8000';

  static Future<Map<String, String>> _headers() async {
    final token = await AuthService.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ─── Catálogo de espécies ───────────────────────────
  static Future<Map<String, dynamic>> listarEspecies({String? busca}) async {
    try {
      final uri = Uri.parse('$_baseUrl/peixes/').replace(
        queryParameters: (busca != null && busca.trim().isNotEmpty)
            ? {'busca': busca.trim()}
            : null,
      );

      final resposta = await http.get(uri, headers: await _headers());

      if (resposta.statusCode == 200) {
        final lista = jsonDecode(utf8.decode(resposta.bodyBytes)) as List;
        return {
          'sucesso': true,
          'dados': lista.map((e) => e as Map<String, dynamic>).toList(),
        };
      }
      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Compatibilidade de todo o catálogo com um aquário ──
  static Future<Map<String, dynamic>> compatibilidades(String aquarioId) async {
    try {
      final resposta = await http.get(
        Uri.parse('$_baseUrl/peixes/compativeis/$aquarioId'),
        headers: await _headers(),
      );

      if (resposta.statusCode == 200) {
        final lista = jsonDecode(utf8.decode(resposta.bodyBytes)) as List;
        // Indexa por especie_id para consulta rápida na tela
        final mapa = <String, Map<String, dynamic>>{};
        for (final item in lista) {
          mapa[item['especie_id']] = item as Map<String, dynamic>;
        }
        return {'sucesso': true, 'dados': mapa};
      }
      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Análise de uma espécie na quantidade escolhida ──
  static Future<Map<String, dynamic>> analisar({
    required String especieId,
    required String aquarioId,
    required int quantidade,
  }) async {
    try {
      final resposta = await http.get(
        Uri.parse(
          '$_baseUrl/peixes/$especieId/aquario/$aquarioId?quantidade=$quantidade',
        ),
        headers: await _headers(),
      );

      if (resposta.statusCode == 200) {
        return {
          'sucesso': true,
          'dados': jsonDecode(utf8.decode(resposta.bodyBytes)),
        };
      }
      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Habitantes do aquário ──────────────────────────
  static Future<Map<String, dynamic>> habitantes(String aquarioId) async {
    try {
      final resposta = await http.get(
        Uri.parse('$_baseUrl/peixes/aquario/$aquarioId'),
        headers: await _headers(),
      );

      if (resposta.statusCode == 200) {
        final lista = jsonDecode(utf8.decode(resposta.bodyBytes)) as List;
        return {
          'sucesso': true,
          'dados': lista.map((e) => e as Map<String, dynamic>).toList(),
        };
      }
      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Adicionar espécie ao aquário ───────────────────
  static Future<Map<String, dynamic>> adicionar({
    required String aquarioId,
    required String especieId,
    required int quantidade,
    bool confirmar = false,
  }) async {
    try {
      final uri = Uri.parse(
        '$_baseUrl/peixes/aquario/$aquarioId?confirmar=$confirmar',
      );

      final resposta = await http.post(
        uri,
        headers: await _headers(),
        body: jsonEncode({
          'especie_id': especieId,
          'quantidade': quantidade,
        }),
      );

      if (resposta.statusCode == 201) {
        return {
          'sucesso': true,
          'dados': jsonDecode(utf8.decode(resposta.bodyBytes)),
        };
      }

      // 409 traz a decisão e os motivos em detail
      if (resposta.statusCode == 409) {
        final corpo = jsonDecode(utf8.decode(resposta.bodyBytes));
        final detalhe = corpo['detail'];

        if (detalhe is Map) {
          return {
            'sucesso': false,
            'decisao': detalhe['decisao'],
            'erro': detalhe['mensagem'],
            'motivos': List<String>.from(
              detalhe['motivos'] ?? detalhe['ressalvas'] ?? [],
            ),
          };
        }
        return {'sucesso': false, 'erro': detalhe.toString()};
      }

      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Atualizar quantidade ───────────────────────────
  static Future<Map<String, dynamic>> atualizarQuantidade({
    required String aquarioId,
    required String itemId,
    required int quantidade,
  }) async {
    try {
      final resposta = await http.put(
        Uri.parse('$_baseUrl/peixes/aquario/$aquarioId/$itemId'),
        headers: await _headers(),
        body: jsonEncode({'quantidade': quantidade}),
      );

      if (resposta.statusCode == 200) {
        return {
          'sucesso': true,
          'dados': jsonDecode(utf8.decode(resposta.bodyBytes)),
        };
      }
      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Remover do aquário ─────────────────────────────
  static Future<Map<String, dynamic>> remover({
    required String aquarioId,
    required String itemId,
  }) async {
    try {
      final resposta = await http.delete(
        Uri.parse('$_baseUrl/peixes/aquario/$aquarioId/$itemId'),
        headers: await _headers(),
      );

      if (resposta.statusCode == 204) return {'sucesso': true};
      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  static String _extrairErro(http.Response resposta) {
    try {
      final corpo = jsonDecode(utf8.decode(resposta.bodyBytes));
      final detalhe = corpo['detail'];

      if (detalhe is String) return detalhe;
      if (detalhe is Map) return detalhe['mensagem']?.toString() ?? 'Erro na requisição.';
      if (detalhe is List && detalhe.isNotEmpty) {
        return detalhe.first['msg']?.toString() ?? 'Dados inválidos.';
      }
    } catch (_) {}
    return 'Erro ${resposta.statusCode}. Tente novamente.';
  }
}