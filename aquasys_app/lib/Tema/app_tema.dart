import 'package:flutter/material.dart';

class AppTheme {
  // ─── Cores do Figma ───────────────────────────────
  static const Color backgroundApp   = Color(0xFFF8FCFF);
  static const Color backgroundCard  = Color(0xFFFFFFFF);
  static const Color backgroundLabel = Color(0xFFF8FCFF);
  static const Color tituloBemVindo  = Color(0xFF023E8A);
  static const Color subtitulo       = Color(0x99000000);
  static const Color labelCampo      = Color(0xFF023E8A);
  static const Color hintCampo       = Color(0xFF737373);
  static const Color ctaEntrar       = Color(0xFF0096C7);
  static const Color bordaCard       = Color(0xFFD6EAF5);
  static const Color bordaCampo      = Color(0xFFB8DDF0);
  static const Color white           = Color(0xFFFFFFFF);
  static const Color textDark        = Color(0xFF023E8A);
  static const Color error           = Color(0xFFE53935);

  // App é mobile-only: hover não existe em toque, então é
  // neutralizado para o preview no navegador não enganar o layout.
  static final WidgetStateProperty<Color?> _semHover =
      WidgetStateProperty.resolveWith((estados) {
    if (estados.contains(WidgetState.pressed)) {
      return Colors.white.withOpacity(0.16);
    }
    return Colors.transparent;
  });

  static ThemeData get theme => ThemeData(
    useMaterial3: true,
    fontFamily: 'Roboto',
    scaffoldBackgroundColor: backgroundApp,
    colorScheme: ColorScheme.fromSeed(
      seedColor: ctaEntrar,
      brightness: Brightness.light,
    ),

    // ─── Neutraliza hover em toda a árvore ──────────
    hoverColor: Colors.transparent,

    appBarTheme: const AppBarTheme(
      backgroundColor: backgroundApp,
      foregroundColor: textDark,
      elevation: 0,
    ),

    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: ctaEntrar,
        foregroundColor: white,
        minimumSize: const Size(double.infinity, 52),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        elevation: 0,
        textStyle: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
        ),
      ).copyWith(overlayColor: _semHover),
    ),

    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(double.infinity, 52),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ).copyWith(
        overlayColor: WidgetStateProperty.resolveWith((estados) {
          if (estados.contains(WidgetState.pressed)) {
            return error.withOpacity(0.08);
          }
          return Colors.transparent;
        }),
      ),
    ),

    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom().copyWith(
        overlayColor: WidgetStateProperty.resolveWith((estados) {
          if (estados.contains(WidgetState.pressed)) {
            return ctaEntrar.withOpacity(0.08);
          }
          return Colors.transparent;
        }),
      ),
    ),

    iconButtonTheme: IconButtonThemeData(
      style: ButtonStyle(overlayColor: WidgetStateProperty.resolveWith((estados) {
        if (estados.contains(WidgetState.pressed)) {
          return ctaEntrar.withOpacity(0.10);
        }
        return Colors.transparent;
      })),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: backgroundLabel,
      hoverColor: Colors.transparent,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: bordaCampo),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: bordaCampo),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: ctaEntrar, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: error),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: error, width: 1.5),
      ),
      hintStyle: const TextStyle(color: hintCampo, fontSize: 13),
    ),
  );
}