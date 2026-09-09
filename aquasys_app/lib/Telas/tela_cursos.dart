import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../Services/auth_service.dart';
import '../Services/curso_service.dart';
import 'tela_curso_detalhe.dart';

/// Lista de cursos.
///
/// Publicar curso é coisa da conta empresarial. O acesso do cliente
/// (CPF) só assiste o que a loja dele disponibilizou.
///
/// Quem decide isso é o tipo do usuário logado, lido aqui dentro — e não
/// um parâmetro de quem constrói a tela. Assim não existe caminho, nem
/// por engano, em que a área do cliente mostre botão de publicar.
class TelaCursos extends StatefulWidget {
  const TelaCursos({super.key});

  @override
  State<TelaCursos> createState() => _TelaCursosState();
}

class _TelaCursosState extends State<TelaCursos> {
  List<Map<String, dynamic>> _cursos = [];
  bool _carregando = true;
  bool _podeGerenciar = false;
  String? _erro;

  /// Ids marcados no modo de seleção. Vazio = modo normal.
  ///
  /// Só entram cursos da própria loja: curso global é conteúdo do
  /// AquaSys e a API recusa a exclusão, então nem deixamos marcar —
  /// melhor não oferecer do que oferecer e falhar.
  final Set<String> _selecionados = {};
  bool _excluindo = false;

  bool get _selecionando => _selecionados.isNotEmpty;

  bool _podeExcluir(Map<String, dynamic> curso) =>
      _podeGerenciar && curso['curso_global'] == false;

  @override
  void initState() {
    super.initState();
    _descobrirPermissao();
    _carregar();
  }

  Future<void> _descobrirPermissao() async {
    final tipo = await AuthService.getTipoUsuario();
    if (mounted) setState(() => _podeGerenciar = tipo == 'dono');
  }

  Future<void> _carregar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    final resultado = await CursoService.listar();
    if (!mounted) return;

    setState(() {
      _carregando = false;
      _selecionados.clear();
      if (resultado['sucesso'] == true) {
        _cursos = List<Map<String, dynamic>>.from(resultado['dados']);
      } else {
        _erro = resultado['erro'];
      }
    });
  }

  // ─── Seleção múltipla ───────────────────────────────────
  void _alternar(Map<String, dynamic> curso) {
    if (!_podeExcluir(curso)) return;
    final id = curso['id'].toString();
    setState(() {
      if (!_selecionados.remove(id)) _selecionados.add(id);
    });
  }

  void _limparSelecao() => setState(_selecionados.clear);

  Future<void> _excluirSelecionados() =>
      _confirmarEExcluir(_selecionados.toList());

  /// Exclui um curso sozinho, sem entrar no modo de seleção.
  ///
  /// Separado de propósito: se o botão da lixeira marcasse o card para
  /// depois excluir, cancelar o aviso deixaria a tela presa em seleção
  /// com um item marcado que o usuário nunca pediu para marcar.
  Future<void> _excluirUm(Map<String, dynamic> curso) =>
      _confirmarEExcluir([curso['id'].toString()]);

  Future<void> _confirmarEExcluir(List<String> ids) async {
    final quantos = ids.length;
    if (quantos == 0) return;

    final nomes = _cursos
        .where((c) => ids.contains(c['id'].toString()))
        .map((c) => c['titulo']?.toString() ?? '')
        .toList();

    final confirmou = await showDialog<bool>(
      context: context,
      builder: (dialogo) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          quantos == 1 ? 'Excluir curso' : 'Excluir $quantos cursos',
          style: const TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.tituloBemVindo,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              quantos == 1
                  ? 'O curso "${nomes.first}" e as aulas dele serão apagados.'
                  : 'Estes cursos e as aulas deles serão apagados:',
              style: TextStyle(
                fontSize: 13.5,
                height: 1.4,
                color: Colors.black.withValues(alpha: 0.65),
              ),
            ),
            // Listar os nomes evita o erro clássico da seleção múltipla:
            // apagar em lote sem perceber que um item errado foi marcado.
            if (quantos > 1) ...[
              const SizedBox(height: 8),
              for (final nome in nomes)
                Padding(
                  padding: const EdgeInsets.only(bottom: 3),
                  child: Text(
                    '• $nome',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.tituloBemVindo,
                    ),
                  ),
                ),
            ],
            const SizedBox(height: 10),
            const Text(
              'Essa ação não pode ser desfeita.',
              style: TextStyle(fontSize: 12.5, color: AppTheme.error),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogo, false),
            child: const Text('Cancelar',
                style: TextStyle(color: AppTheme.hintCampo)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.error,
              minimumSize: const Size(0, 42),
            ),
            onPressed: () => Navigator.pop(dialogo, true),
            child: const Text('Excluir'),
          ),
        ],
      ),
    );

    if (confirmou != true || !mounted) return;

    setState(() => _excluindo = true);

    // Um por vez, guardando quem falhou: se o quinto der erro, os quatro
    // primeiros já foram — dizer "erro ao excluir" e nada mais deixaria
    // a lista e a tela em desacordo.
    final falharam = <String>[];
    for (final id in ids) {
      final resposta = await CursoService.excluir(id);
      if (resposta['sucesso'] != true) falharam.add(id);
    }
    if (!mounted) return;

    setState(() => _excluindo = false);
    await _carregar();
    if (!mounted) return;

    final apagados = quantos - falharam.length;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          falharam.isEmpty
              ? (apagados == 1
                  ? 'Curso excluído'
                  : '$apagados cursos excluídos')
              : 'Excluídos $apagados de $quantos — tente os demais de novo',
        ),
        backgroundColor:
            falharam.isEmpty ? AppTheme.ctaEntrar : AppTheme.error,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _abrir(Map<String, dynamic> curso) async {
    // Com a seleção aberta, o toque marca em vez de navegar — é o que
    // se espera depois de já ter segurado um item.
    if (_selecionando) {
      _alternar(curso);
      return;
    }

    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => TelaCursoDetalhe(
          cursoId: curso['id'],
          // Curso global é conteúdo do AquaSys: a loja também não edita.
          // Curso global é conteúdo do AquaSys: nem a loja edita.
          podeEditar: _podeGerenciar && curso['curso_global'] == false,
        ),
      ),
    );
    _carregar();
  }

  @override
  Widget build(BuildContext context) {
    // Com itens marcados, o botão voltar do Android desfaz a seleção em
    // vez de sair da tela — é o comportamento de qualquer app que tem
    // seleção múltipla, e evita perder o que já foi marcado sem querer.
    return PopScope(
      canPop: !_selecionando,
      onPopInvokedWithResult: (saiu, _) {
        if (!saiu && _selecionando) _limparSelecao();
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_selecionando) _barraSelecao() else _barraNormal(),
          const SizedBox(height: 16),
          _buildConteudo(),
        ],
      ),
    );
  }

  // ─── Barra de seleção, no lugar do cabeçalho da seção ───
  Widget _barraSelecao() {
    final quantos = _selecionados.length;

    return Container(
      padding: const EdgeInsets.fromLTRB(6, 6, 10, 6),
      decoration: BoxDecoration(
        color: AppTheme.superficieAzul,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.bordaCard),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.close_rounded, color: AppTheme.azulMedio),
            tooltip: 'Cancelar seleção',
            onPressed: _excluindo ? null : _limparSelecao,
          ),
          Expanded(
            child: Text(
              quantos == 1 ? '1 selecionado' : '$quantos selecionados',
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: AppTheme.azulMedio,
              ),
            ),
          ),
          if (_excluindo)
            const Padding(
              padding: EdgeInsets.all(10),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                    strokeWidth: 2.2, color: AppTheme.error),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded,
                  color: AppTheme.error),
              tooltip: 'Excluir selecionados',
              onPressed: _excluirSelecionados,
            ),
        ],
      ),
    );
  }

  Widget _barraNormal() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        BarraSecao(
          titulo: _podeGerenciar ? 'Cursos' : 'Aprender',
          subtitulo: _podeGerenciar
              ? 'Conteúdo para os seus clientes'
              : 'Mini cursos de aquarismo',
          acao: _podeGerenciar
              ? ElevatedButton.icon(
                  onPressed: _abrirNovoCurso,
                  icon: const Icon(Icons.add_rounded, size: 18),
                  label: const Text('Novo'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(0, 40),
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    textStyle: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                )
              : null,
        ),
        // Segurar para selecionar não é descobrível sozinho; a linha
        // aparece só quando existe curso da loja para excluir.
        if (_podeGerenciar && _cursos.any(_podeExcluir)) ...[
          const SizedBox(height: 6),
          Row(
            children: const [
              Icon(Icons.touch_app_outlined, size: 14, color: AppTheme.textoFraco),
              SizedBox(width: 5),
              Text(
                'Segure um curso para selecionar e excluir',
                style: TextStyle(fontSize: 11.5, color: AppTheme.textoFraco),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildConteudo() {
    if (_carregando) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: CircularProgressIndicator(color: AppTheme.primaria)),
      );
    }

    if (_erro != null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.bordaCard),
        ),
        child: Column(
          children: [
            const Icon(Icons.cloud_off_rounded,
                size: 40, color: AppTheme.textoFraco),
            const SizedBox(height: 10),
            Text(
              _erro!,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13.5, color: AppTheme.textoFraco),
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: 170,
              child: ElevatedButton(
                onPressed: _carregar,
                style: ElevatedButton.styleFrom(minimumSize: const Size(0, 42)),
                child: const Text('Tentar de novo'),
              ),
            ),
          ],
        ),
      );
    }

    if (_cursos.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 40),
        child: Center(
          child: Column(
            children: [
              Icon(Icons.school_outlined,
                  size: 48, color: AppTheme.textoFraco.withValues(alpha: 0.45)),
              const SizedBox(height: 12),
              Text(
                _podeGerenciar
                    ? 'Nenhum curso ainda'
                    : 'Nenhum curso disponível',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _podeGerenciar
                    ? 'Use "Novo" para montar um curso com vídeos do YouTube'
                    : 'Sua loja ainda não publicou conteúdo',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13, color: AppTheme.textoFraco),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        for (final curso in _cursos) ...[
          _cardCurso(curso),
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  Widget _cardCurso(Map<String, dynamic> curso) {
    final total = curso['total_aulas'] ?? 0;
    final concluidas = curso['aulas_concluidas'] ?? 0;
    final percentual = (curso['percentual'] ?? 0) as int;
    final capa = curso['miniatura_url'] as String?;
    final marcado = _selecionados.contains(curso['id'].toString());

    return Material(
      color: marcado ? AppTheme.superficieAzul : AppTheme.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: () => _abrir(curso),
        onLongPress: _podeExcluir(curso) ? () => _alternar(curso) : null,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: marcado ? AppTheme.primaria : AppTheme.bordaCard,
              width: marcado ? 1.8 : 1,
            ),
            boxShadow: AppTheme.sombraCard,
          ),
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Capa: miniatura da primeira aula, vinda do YouTube.
              if (capa != null)
                AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Image.network(
                    capa,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => Container(
                      color: AppTheme.superficieAzul,
                      child: const Icon(Icons.play_circle_outline_rounded,
                          size: 40, color: AppTheme.primaria),
                    ),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            curso['titulo'] ?? '',
                            style: const TextStyle(
                              fontSize: 15.5,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.azulMedio,
                            ),
                          ),
                        ),
                        if (curso['curso_global'] == true) _selo('AquaSys'),
                        // Em seleção, a marca de conferido substitui o
                        // botão: com vários marcados, um ícone de lixeira
                        // por card sugeriria apagar só aquele.
                        if (_selecionando && _podeExcluir(curso))
                          Icon(
                            marcado
                                ? Icons.check_circle_rounded
                                : Icons.circle_outlined,
                            size: 21,
                            color: marcado
                                ? AppTheme.primaria
                                : AppTheme.bordaCard,
                          )
                        else if (_podeExcluir(curso))
                          // Excluir um curso sozinho, sem passar pela
                          // seleção — é o caminho mais curto e o mais
                          // comum.
                          SizedBox(
                            width: 32,
                            height: 32,
                            child: IconButton(
                              padding: EdgeInsets.zero,
                              iconSize: 19,
                              tooltip: 'Excluir curso',
                              icon: const Icon(Icons.delete_outline_rounded,
                                  color: AppTheme.textoFraco),
                              onPressed: () => _excluirUm(curso),
                            ),
                          ),
                      ],
                    ),
                    if ((curso['descricao'] ?? '').toString().isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        curso['descricao'],
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12.5,
                          color: Colors.black.withValues(alpha: 0.6),
                          height: 1.35,
                        ),
                      ),
                    ],
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        const Icon(Icons.play_circle_outline_rounded,
                            size: 16, color: AppTheme.textoFraco),
                        const SizedBox(width: 5),
                        Text(
                          '$total ${total == 1 ? "aula" : "aulas"}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.textoFraco,
                          ),
                        ),
                        if (!_podeGerenciar && total > 0) ...[
                          const SizedBox(width: 12),
                          Text(
                            '$concluidas concluída${concluidas == 1 ? "" : "s"}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppTheme.sucesso,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ],
                    ),
                    // Barra de progresso só faz sentido para quem assiste.
                    if (!_podeGerenciar && total > 0) ...[
                      const SizedBox(height: 10),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: percentual / 100,
                          minHeight: 6,
                          backgroundColor: AppTheme.superficieAzul,
                          valueColor: AlwaysStoppedAnimation(
                            percentual == 100
                                ? AppTheme.sucesso
                                : AppTheme.primaria,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _selo(String texto) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppTheme.primaria.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        texto,
        style: const TextStyle(
          fontSize: 10.5,
          fontWeight: FontWeight.w700,
          color: AppTheme.primaria,
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // NOVO CURSO (loja)
  // ═══════════════════════════════════════════════════
  void _abrirNovoCurso() {
    final chaveForm = GlobalKey<FormState>();
    final titulo = TextEditingController();
    final descricao = TextEditingController();

    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Novo curso',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: Form(
          key: chaveForm,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: titulo,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(
                  hintText: 'Ex: Ciclagem do aquário',
                ),
                validator: (v) => (v == null || v.trim().length < 2)
                    ? 'Informe o nome do curso'
                    : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: descricao,
                maxLines: 2,
                decoration: const InputDecoration(
                  hintText: 'Descrição (opcional)',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto),
            child: const Text('Cancelar',
                style: TextStyle(color: AppTheme.textoFraco)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(minimumSize: const Size(120, 44)),
            onPressed: () async {
              if (!chaveForm.currentState!.validate()) return;
              Navigator.pop(contexto);

              final resultado = await CursoService.criar(
                titulo: titulo.text.trim(),
                descricao: descricao.text.trim(),
              );
              if (!mounted) return;

              if (resultado['sucesso'] == true) {
                await _carregar();
                if (!mounted) return;
                // Curso novo nasce vazio — leva direto para adicionar vídeo.
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => TelaCursoDetalhe(
                      cursoId: resultado['dados']['id'],
                      podeEditar: true,
                    ),
                  ),
                ).then((_) => _carregar());
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(resultado['erro']),
                    backgroundColor: AppTheme.error,
                    behavior: SnackBarBehavior.floating,
                  ),
                );
              }
            },
            child: const Text('Criar'),
          ),
        ],
      ),
    );
  }
}
