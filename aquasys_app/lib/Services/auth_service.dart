import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  // URL base da API — localhost para desenvolvimento
  static const String _baseUrl = 'http://127.0.0.1:8000';
  static const String _tokenKey = 'access_token';
  static const String _tipoKey = 'tipo_usuario';

  // ─── Login ────────────────────────────────────────
  static Future<Map<String, dynamic>> login({
    required String cpfCnpj,
    required String senha,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'cpf_cnpj': cpfCnpj,
          'senha': senha,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        // Salva o token e tipo do usuário localmente
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_tokenKey, data['access_token']);
        await prefs.setString(_tipoKey, data['tipo_usuario']);

        return {'sucesso': true, 'tipo': data['tipo_usuario']};
      } else {
        // Retorna a mensagem de erro da API
        final mensagem = data['detail'] ?? 'Erro ao fazer login';
        return {'sucesso': false, 'erro': mensagem};
      }
    } catch (e) {
      return {
        'sucesso': false,
        'erro': 'Não foi possível conectar ao servidor. Verifique sua conexão.',
      };
    }
  }

  // ─── Logout ───────────────────────────────────────
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_tipoKey);
  }

  // ─── Verifica se está logado ──────────────────────
  static Future<bool> estaLogado() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    return token != null && token.isNotEmpty;
  }

  // ─── Recupera o token salvo ───────────────────────
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  // ─── Recupera o tipo do usuário ───────────────────
  static Future<String?> getTipoUsuario() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tipoKey);
  }
}