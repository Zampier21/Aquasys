import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../widgets/bottom_nav.dart';
import '../widgets/cabecalho_usuario.dart';
import 'tela_inicial.dart';
import 'tela_aquarios.dart';
import 'tela_peixes.dart';
import 'tela_acessos_clientes.dart';
import 'tela_manutencoes.dart';
import 'tela_clientes_manutencao.dart';
import 'tela_cursos.dart';

/// Aba 4 da barra inferior.
///
/// Para o acesso empresarial (CNPJ) é o menu de Clientes.
/// Para o acesso do cliente (CPF) é a área de Cursos.
class TelaClientes extends StatelessWidget {
  final String tipoUsuario;
  const TelaClientes({super.key, required this.tipoUsuario});

  bool get _isDono => tipoUsuario == 'dono';

  void _onNavTap(BuildContext context, int index) {
    if (index == 3) return;
    final destino = switch (index) {
      0 => TelaInicial(tipoUsuario: tipoUsuario),
      1 => TelaAquarios(tipoUsuario: tipoUsuario),
      _ => TelaPeixes(tipoUsuario: tipoUsuario),
    };
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => destino),
    );
  }

  void _abrir(BuildContext context, Widget tela) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => tela));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CabecalhoUsuario(tipoUsuario: tipoUsuario),
              const SizedBox(height: 26),
              if (_isDono) ..._menuDono(context) else ..._areaCursos(),
            ],
          ),
        ),
      ),
      bottomNavigationBar: BottomNav(
        currentIndex: 3,
        onTap: (i) => _onNavTap(context, i),
        isDono: _isDono,
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // MENU DO ACESSO EMPRESARIAL
  // ═══════════════════════════════════════════════════
  List<Widget> _menuDono(BuildContext context) {
    return [
      LinhaLista(
        icone: const Icon(Icons.person_add_alt_1_rounded,
            color: AppTheme.white, size: 21),
        titulo: 'Acessos para clientes',
        subtitulo: 'Controle de credenciais',
        onTap: () => _abrir(context, const TelaAcessosClientes()),
      ),
      const SizedBox(height: 12),
      LinhaLista(
        icone: const Icon(Icons.assignment_rounded,
            color: AppTheme.white, size: 21),
        titulo: 'Manutenções',
        subtitulo: 'Controle de manutenções clientes',
        onTap: () => _abrir(context, const TelaManutencoes()),
      ),
      const SizedBox(height: 12),
      LinhaLista(
        icone: const Icon(Icons.handyman_rounded,
            color: AppTheme.white, size: 21),
        titulo: 'Clientes de manutenção',
        subtitulo: 'Contatos que você atende em casa',
        onTap: () => _abrir(context, const TelaClientesManutencao()),
      ),
      const SizedBox(height: 12),
      LinhaLista(
        icone: const Icon(Icons.school_rounded,
            color: AppTheme.white, size: 21),
        titulo: 'Cursos',
        subtitulo: 'Conteúdo em vídeo para seus clientes',
        onTap: () => _abrir(context, const _PaginaCursos()),
      ),
    ];
  }

  // ═══════════════════════════════════════════════════
  // ÁREA DE CURSOS (acesso do cliente)
  // ═══════════════════════════════════════════════════
  List<Widget> _areaCursos() {
    return const [TelaCursos()];
  }
}

/// Envelope com Scaffold para abrir a lista de cursos como página
/// própria — no acesso do cliente ela é embutida na aba.
class _PaginaCursos extends StatelessWidget {
  const _PaginaCursos();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundApp,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppTheme.azulMedio),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: const TelaCursos(),
        ),
      ),
    );
  }
}
