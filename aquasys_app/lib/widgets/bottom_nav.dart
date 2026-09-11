import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import '../Tema/app_tema.dart';

/// Barra inferior do Figma: ícone + rótulo e, no item ativo,
/// um traço horizontal logo abaixo do rótulo.
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
    final itens = <_ItemNav>[
      const _ItemNav(
        rotulo: 'Início',
        icone: Icon(Icons.home_outlined, size: 24),
        iconeAtivo: Icon(Icons.home_rounded, size: 24),
      ),
      const _ItemNav(
        rotulo: 'Aquários',
        icone: Icon(Icons.water_drop_outlined, size: 23),
        iconeAtivo: Icon(Icons.water_drop_rounded, size: 23),
      ),
      const _ItemNav(
        rotulo: 'Peixes',
        icone: FaIcon(FontAwesomeIcons.fish, size: 19),
        iconeAtivo: FaIcon(FontAwesomeIcons.fish, size: 19),
      ),
      _ItemNav(
        rotulo: isDono ? 'Clientes' : 'Cursos',
        icone: Icon(
          isDono ? Icons.groups_outlined : Icons.school_outlined,
          size: 24,
        ),
        iconeAtivo: Icon(
          isDono ? Icons.groups_rounded : Icons.school_rounded,
          size: 24,
        ),
      ),
    ];

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        border: const Border(
          top: BorderSide(color: AppTheme.bordaCard, width: 1),
        ),
        boxShadow: [
          BoxShadow(
            color: AppTheme.azulEscuro.withValues(alpha: 0.06),
            blurRadius: 20,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 62,
          child: Row(
            children: List.generate(itens.length, (i) {
              final ativo = i == currentIndex;
              final cor = ativo ? AppTheme.primaria : AppTheme.textoFraco;

              return Expanded(
                child: InkWell(
                  onTap: () => onTap(i),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      IconTheme(
                        data: IconThemeData(color: cor),
                        child: ativo ? itens[i].iconeAtivo : itens[i].icone,
                      ),
                      const SizedBox(height: 4),
                      // Uma linha só, sempre. Sem isto o rótulo quebra
                      // quando a largura aperta — e, no limite, uma letra
                      // por linha —, o que faz a coluna crescer muito além
                      // dos 62 px da barra e estourar o layout. Acontece
                      // ao encolher a janela no navegador, e aconteceria
                      // também com fonte de sistema muito ampliada.
                      Text(
                        itens[i].rotulo,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        softWrap: false,
                        style: TextStyle(
                          fontSize: 11,
                          color: cor,
                          fontWeight:
                              ativo ? FontWeight.w600 : FontWeight.w400,
                        ),
                      ),
                      const SizedBox(height: 4),
                      // Traço do item ativo
                      Container(
                        height: 2,
                        width: 34,
                        decoration: BoxDecoration(
                          color: ativo ? AppTheme.primaria : Colors.transparent,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}

class _ItemNav {
  final String rotulo;
  final Widget icone;
  final Widget iconeAtivo;

  const _ItemNav({
    required this.rotulo,
    required this.icone,
    required this.iconeAtivo,
  });
}
