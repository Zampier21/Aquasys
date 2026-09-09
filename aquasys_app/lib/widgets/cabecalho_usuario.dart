import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../Services/auth_service.dart';
import '../Telas/tela_configuracoes.dart';

/// Cabeçalho comum a todas as telas internas:
/// foto (ou logo) + saudação + engrenagem que abre as Configurações.
///
/// Nome e foto vêm da cópia local gravada no login e atualizada pela tela
/// de Configurações — não de uma requisição. O cabeçalho aparece em toda
/// tela do app; buscar isso na rede a cada abertura seria uma chamada por
/// navegação para um dado que quase nunca muda.
class CabecalhoUsuario extends StatefulWidget {
  final String tipoUsuario;
  const CabecalhoUsuario({super.key, required this.tipoUsuario});

  @override
  State<CabecalhoUsuario> createState() => _CabecalhoUsuarioState();
}

class _CabecalhoUsuarioState extends State<CabecalhoUsuario> {
  String? _nome;
  String? _avatar;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    final nome = await AuthService.getNomeUsuario();
    final avatar = await AuthService.getAvatar();
    if (!mounted) return;
    setState(() {
      _nome = nome;
      _avatar = avatar;
    });
  }

  Future<void> _abrirConfiguracoes() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const TelaConfiguracoes()),
    );
    // Voltou das Configurações: o nome ou a foto podem ter mudado.
    if (mounted) _carregar();
  }

  @override
  Widget build(BuildContext context) {
    final isDono = widget.tipoUsuario == 'dono';
    final nome = (_nome != null && _nome!.isNotEmpty)
        ? _nome!
        : (isDono ? 'Empresa de aquarismo' : 'Cliente');

    return Row(
      children: [
        GestureDetector(
          onTap: _abrirConfiguracoes,
          child: Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppTheme.primaria,
              borderRadius: BorderRadius.circular(12),
            ),
            clipBehavior: Clip.antiAlias,
            child: AvatarDaConta(
              base64: _avatar,
              isDono: isDono,
              tamanho: 44,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Olá, $nome',
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                isDono ? 'Acesso empresarial' : 'Acesso cliente',
                style: const TextStyle(fontSize: 12, color: AppTheme.textoFraco),
              ),
            ],
          ),
        ),
        IconButton(
          icon: const Icon(Icons.settings_outlined, color: AppTheme.textoFraco),
          tooltip: 'Configurações',
          onPressed: _abrirConfiguracoes,
        ),
      ],
    );
  }
}
