import 'api.dart';
import 'auth_service.dart';

/// Perfil da conta logada — o que a tela de Configurações edita.
///
/// Toda alteração que muda o que o cabeçalho mostra (nome e foto) também
/// atualiza a cópia local, senão a tela salvava com sucesso e o topo
/// continuava exibindo o valor antigo até o próximo login.
class PerfilService {
  static Future<Map<String, dynamic>> carregar() => Api.get('/perfil/');

  static Future<Map<String, dynamic>> editar({
    String? nome,
    String? email,
  }) async {
    final resposta = await Api.patch('/perfil/', corpo: {
      'nome': ?nome,
      'email': ?email,
    });
    await _sincronizarCache(resposta);
    return resposta;
  }

  /// Troca a senha. A atual é exigida pela API, não é formalidade.
  static Future<Map<String, dynamic>> trocarSenha({
    required String senhaAtual,
    required String senhaNova,
  }) =>
      Api.put('/perfil/senha', corpo: {
        'senha_atual': senhaAtual,
        'senha_nova': senhaNova,
      });

  /// Envia a foto/logo já em base64 — quem reduz a imagem é o app.
  static Future<Map<String, dynamic>> trocarAvatar(String base64) async {
    final resposta = await Api.put('/perfil/avatar', corpo: {'imagem': base64});
    await _sincronizarCache(resposta);
    return resposta;
  }

  static Future<Map<String, dynamic>> removerAvatar() async {
    final resposta = await Api.delete('/perfil/avatar');
    if (resposta['sucesso'] == true) await AuthService.salvarAvatar(null);
    return resposta;
  }

  static Future<void> _sincronizarCache(Map<String, dynamic> resposta) async {
    if (resposta['sucesso'] != true) return;
    final dados = resposta['dados'];
    if (dados is! Map) return;

    await AuthService.salvarNome(dados['nome']?.toString());
    await AuthService.salvarAvatar(dados['avatar']?.toString());
  }
}
