import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../widgets/bottom_nav.dart';
import 'tela_inicial.dart';
import 'tela_aquarios.dart';
import 'tela_peixes.dart';

class TelaClientes extends StatelessWidget {
  final String tipoUsuario;
  const TelaClientes({super.key, required this.tipoUsuario});

  void _onNavTap(BuildContext context, int index) {
    switch (index) {
      case 0:
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => TelaInicial(tipoUsuario: tipoUsuario)));
        break;
      case 1:
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => TelaAquarios(tipoUsuario: tipoUsuario)));
        break;
      case 2:
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => TelaPeixes(tipoUsuario: tipoUsuario)));
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: Center(
          child: Text(
            tipoUsuario == 'dono' ? 'Tela Clientes — em desenvolvimento' : 'Tela Cursos — em desenvolvimento',
            style: const TextStyle(color: AppTheme.tituloBemVindo),
          ),
        ),
      ),
      bottomNavigationBar: BottomNav(
        currentIndex: 3,
        onTap: (i) => _onNavTap(context, i),
        isDono: tipoUsuario == 'dono',
      ),
    );
  }
}