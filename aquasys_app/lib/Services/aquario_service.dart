import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class AquarioService {
  static const String _baseUrl = 'http://127.0.0.1:8000';

  // Monta o header com o token JWT salvo no login
  static Future<Map<String, String>> _headers() async {
    final token = await AuthService.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ─── Listar aquários do usuário logado ──────────────
  static Future<Map<String, dynamic>> listar() async {
    try {
      final resposta = await http.get(
        Uri.parse('$_baseUrl/aquarios/'),
        headers: await _headers(),
      );

      if (resposta.statusCode == 200) {
        final lista = jsonDecode(utf8.decode(resposta.bodyBytes)) as List;
        return {
          'sucesso': true,
          'dados': lista.map((e) => e as Map<String, dynamic>).toList(),
        };
      }

      if (resposta.statusCode == 401) {
        return {'sucesso': false, 'erro': 'Sessão expirada. Faça login novamente.'};
      }

      return {'sucesso': false, 'erro': 'Não foi possível carregar os aquários.'};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Criar aquário ──────────────────────────────────
  static Future<Map<String, dynamic>> criar({
    required String nome,
    required double volumeLitros,
    required double temperatura,
    required double ph,
    String? tipo,
    double amonia = 0,
    double nitrito = 0,
    double nitrato = 0,
  }) async {
    try {
      final resposta = await http.post(
        Uri.parse('$_baseUrl/aquarios/'),
        headers: await _headers(),
        body: jsonEncode({
          'nome': nome,
          'volume_litros': volumeLitros,
          'temperatura': temperatura,
          'ph': ph,
          if (tipo != null) 'tipo': tipo,
          'amonia_ppm': amonia,
          'nitrito_ppm': nitrito,
          'nitrato_ppm': nitrato,
        }),
      );

      if (resposta.statusCode == 201) {
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

  // ─── Editar aquário ─────────────────────────────────
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
  }) async {
    try {
      // Envia só os campos preenchidos — o back-end usa exclude_unset
      final corpo = <String, dynamic>{
        if (nome != null) 'nome': nome,
        if (volumeLitros != null) 'volume_litros': volumeLitros,
        if (temperatura != null) 'temperatura': temperatura,
        if (ph != null) 'ph': ph,
        if (tipo != null) 'tipo': tipo,
        if (amonia != null) 'amonia_ppm': amonia,
        if (nitrito != null) 'nitrito_ppm': nitrito,
        if (nitrato != null) 'nitrato_ppm': nitrato,
      };

      final resposta = await http.put(
        Uri.parse('$_baseUrl/aquarios/$id'),
        headers: await _headers(),
        body: jsonEncode(corpo),
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

  // ─── Excluir aquário ────────────────────────────────
  static Future<Map<String, dynamic>> excluir(String id) async {
    try {
      final resposta = await http.delete(
        Uri.parse('$_baseUrl/aquarios/$id'),
        headers: await _headers(),
      );

      if (resposta.statusCode == 204) {
        return {'sucesso': true};
      }

      return {'sucesso': false, 'erro': _extrairErro(resposta)};
    } catch (_) {
      return {'sucesso': false, 'erro': 'Sem conexão com o servidor.'};
    }
  }

  // ─── Histórico de medições ──────────────────────────
  static Future<Map<String, dynamic>> historicoParametros(String id) async {
    try {
      final resposta = await http.get(
        Uri.parse('$_baseUrl/aquarios/$id/parametros'),
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

  // Traduz o corpo de erro da API para uma mensagem legível
  static String _extrairErro(http.Response resposta) {
    try {
      final corpo = jsonDecode(utf8.decode(resposta.bodyBytes));
      final detalhe = corpo['detail'];

      if (detalhe is String) return detalhe;

      // Erros de validação do Pydantic vêm como lista
      if (detalhe is List && detalhe.isNotEmpty) {
        return detalhe.first['msg']?.toString() ?? 'Dados inválidos.';
      }
    } catch (_) {}

    return 'Erro ${resposta.statusCode}. Tente novamente.';
  }
}