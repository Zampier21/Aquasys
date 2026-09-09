import 'package:flutter/material.dart';
import 'package:youtube_player_iframe/youtube_player_iframe.dart';
import '../Tema/app_tema.dart';
import '../Services/curso_service.dart';

class TelaCursoDetalhe extends StatefulWidget {
  final String cursoId;

  final bool podeEditar;

  const TelaCursoDetalhe({
    super.key,
    required this.cursoId,
    this.podeEditar = false,
  });

  @override
  State<TelaCursoDetalhe> createState() => _TelaCursoDetalheState();
}

class _TelaCursoDetalheState extends State<TelaCursoDetalhe> {
  YoutubePlayerController? _player;
  Map<String, dynamic>? _curso;
  Map<String, dynamic>? _aulaAtual;
  bool _carregando = true;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  @override
  void dispose() {
    _player?.close();
    super.dispose();
  }

  List<Map<String, dynamic>> get _aulas =>
      List<Map<String, dynamic>>.from(_curso?['aulas'] ?? const []);

  Future<void> _carregar({bool manterAula = true}) async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    final resultado = await CursoService.detalhar(widget.cursoId);
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (resultado['sucesso'] == true) {
        _curso = resultado['dados'] as Map<String, dynamic>;
      } else {
        _erro = resultado['erro'];
      }
    });

    if (_curso == null) return;

    final aulas = _aulas;
    if (aulas.isEmpty) {
      setState(() => _aulaAtual = null);
      return;
    }

    final id = manterAula ? (_aulaAtual?['id']) : null;
    final escolhida = aulas.firstWhere(
      (a) => a['id'] == id,
      orElse: () => aulas.first,
    );

    if (escolhida['id'] != _aulaAtual?['id']) {
      _tocar(escolhida);
    } else {
      setState(() => _aulaAtual = escolhida);
    }
  }

  void _tocar(Map<String, dynamic> aula) {
    final videoId = aula['youtube_id'] as String;

    if (_player == null) {
      _player = YoutubePlayerController.fromVideoId(
        videoId: videoId,
        params: const YoutubePlayerParams(
          showFullscreenButton: true,
          strictRelatedVideos: true,
        ),
      );
    } else {
      _player!.loadVideoById(videoId: videoId);
    }

    setState(() => _aulaAtual = aula);
  }

  Future<void> _alternarConcluida(Map<String, dynamic> aula) async {
    final novo = !(aula['concluida'] == true);

    setState(() => aula['concluida'] = novo);

    final resultado =
        await CursoService.marcarAula(aula['id'], concluida: novo);
    if (!mounted) return;

    if (resultado['sucesso'] != true) {
      setState(() => aula['concluida'] = !novo);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(resultado['erro']),
          backgroundColor: AppTheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  int get _concluidas =>
      _aulas.where((a) => a['concluida'] == true).length;

  @override
  Widget build(BuildContext context) {
    if (_carregando && _curso == null) {
      return const Scaffold(
        backgroundColor: AppTheme.backgroundApp,
        body: Center(child: CircularProgressIndicator(color: AppTheme.primaria)),
      );
    }

    if (_erro != null && _curso == null) {
      return Scaffold(
        backgroundColor: AppTheme.backgroundApp,
        appBar: _appBar(),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.cloud_off_rounded,
                    size: 48, color: AppTheme.textoFraco),
                const SizedBox(height: 12),
                Text(
                  _erro!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontSize: 14, color: AppTheme.textoFraco),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: 170,
                  child: ElevatedButton(
                    onPressed: _carregar,
                    child: const Text('Tentar de novo'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (_player == null) {
      return Scaffold(
        backgroundColor: AppTheme.backgroundApp,
        appBar: _appBar(),
        body: _corpo(),
      );
    }

    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      appBar: _appBar(),
      body: Column(
        children: [
          Container(
            color: Colors.black,
            child: YoutubePlayer(controller: _player!, aspectRatio: 16 / 9),
          ),
          Expanded(child: _corpo()),
        ],
      ),
    );
  }

  PreferredSizeWidget _appBar() {
    return AppBar(
      backgroundColor: AppTheme.backgroundApp,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      iconTheme: const IconThemeData(color: AppTheme.azulMedio),
      title: Text(
        _curso?['titulo'] ?? 'Curso',
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: AppTheme.azulMedio,
        ),
      ),
      actions: [
        if (widget.podeEditar) ...[
          IconButton(
            icon: const Icon(Icons.playlist_add_rounded),
            tooltip: 'Importar playlist',
            onPressed: _abrirImportarPlaylist,
          ),
          IconButton(
            icon: const Icon(Icons.add_rounded),
            tooltip: 'Adicionar vídeo',
            onPressed: _abrirAdicionarAula,
          ),
        ],
      ],
    );
  }

  Widget _corpo() {
    final aulas = _aulas;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      children: [
        if (_aulaAtual != null) ...[
          Text(
            _aulaAtual!['titulo'] ?? '',
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: AppTheme.azulEscuro,
              height: 1.3,
            ),
          ),
          if ((_aulaAtual!['canal'] ?? '').toString().isNotEmpty) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.person_outline_rounded,
                    size: 14, color: AppTheme.textoFraco),
                const SizedBox(width: 4),
                Text(
                  _aulaAtual!['canal'],
                  style: const TextStyle(
                      fontSize: 12.5, color: AppTheme.textoFraco),
                ),
              ],
            ),
          ],
          const SizedBox(height: 14),
          if (!widget.podeEditar) _botaoConcluir(_aulaAtual!),
          const SizedBox(height: 8),
          const Divider(color: AppTheme.bordaCard),
          const SizedBox(height: 8),
        ],

        if ((_curso?['descricao'] ?? '').toString().isNotEmpty &&
            _aulaAtual == null) ...[
          Text(
            _curso!['descricao'],
            style: TextStyle(
              fontSize: 13.5,
              color: Colors.black.withValues(alpha: 0.65),
              height: 1.4,
            ),
          ),
          const SizedBox(height: 18),
        ],

        Row(
          children: [
            Text(
              aulas.isEmpty
                  ? 'Aulas'
                  : 'Aulas (${aulas.length})',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppTheme.azulMedio,
              ),
            ),
            const Spacer(),
            if (!widget.podeEditar && aulas.isNotEmpty)
              Text(
                '$_concluidas de ${aulas.length} concluídas',
                style: const TextStyle(
                    fontSize: 12, color: AppTheme.textoFraco),
              ),
          ],
        ),
        const SizedBox(height: 10),

        if (aulas.isEmpty)
          _vazio()
        else
          for (final aula in aulas) _linhaAula(aula),
      ],
    );
  }

  Widget _vazio() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Column(
        children: [
          Icon(Icons.video_library_outlined,
              size: 44, color: AppTheme.textoFraco.withValues(alpha: 0.45)),
          const SizedBox(height: 12),
          Text(
            widget.podeEditar
                ? 'Nenhum vídeo neste curso'
                : 'Este curso ainda não tem aulas',
            style: const TextStyle(
              fontSize: 14.5,
              fontWeight: FontWeight.w700,
              color: AppTheme.azulMedio,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            widget.podeEditar
                ? 'Toque em + e cole o link de um vídeo do YouTube'
                : 'Volte mais tarde',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12.5, color: AppTheme.textoFraco),
          ),
        ],
      ),
    );
  }

  Widget _botaoConcluir(Map<String, dynamic> aula) {
    final concluida = aula['concluida'] == true;

    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () => _alternarConcluida(aula),
        icon: Icon(
          concluida
              ? Icons.check_circle_rounded
              : Icons.check_circle_outline_rounded,
          size: 19,
          color: concluida ? AppTheme.sucesso : AppTheme.primaria,
        ),
        label: Text(concluida ? 'Aula concluída' : 'Marcar como concluída'),
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(double.infinity, 46),
          foregroundColor: concluida ? AppTheme.sucesso : AppTheme.primaria,
          side: BorderSide(
            color: concluida ? AppTheme.sucessoBorda : AppTheme.bordaCampo,
          ),
          backgroundColor:
              concluida ? AppTheme.sucessoFundo : AppTheme.backgroundLabel,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  Widget _linhaAula(Map<String, dynamic> aula) {
    final tocando = aula['id'] == _aulaAtual?['id'];
    final concluida = aula['concluida'] == true;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: tocando ? AppTheme.superficieAzul : AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: tocando ? AppTheme.primaria : AppTheme.bordaCard,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _tocar(aula),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: SizedBox(
                    width: 72,
                    height: 44,
                    child: aula['miniatura_url'] != null
                        ? Image.network(
                            aula['miniatura_url'],
                            fit: BoxFit.cover,
                            errorBuilder: (_, _, _) => Container(
                              color: AppTheme.superficieAzul,
                              child: const Icon(Icons.play_arrow_rounded,
                                  color: AppTheme.primaria, size: 20),
                            ),
                          )
                        : Container(
                            color: AppTheme.superficieAzul,
                            child: const Icon(Icons.play_arrow_rounded,
                                color: AppTheme.primaria, size: 20),
                          ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        aula['titulo'] ?? '',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight:
                              tocando ? FontWeight.w700 : FontWeight.w500,
                          color: AppTheme.azulEscuro,
                          height: 1.3,
                        ),
                      ),
                      if (concluida) ...[
                        const SizedBox(height: 3),
                        const Row(
                          children: [
                            Icon(Icons.check_circle_rounded,
                                size: 13, color: AppTheme.sucesso),
                            SizedBox(width: 4),
                            Text(
                              'Concluída',
                              style: TextStyle(
                                fontSize: 11,
                                color: AppTheme.sucesso,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                if (widget.podeEditar)
                  IconButton(
                    icon: const Icon(Icons.delete_outline_rounded,
                        size: 19, color: AppTheme.error),
                    onPressed: () => _confirmarRemocao(aula),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ADICIONAR VÍDEO (loja)
  // ═══════════════════════════════════════════════════
  void _abrirAdicionarAula() => _abrirDialogoLink(
        titulo: 'Adicionar vídeo',
        ajuda: 'Cole o link do YouTube. O título, o canal e a capa vêm '
            'automaticamente.',
        exemplo: 'https://www.youtube.com/watch?v=...',
        botao: 'Adicionar',
        enviar: (url) => CursoService.adicionarAula(
          cursoId: widget.cursoId,
          url: url,
        ),
      );

  void _abrirImportarPlaylist() => _abrirDialogoLink(
        titulo: 'Importar playlist',
        ajuda: 'Cole o link de uma playlist (o endereço que tem "list=") e '
            'todos os vídeos dela entram de uma vez, na ordem. Vídeo que já '
            'está no curso é ignorado.',
        exemplo: 'https://www.youtube.com/watch?v=...&list=PL...',
        botao: 'Importar',
        enviar: (url) => CursoService.importarPlaylist(
          cursoId: widget.cursoId,
          url: url,
        ),
      );

  void _abrirDialogoLink({
    required String titulo,
    required String ajuda,
    required String exemplo,
    required String botao,
    required Future<Map<String, dynamic>> Function(String url) enviar,
  }) {
    final chaveForm = GlobalKey<FormState>();
    final url = TextEditingController();
    var salvando = false;

    showDialog(
      context: context,
      builder: (contexto) => StatefulBuilder(
        builder: (contexto, refazer) => AlertDialog(
          backgroundColor: AppTheme.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text(
            titulo,
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w700,
              color: AppTheme.azulMedio,
            ),
          ),
          content: Form(
            key: chaveForm,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  ajuda,
                  style: const TextStyle(
                      fontSize: 12.5, color: AppTheme.textoFraco),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: url,
                  autofocus: true,
                  decoration: InputDecoration(hintText: exemplo),
                  validator: (v) => (v == null || v.trim().length < 5)
                      ? 'Cole o link'
                      : null,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: salvando ? null : () => Navigator.pop(contexto),
              child: const Text('Cancelar',
                  style: TextStyle(color: AppTheme.textoFraco)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(minimumSize: const Size(120, 44)),
              onPressed: salvando
                  ? null
                  : () async {
                      if (!chaveForm.currentState!.validate()) return;
                      refazer(() => salvando = true);

                      final resultado = await enviar(url.text.trim());
                      if (!contexto.mounted) return;

                      if (resultado['sucesso'] == true) {
                        Navigator.pop(contexto);
                        _carregar();
                      } else {
                        refazer(() => salvando = false);
                        ScaffoldMessenger.of(contexto).showSnackBar(
                          SnackBar(
                            content: Text(resultado['erro']),
                            backgroundColor: AppTheme.error,
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      }
                    },
              child: salvando
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                        color: AppTheme.white,
                        strokeWidth: 2,
                      ),
                    )
                  : Text(botao),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmarRemocao(Map<String, dynamic> aula) {
    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Remover vídeo',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: Text(
          '"${aula['titulo']}" sai deste curso. O vídeo continua no YouTube.',
          style: TextStyle(fontSize: 14, color: Colors.black.withValues(alpha: 0.65)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto),
            child: const Text('Cancelar',
                style: TextStyle(color: AppTheme.textoFraco)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.error,
              minimumSize: const Size(120, 44),
            ),
            onPressed: () async {
              Navigator.pop(contexto);
              final resultado = await CursoService.removerAula(
                cursoId: widget.cursoId,
                aulaId: aula['id'],
              );
              if (!mounted) return;

              if (resultado['sucesso'] == true) {
                _carregar(manterAula: false);
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
            child: const Text('Remover'),
          ),
        ],
      ),
    );
  }
}
