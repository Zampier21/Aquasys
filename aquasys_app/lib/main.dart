import 'package:flutter/material.dart';
import 'tema/app_tema.dart';
import 'Telas/tela_login.dart';

void main() {
  runApp(const AquaSysApp());
}

class AquaSysApp extends StatelessWidget {
  const AquaSysApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AquaSys',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const LoginScreen(),
    );
  }
}