import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import '../Tema/app_tema.dart';
import '../widgets/bottom_nav.dart';
import '../services/auth_service.dart';
import 'tela_aquarios.dart';
import 'tela_peixes.dart';
import 'tela_clientes.dart';

class TelaInicial extends StatefulWidget {
  final String tipoUsuario;
  const TelaInicial({super.key, required this.tipoUsuario});

  @override
  State<TelaInicial> createState() => _TelaInicialState();
}

class _TelaInicialState extends State<TelaInicial> {
  // Sombra padrão dos cards — duas camadas para profundidade real
  static final List<BoxShadow> _sombraCard = [
    BoxShadow(
      color: const Color(0xFF023E8A).withOpacity(0.06),
      blurRadius: 24,
      spreadRadius: -6,
      offset: const Offset(0, 10),
    ),
    BoxShadow(
      color: const Color(0xFF023E8A).withOpacity(0.04),
      blurRadius: 6,
      offset: const Offset(0, 2),
    ),
  ];

  void _onNavTap(int index) {
    if (index == 0) return;
    final t = widget.tipoUsuario;
    final destino = switch (index) {
      1 => TelaAquarios(tipoUsuario: t),
      2 => TelaPeixes(tipoUsuario: t),
      _ => TelaClientes(tipoUsuario: t),
    };
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => destino));
  }

  void _logout() async {
    await AuthService.logout();
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final isDono = widget.tipoUsuario == 'dono';

    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(isDono),
              const SizedBox(height: 26),
              _buildTituloSecao('Meu Painel', 'Resumo dos seus aquários'),
              const SizedBox(height: 14),
              _buildCardsResumo(),
              const SizedBox(height: 18),
              _buildAlerta(),
              const SizedBox(height: 18),
              _buildDicas(),
              const SizedBox(height: 18),
              _buildAtalhos(isDono),
            ],
          ),
        ),
      ),
      bottomNavigationBar: BottomNav(
        currentIndex: 0,
        onTap: _onNavTap,
        isDono: isDono,
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // HEADER — igual ao Figma
  // ═══════════════════════════════════════════════════
  Widget _buildHeader(bool isDono) {
    return Row(
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: AppTheme.ctaEntrar.withOpacity(0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.business, color: AppTheme.ctaEntrar, size: 24),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isDono ? 'Olá, Empresa de aquarismo' : 'Olá, Cliente',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.tituloBemVindo,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                isDono ? 'Acesso empresarial' : 'Acesso cliente',
                style: const TextStyle(fontSize: 12, color: AppTheme.hintCampo),
              ),
            ],
          ),
        ),
        IconButton(
          icon: const Icon(Icons.settings_outlined, color: AppTheme.hintCampo),
          onPressed: _logout,
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════
  // TÍTULO DE SEÇÃO
  // ═══════════════════════════════════════════════════
  Widget _buildTituloSecao(String titulo, String subtitulo) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          titulo,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: AppTheme.tituloBemVindo,
          ),
        ),
        const SizedBox(height: 2),
        Text(subtitulo, style: const TextStyle(fontSize: 13, color: AppTheme.hintCampo)),
      ],
    );
  }

  // ═══════════════════════════════════════════════════
  // CARDS DE RESUMO — altura fixa, todos nivelados
  // ═══════════════════════════════════════════════════
  Widget _buildCardsResumo() {
    return SizedBox(
      height: 138,
      child: Row(
        children: [
          Expanded(
            child: _cardResumo(
              '2',
              'Meus\nAquários',
              const Icon(Icons.water_drop_rounded, color: Color(0xFF0096C7), size: 20),
              const Color(0xFF0096C7),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _cardResumo(
              '18',
              'Peixes',
              const FaIcon(FontAwesomeIcons.fish, color: Color(0xFF00A878), size: 17),
              const Color(0xFF00A878),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _cardResumo(
              '95%',
              'Saúde\ngeral',
              const Icon(Icons.trending_up_rounded, color: Color(0xFF1565C0), size: 21),
              const Color(0xFF1565C0),
            ),
          ),
        ],
      ),
    );
  }

  Widget _cardResumo(String valor, String label, Widget icone, Color cor) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.bordaCard),
        boxShadow: _sombraCard,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: cor.withOpacity(0.10),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(child: icone),
          ),
          const SizedBox(height: 10),
          Text(
            valor,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: cor,
              height: 1,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 11.5,
              color: AppTheme.hintCampo,
              height: 1.25,
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ALERTA — conteúdo do Figma, header separado
  // ═══════════════════════════════════════════════════
  Widget _buildAlerta() {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFFCE4B0)),
        boxShadow: _sombraCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
            decoration: const BoxDecoration(
              color: Color(0xFFFFF9EC),
              borderRadius: BorderRadius.vertical(top: Radius.circular(15)),
              border: Border(bottom: BorderSide(color: Color(0xFFFCE4B0))),
            ),
            child: Row(
              children: [
                Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF59E0B).withOpacity(0.14),
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: const Icon(Icons.warning_amber_rounded,
                      color: Color(0xFFD97706), size: 18),
                ),
                const SizedBox(width: 10),
                const Text(
                  'Atenção',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF92400E),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      margin: const EdgeInsets.only(top: 5),
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: Color(0xFFF59E0B),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Comunitário',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.tituloBemVindo,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Ph do aquário "Comunitário" está 0.3 acima do ideal',
                            style: TextStyle(
                              fontSize: 12.5,
                              color: Colors.black.withOpacity(0.62),
                              height: 1.35,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                InkWell(
                  onTap: () => _onNavTap(1),
                  borderRadius: BorderRadius.circular(8),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      children: [
                        Text(
                          'Ver meus aquários',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.ctaEntrar,
                          ),
                        ),
                        SizedBox(width: 4),
                        Icon(Icons.chevron_right_rounded,
                            size: 18, color: AppTheme.ctaEntrar),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // DICAS — textos do Figma, layout com ícone contextual
  // ═══════════════════════════════════════════════════
  Widget _buildDicas() {
    final dicas = <Map<String, dynamic>>[
      {
        'icon': const Icon(Icons.water_drop_rounded, size: 16, color: Color(0xFF0096C7)),
        'cor': const Color(0xFF0096C7),
        'titulo': 'Troca parcial de água',
        'texto': 'Lembre-se de que está prevista para esta semana',
      },
      {
        'icon': const FaIcon(FontAwesomeIcons.fish, size: 14, color: Color(0xFF00A878)),
        'cor': const Color(0xFF00A878),
        'titulo': 'Neon tetras em cardume',
        'texto': 'Seus neon tetras precisam estar em um grupo ideal de 10 peixes',
      },
      {
        'icon': const Icon(Icons.thermostat_rounded, size: 16, color: Color(0xFFE07A3E)),
        'cor': const Color(0xFFE07A3E),
        'titulo': 'Temperatura ideal',
        'texto': 'Mantenha seus aquários entre 26 °C e 28 °C',
      },
    ];

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.bordaCard),
        boxShadow: _sombraCard,
      ),
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
            decoration: const BoxDecoration(
              color: Color(0xFFF4FAFE),
              borderRadius: BorderRadius.vertical(top: Radius.circular(15)),
              border: Border(bottom: BorderSide(color: AppTheme.bordaCard)),
            ),
            child: Row(
              children: [
                Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    color: AppTheme.ctaEntrar.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: const Icon(Icons.lightbulb_outline_rounded,
                      color: AppTheme.ctaEntrar, size: 17),
                ),
                const SizedBox(width: 10),
                const Text(
                  'Dicas para você',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.tituloBemVindo,
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            child: Column(
              children: List.generate(dicas.length, (i) {
                final d = dicas[i];
                return Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 34,
                            height: 34,
                            decoration: BoxDecoration(
                              color: (d['cor'] as Color).withOpacity(0.10),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Center(child: d['icon'] as Widget),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  d['titulo'] as String,
                                  style: const TextStyle(
                                    fontSize: 13.5,
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.tituloBemVindo,
                                    height: 1.3,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  d['texto'] as String,
                                  style: TextStyle(
                                    fontSize: 12.5,
                                    color: Colors.black.withOpacity(0.55),
                                    height: 1.35,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (i < dicas.length - 1)
                      Divider(
                        height: 1,
                        color: AppTheme.bordaCard.withOpacity(0.7),
                        indent: 46,
                      ),
                  ],
                );
              }),
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ATALHOS
  // ═══════════════════════════════════════════════════
  Widget _buildAtalhos(bool isDono) {
    return SizedBox(
      height: 108,
      child: Row(
        children: [
          Expanded(
            child: _cardAtalho(
              'Aquários',
              'Gerenciar',
              const Icon(Icons.water_drop_rounded, color: Color(0xFF0096C7), size: 20),
              const Color(0xFF0096C7),
              () => _onNavTap(1),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _cardAtalho(
              isDono ? 'Clientes' : 'Aprender',
              isDono ? 'Gerenciar' : 'Mini cursos',
              Icon(
                isDono ? Icons.groups_rounded : Icons.school_rounded,
                color: const Color(0xFFD6337F),
                size: 21,
              ),
              const Color(0xFFD6337F),
              () => _onNavTap(3),
            ),
          ),
        ],
      ),
    );
  }

  Widget _cardAtalho(
    String titulo,
    String subtitulo,
    Widget icone,
    Color cor,
    VoidCallback onTap,
  ) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            color: AppTheme.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.bordaCard),
            boxShadow: _sombraCard,
          ),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: cor.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Center(child: icone),
              ),
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
                        fontWeight: FontWeight.w700,
                        color: AppTheme.tituloBemVindo,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitulo,
                      style: const TextStyle(fontSize: 12, color: AppTheme.hintCampo),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: AppTheme.hintCampo.withOpacity(0.6),
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}