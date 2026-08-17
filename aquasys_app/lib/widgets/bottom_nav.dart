import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import '../Tema/app_tema.dart';

class BottomNav extends StatelessWidget {
  final int currentIndex;
  final Function(int) onTap;
  final bool isDono;

  const BottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
    this.isDono = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        border: const Border(
          top: BorderSide(color: AppTheme.bordaCard, width: 1),
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF023E8A).withOpacity(0.06),
            blurRadius: 20,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: BottomNavigationBar(
        currentIndex: currentIndex,
        onTap: onTap,
        type: BottomNavigationBarType.fixed,
        backgroundColor: AppTheme.white,
        selectedItemColor: AppTheme.ctaEntrar,
        unselectedItemColor: AppTheme.hintCampo,
        selectedLabelStyle: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelStyle: const TextStyle(fontSize: 11),
        elevation: 0,
        items: [
          // ─── Início ─────────────────────────────────
          const BottomNavigationBarItem(
            icon: Icon(Icons.home_outlined, size: 24),
            activeIcon: Icon(Icons.home_rounded, size: 24),
            label: 'Início',
          ),

          // ─── Aquários — gota d'água, igual aos cards ─
          const BottomNavigationBarItem(
            icon: Icon(Icons.water_drop_outlined, size: 23),
            activeIcon: Icon(Icons.water_drop_rounded, size: 23),
            label: 'Aquários',
          ),

          // ─── Peixes — mesmo peixe dos cards ─────────
          const BottomNavigationBarItem(
            icon: Padding(
              padding: EdgeInsets.only(top: 2, bottom: 2),
              child: FaIcon(FontAwesomeIcons.fish, size: 19),
            ),
            activeIcon: Padding(
              padding: EdgeInsets.only(top: 2, bottom: 2),
              child: FaIcon(FontAwesomeIcons.fish, size: 19),
            ),
            label: 'Peixes',
          ),

          // ─── Clientes / Cursos ──────────────────────
          BottomNavigationBarItem(
            icon: Icon(
              isDono ? Icons.groups_outlined : Icons.school_outlined,
              size: 24,
            ),
            activeIcon: Icon(
              isDono ? Icons.groups_rounded : Icons.school_rounded,
              size: 24,
            ),
            label: isDono ? 'Clientes' : 'Cursos',
          ),
        ],
      ),
    );
  }
}