import 'package:flutter/material.dart';

class AppTheme {
  // ─── Superfícies ──────────────────────────────────
  /// Fundo geral das telas.
  static const Color backgroundApp = Color(0xFFF8FCFF);

  /// Card branco — modais, formulários, corpo dos cards abertos.
  static const Color backgroundCard = Color(0xFFFFFFFF);

  /// Azul claro dos agrupamentos: barras de seção, linhas de lista,
  /// faixas internas (é a cor que domina as telas no Figma).
  static const Color superficieAzul = Color(0xFFCFDEE9);

  /// Versão suave do azul — blocos internos dentro de card branco.
  static const Color superficieSuave = Color(0xFFEAF4FB);

  /// Fundo de campo de formulário.
  static const Color backgroundLabel = Color(0xFFF8FCFF);

  // ─── Marca ────────────────────────────────────────
  /// Cor principal: botões, ícones ativos, links.
  static const Color primaria = Color(0xFF0096C7);

  /// Azul profundo — títulos fortes ("Bem-vindo", títulos de seção).
  static const Color azulEscuro = Color(0xFF023E8A);

  /// Azul médio — nomes de itens em listas e títulos de card.
  static const Color azulMedio = Color(0xCC023E8A);

  // ─── Texto ────────────────────────────────────────
  static const Color textoCorpo = Color(0x99000000);
  static const Color textoFraco = Color(0xFF737373);

  // ─── Bordas ───────────────────────────────────────
  static const Color bordaCard = Color(0xFFD6EAF5);
  static const Color bordaCampo = Color(0xFFB8DDF0);

  // ─── Status ───────────────────────────────────────
  static const Color sucesso = Color(0xFF28934F);
  static const Color sucessoBorda = Color(0xFFB1F0C8);
  static const Color sucessoFundo = Color(0xFFE7F8EF);

  static const Color alerta = Color(0xFFEAB308);
  static const Color alertaBorda = Color(0xFFEFE3BE);
  static const Color alertaFundo = Color(0xFFFFF9EC);
  static const Color alertaTexto = Color(0xFF7B6523);
  static const Color alertaPonto = Color(0xFFFACC15);

  static const Color error = Color(0xFFEF4444);
  static const Color errorFundo = Color(0xFFFFEBEE);

  // ─── Acentos dos cards de resumo ──────────────────
  static const Color acentoVerde = Color(0xFF22C55E);
  static const Color acentoAzul = Color(0xFF1565C0);
  static const Color acentoRosa = Color(0xFFCA2FA3);
  static const Color acentoLaranja = Color(0xFFE07A3E);

  static const Color white = Color(0xFFFFFFFF);

  // ─── Aliases legados ──────────────────────────────
  // Mantidos para não quebrar telas que ainda usam os nomes antigos.
  static const Color tituloBemVindo = azulEscuro;
  static const Color subtitulo = textoCorpo;
  static const Color labelCampo = azulEscuro;
  static const Color hintCampo = textoFraco;
  static const Color ctaEntrar = primaria;
  static const Color textDark = azulEscuro;

  // ─── Sombra padrão dos cards ──────────────────────
  static List<BoxShadow> get sombraCard => [
        BoxShadow(
          color: azulEscuro.withValues(alpha: 0.06),
          blurRadius: 24,
          spreadRadius: -6,
          offset: const Offset(0, 10),
        ),
        BoxShadow(
          color: azulEscuro.withValues(alpha: 0.04),
          blurRadius: 6,
          offset: const Offset(0, 2),
        ),
      ];

  // App é mobile-only: hover não existe em toque, então é
  // neutralizado para o preview no navegador não enganar o layout.
  static final WidgetStateProperty<Color?> _semHover =
      WidgetStateProperty.resolveWith((estados) {
    if (estados.contains(WidgetState.pressed)) {
      return Colors.white.withValues(alpha: 0.16);
    }
    return Colors.transparent;
  });

  static ThemeData get theme => ThemeData(
        useMaterial3: true,
        fontFamily: 'Roboto',
        scaffoldBackgroundColor: backgroundApp,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primaria,
          brightness: Brightness.light,
        ),

        // ─── Neutraliza hover em toda a árvore ──────────
        hoverColor: Colors.transparent,

        appBarTheme: const AppBarTheme(
          backgroundColor: backgroundApp,
          foregroundColor: azulEscuro,
          elevation: 0,
        ),

        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: primaria,
            foregroundColor: white,
            disabledBackgroundColor: primaria.withValues(alpha: 0.5),
            disabledForegroundColor: white,
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
                return error.withValues(alpha: 0.08);
              }
              return Colors.transparent;
            }),
          ),
        ),

        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom().copyWith(
            overlayColor: WidgetStateProperty.resolveWith((estados) {
              if (estados.contains(WidgetState.pressed)) {
                return primaria.withValues(alpha: 0.08);
              }
              return Colors.transparent;
            }),
          ),
        ),

        iconButtonTheme: IconButtonThemeData(
          style: ButtonStyle(
              overlayColor: WidgetStateProperty.resolveWith((estados) {
            if (estados.contains(WidgetState.pressed)) {
              return primaria.withValues(alpha: 0.10);
            }
            return Colors.transparent;
          })),
        ),

        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: backgroundLabel,
          hoverColor: Colors.transparent,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
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
            borderSide: const BorderSide(color: primaria, width: 1.5),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: error),
          ),
          focusedErrorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: error, width: 1.5),
          ),
          hintStyle: const TextStyle(color: textoFraco, fontSize: 13),
        ),
      );
}

/// ═══════════════════════════════════════════════════════════
/// WIDGETS REUTILIZÁVEIS — repetem o desenho do Figma
/// ═══════════════════════════════════════════════════════════

/// Barra de seção azul-clara ("Meus Aquários", "Acesso para clientes").
class BarraSecao extends StatelessWidget {
  final String titulo;
  final String? subtitulo;
  final Widget? acao;
  final bool centralizado;

  const BarraSecao({
    super.key,
    required this.titulo,
    this.subtitulo,
    this.acao,
    this.centralizado = false,
  });

  @override
  Widget build(BuildContext context) {
    final texto = Column(
      crossAxisAlignment:
          centralizado ? CrossAxisAlignment.center : CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          titulo,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        if (subtitulo != null) ...[
          const SizedBox(height: 2),
          Text(
            subtitulo!,
            style: const TextStyle(fontSize: 12.5, color: AppTheme.textoFraco),
          ),
        ],
      ],
    );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppTheme.superficieAzul,
        borderRadius: BorderRadius.circular(12),
      ),
      child: centralizado
          ? Center(child: texto)
          : Row(
              children: [
                Expanded(child: texto),
                ?acao,
              ],
            ),
    );
  }
}

/// Chip de ícone — forma sólida com ícone branco dentro.
class ChipIcone extends StatelessWidget {
  final Widget icone;
  final Color cor;
  final double tamanho;
  final bool circular;

  const ChipIcone({
    super.key,
    required this.icone,
    this.cor = AppTheme.primaria,
    this.tamanho = 40,
    this.circular = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: tamanho,
      height: tamanho,
      decoration: BoxDecoration(
        color: cor,
        shape: circular ? BoxShape.circle : BoxShape.rectangle,
        borderRadius: circular ? null : BorderRadius.circular(12),
      ),
      child: Center(child: icone),
    );
  }
}

/// Linha de lista azul-clara com ícone à esquerda (menu de Clientes,
/// lista de acessos, lista de manutenções).
class LinhaLista extends StatelessWidget {
  final Widget icone;
  final String titulo;
  final String? subtitulo;
  final List<Widget> acoes;
  final VoidCallback? onTap;

  const LinhaLista({
    super.key,
    required this.icone,
    required this.titulo,
    this.subtitulo,
    this.acoes = const [],
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.superficieAzul,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Row(
            children: [
              ChipIcone(icone: icone),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      titulo,
                      style: const TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.azulMedio,
                      ),
                    ),
                    if (subtitulo != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        subtitulo!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.textoFraco,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              ...acoes,
            ],
          ),
        ),
      ),
    );
  }
}

/// Botão vermelho sólido de "Cancelar" — o Figma usa preenchido, não outline.
class BotaoCancelar extends StatelessWidget {
  final VoidCallback? onPressed;
  final String texto;

  const BotaoCancelar({super.key, this.onPressed, this.texto = 'Cancelar'});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppTheme.error,
        foregroundColor: AppTheme.white,
        minimumSize: const Size(double.infinity, 48),
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
      ),
      child: Text(texto),
    );
  }
}
