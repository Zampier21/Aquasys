class Config {
  /// Endereço da API.
  static const String apiUrl = String.fromEnvironment(
    'AQUASYS_API',
    defaultValue: 'http://127.0.0.1:8000',
  );
}
