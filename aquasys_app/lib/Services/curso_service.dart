import 'api.dart';

/// Cursos e aulas (vídeos do YouTube).
class CursoService {
  static Future<Map<String, dynamic>> listar() => Api.get('/cursos/');

  static Future<Map<String, dynamic>> detalhar(String id) =>
      Api.get('/cursos/$id');

  static Future<Map<String, dynamic>> marcarAula(
    String aulaId, {
    required bool concluida,
  }) =>
      Api.patch('/cursos/aulas/$aulaId/concluida',
          query: {'concluida': concluida});

  // ─── Gestão pela loja ───────────────────────────────
  static Future<Map<String, dynamic>> criar({
    required String titulo,
    String? descricao,
    String? categoria,
  }) =>
      Api.post('/cursos/', corpo: {
        'titulo': titulo,
        if (descricao != null && descricao.isNotEmpty) 'descricao': descricao,
        if (categoria != null && categoria.isNotEmpty) 'categoria': categoria,
      });

  static Future<Map<String, dynamic>> excluir(String id) =>
      Api.delete('/cursos/$id');

  /// Adiciona um vídeo: título, canal e capa vêm do próprio YouTube.
  static Future<Map<String, dynamic>> adicionarAula({
    required String cursoId,
    required String url,
    String? titulo,
  }) =>
      Api.post('/cursos/$cursoId/aulas', corpo: {
        'url': url,
        if (titulo != null && titulo.isNotEmpty) 'titulo': titulo,
      });

  /// Importa todos os vídeos de uma playlist de uma vez.
  static Future<Map<String, dynamic>> importarPlaylist({
    required String cursoId,
    required String url,
  }) =>
      Api.post('/cursos/$cursoId/aulas/playlist', corpo: {'url': url});

  static Future<Map<String, dynamic>> removerAula({
    required String cursoId,
    required String aulaId,
  }) =>
      Api.delete('/cursos/$cursoId/aulas/$aulaId');
}
