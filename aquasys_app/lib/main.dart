import 'package:flutter/material.dart';
import 'Tema/app_tema.dart';
import 'Services/auth_service.dart';
import 'Services/notificacao_service.dart';
import 'Telas/tela_login.dart';
import 'Telas/tela_inicial.dart';
import 'Telas/tela_aquarios.dart';

void main() {
  runApp(const AquaSysApp());
}
final GlobalKey<NavigatorState> navegador = GlobalKey<NavigatorState>();

class AquaSysApp extends StatelessWidget {
  const AquaSysApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AquaSys',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      navigatorKey: navegador,
      home: const _Abertura(),
    );
  }
}

class _Abertura extends StatefulWidget {
  const _Abertura();

  @override
  State<_Abertura> createState() => _AberturaState();
}

class _AberturaState extends State<_Abertura> {
  Widget? _destino;

  @override
  void initState() {
    super.initState();
    _decidir();
  }

  Future<void> _decidir() async {
    await NotificacaoService.iniciar();

    // Tocar no lembrete abre a lista de aquários, onde o parâmetro
    // problemático pode ser corrigido.
    NotificacaoService.aoTocar = (_) async {
      final tipo = await AuthService.getTipoUsuario();
      if (tipo == null) return;
      navegador.currentState?.push(
        MaterialPageRoute(builder: (_) => TelaAquarios(tipoUsuario: tipo)),
      );
    };

    final logado = await AuthService.estaLogado();
    final tipo = await AuthService.getTipoUsuario();
    if (!mounted) return;

    setState(() {
      // Sem tipo salvo a sessão está pela metade — melhor refazer o login.
      _destino = (logado && tipo != null)
          ? TelaInicial(tipoUsuario: tipo)
          : const LoginScreen();
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_destino == null) {
      return const Scaffold(
        backgroundColor: AppTheme.backgroundApp,
        body: Center(
          child: CircularProgressIndicator(color: AppTheme.primaria),
        ),
      );
    }
    return _destino!;
  }
}
