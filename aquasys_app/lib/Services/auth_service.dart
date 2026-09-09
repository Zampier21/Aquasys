import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config.dart';
import '../utils/documento.dart';

class AuthService {
  static String get baseUrl => Config.apiUrl;
  static const String _tokenKey = 'access_token';
  static const String _tipoKey = 'tipo_usuario';
  static const String _nomeKey = 'nome_usuario';
  static const String _avatarKey = 'avatar_usuario';

  // ─── Login ────────────────────────────────────────
  static Future<Map<String, dynamic>> login({
    required String cpfCnpj,
    required String senha,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          // A API compara só os dígitos, então a máscara não importa.
          'cpf_cnpj': somenteDigitos(cpfCnpj),
          'senha': senha,
        }),
      );

      final data = jsonDecode(utf8.decode(response.bodyBytes));

      if (response.statusCode == 200) {
        // Salva o token e os dados do usuário localmente
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_tokenKey, data['access_token']);
        await prefs.setString(_tipoKey, data['tipo_usuario']);
        await prefs.setString(_nomeKey, data['nome'] ?? '');
        // A foto vem no login para o cabeçalho já abrir com a logo certa.
        final avatar = data['avatar'];
        if (avatar is String && avatar.isNotEmpty) {
          await prefs.setString(_avatarKey, avatar);
        } else {
          await prefs.remove(_avatarKey);
        }

        return {
          'sucesso': true,
          'tipo': data['tipo_usuario'],
          'nome': data['nome'],
        };
      }

      // Retorna a mensagem de erro da API
      final mensagem = data['detail'] ?? 'Erro ao fazer login';
      return {'sucesso': false, 'erro': mensagem};
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
    await prefs.remove(_nomeKey);
    await prefs.remove(_avatarKey);
  }

  // ─── Verifica se está logado ──────────────────────
  static Future<bool> estaLogado() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token == null || token.isEmpty) return false;

    // Token vencido é o mesmo que não ter token: melhor mandar para o
    // login agora do que deixar a Home abrir e quebrar com 401.
    if (tokenExpirado(token)) {
      await logout();
      return false;
    }
    return true;
  }

  /// Lê o `exp` do JWT sem precisar de pacote: o payload é a parte do
  /// meio, em base64url.
  static bool tokenExpirado(String token) {
    try {
      final partes = token.split('.');
      if (partes.length != 3) return true;

      final payload = jsonDecode(
        utf8.decode(base64Url.decode(base64Url.normalize(partes[1]))),
      ) as Map<String, dynamic>;

      final exp = payload['exp'];
      if (exp is! int) return true;

      final vence = DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
      // Um minuto de folga evita expirar no meio de uma requisição.
      return DateTime.now().toUtc().isAfter(
            vence.subtract(const Duration(minutes: 1)),
          );
    } catch (_) {
      return true;
    }
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

  // ─── Recupera o nome do usuário ───────────────────
  static Future<String?> getNomeUsuario() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_nomeKey);
  }

  // ─── Foto de perfil / logo, em base64 ─────────────
  static Future<String?> getAvatar() async {
    final prefs = await SharedPreferences.getInstance();
    final avatar = prefs.getString(_avatarKey);
    return (avatar == null || avatar.isEmpty) ? null : avatar;
  }

  /// Atualiza a cópia local depois que a API confirmou a troca.
  ///
  /// `null` apaga: é o caminho de "remover foto" e o de quem nunca pôs
  /// nenhuma — nos dois casos o cabeçalho volta ao ícone padrão.
  static Future<void> salvarAvatar(String? base64) async {
    final prefs = await SharedPreferences.getInstance();
    if (base64 == null || base64.isEmpty) {
      await prefs.remove(_avatarKey);
    } else {
      await prefs.setString(_avatarKey, base64);
    }
  }

  static Future<void> salvarNome(String? nome) async {
    if (nome == null || nome.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_nomeKey, nome);
  }

  // ─── Header padrão autenticado ────────────────────
  static Future<Map<String, String>> headers() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }
}
