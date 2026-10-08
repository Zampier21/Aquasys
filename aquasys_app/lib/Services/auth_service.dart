import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config.dart';
import '../utils/documento.dart';

class AuthService {
  static String get baseUrl => Config.apiUrl;
  static const String _tokenKey = 'access_token';
  static const String _refreshKey = 'refresh_token';
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
        await prefs.setString(_refreshKey, data['refresh_token'] ?? '');
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
  /// Encerra a sessão aqui e, se der, no servidor também.
  ///
  /// Apagar só no aparelho deixaria o token de renovação valendo por
  /// trinta dias no banco. Quem sai do aplicativo num celular que vai
  /// emprestar espera que sair signifique sair.
  ///
  /// Falha de rede não impede a saída local: é melhor sair daqui e o
  /// servidor continuar com uma sessão pendurada do que recusar o
  /// logout porque a rede caiu.
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    final refresh = prefs.getString(_refreshKey);

    if (refresh != null && refresh.isNotEmpty) {
      try {
        await http
            .post(
              Uri.parse('$baseUrl/auth/sair'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({'refresh_token': refresh}),
            )
            .timeout(const Duration(seconds: 5));
      } catch (_) {
        // Sessão fica pendurada no servidor até vencer. Paciência.
      }
    }

    await prefs.remove(_tokenKey);
    await prefs.remove(_refreshKey);
    await prefs.remove(_tipoKey);
    await prefs.remove(_nomeKey);
    await prefs.remove(_avatarKey);
  }

  // ─── Renovação ────────────────────────────────────
  /// Uma renovação de cada vez, compartilhada por quem pedir.
  ///
  /// Isto não é otimização, é correção. O servidor rotaciona o token a
  /// cada uso e trata token repetido como sinal de cópia em
  /// circulação, derrubando todas as sessões da conta. Se a tela de
  /// início disparasse três requisições juntas e as três tomassem 401,
  /// as três tentariam renovar: a primeira passaria e as outras duas
  /// chegariam com o token já gasto — e o usuário seria deslogado pela
  /// própria proteção contra roubo. Guardar a renovação em curso e
  /// esperá-la resolve.
  static Future<bool>? _renovacaoEmCurso;

  static Future<bool> renovar() {
    return _renovacaoEmCurso ??= _renovar().whenComplete(() {
      _renovacaoEmCurso = null;
    });
  }

  static Future<bool> _renovar() async {
    final prefs = await SharedPreferences.getInstance();
    final refresh = prefs.getString(_refreshKey);
    if (refresh == null || refresh.isEmpty) return false;

    try {
      final resposta = await http.post(
        Uri.parse('$baseUrl/auth/renovar'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': refresh}),
      );

      if (resposta.statusCode != 200) {
        // 401 aqui é definitivo: o servidor recusou a sessão. Limpar
        // evita o aplicativo insistir a cada requisição.
        if (resposta.statusCode == 401) await logout();
        return false;
      }

      final data = jsonDecode(utf8.decode(resposta.bodyBytes));
      await prefs.setString(_tokenKey, data['access_token']);
      await prefs.setString(_refreshKey, data['refresh_token'] ?? '');
      await prefs.setString(_tipoKey, data['tipo_usuario']);
      await prefs.setString(_nomeKey, data['nome'] ?? '');
      final avatar = data['avatar'];
      if (avatar is String && avatar.isNotEmpty) {
        await prefs.setString(_avatarKey, avatar);
      } else {
        await prefs.remove(_avatarKey);
      }
      return true;
    } catch (_) {
      // Sem rede. A sessão pode estar boa; não apaga nada.
      return false;
    }
  }

  // ─── Verifica se está logado ──────────────────────
  static Future<bool> estaLogado() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token == null || token.isEmpty) return false;

    // Token vencido não significa mais sessão perdida: se o token de
    // renovação ainda valer, a troca acontece aqui e o usuário sequer
    // vê a tela de login. Só quando a renovação falha é que se volta
    // ao login.
    if (tokenExpirado(token)) {
      return renovar();
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
