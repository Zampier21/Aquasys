/// Configuração de execução do app.
///
/// Fica isolada aqui para `Api` e `AuthService` compartilharem o mesmo
/// endereço sem um importar o outro.
class Config {
  /// Endereço da API.
  ///
  /// Trocável na hora de rodar, sem editar código — indispensável para
  /// testar no celular, onde `127.0.0.1` seria o próprio aparelho:
  ///
  ///   flutter run --dart-define=AQUASYS_API=http://192.168.0.10:8000
  ///
  /// Descubra o IP da sua máquina com `ipconfig` (Windows) e garanta que
  /// a API esteja ouvindo fora do localhost:
  ///
  ///   uvicorn app.main:app --host 0.0.0.0 --port 8000
  static const String apiUrl = String.fromEnvironment(
    'AQUASYS_API',
    defaultValue: 'http://127.0.0.1:8000',
  );
}
