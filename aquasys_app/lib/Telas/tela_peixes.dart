import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import '../Tema/app_tema.dart';
import 'tela_importar_peixes.dart';
import 'tela_revisar_especies.dart';
import '../widgets/bottom_nav.dart';
import '../widgets/cabecalho_usuario.dart';
import '../widgets/foto_especie.dart';
import '../Services/api.dart';
import '../Services/aquario_service.dart';
import '../Services/peixe_service.dart';
import 'tela_inicial.dart';
import 'tela_aquarios.dart';
import 'tela_clientes.dart';

// ═══════════════════════════════════════════════════════════
// TELA DE PEIXES — conectada à API
// ═══════════════════════════════════════════════════════════
class TelaPeixes extends StatefulWidget {
  final String tipoUsuario;
  const TelaPeixes({super.key, required this.tipoUsuario});

  @override
  State<TelaPeixes> createState() => _TelaPeixesState();
}

class _TelaPeixesState extends State<TelaPeixes> {

  // Paleta usada para dar identidade visual a cada espécie
  static const List<Color> _paleta = [
    Color(0xFF2E86C1), Color(0xFFC0392B), Color(0xFF566573),
    Color(0xFFCA6F1E), Color(0xFFD4AC0D), Color(0xFF7B5CD6),
    Color(0xFF00A878), Color(0xFFD6337F),
  ];

  final _buscaCtrl = TextEditingController();
  String _busca = '';

  List<Map<String, dynamic>> _aquarios = [];
  Map<String, dynamic>? _aquarioSelecionado;

  List<Map<String, dynamic>> _especies = [];
  Map<String, Map<String, dynamic>> _compat = {};
  List<Map<String, dynamic>> _habitantes = [];

  final Set<String> _abertos = {};

  /// Variedade escolhida em cada card, pelo id da base. Ausente = a
  /// própria base. É o que o card mostra e o que o botão adiciona.
  final Map<String, String> _variedadeEscolhida = {};
  bool _carregando = true;
  bool _habitantesAbertos = true;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _carregarTudo();
  }

  @override
  void dispose() {
    _buscaCtrl.dispose();
    super.dispose();
  }

  /// Quantas fichas da loja estão à espera de revisão.
  ///
  /// Serve ao selo sobre o ícone de revisar: sem ele, a loja só
  /// descobriria que há ficha incompleta entrando na tela, e depois de
  /// uma importação é justamente quando há.
  int _aRevisar = 0;

  // ─── Carregamento ───────────────────────────────────────
  Future<void> _carregarTudo() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    // O try/finally existe porque um erro no meio do caminho já deixou
    // esta tela presa no "carregando" para sempre: sem ele, a linha que
    // desliga o spinner nunca era alcançada e o usuário via só o aviso
    // de "cadastre um aquário", mesmo tendo aquários.
    try {
      final respAquarios = await AquarioService.listar();
      final respEspecies = await PeixeService.listarEspecies(busca: _busca);
      if (!mounted) return;

      if (respAquarios['sucesso'] != true) {
        _erro = respAquarios['erro'];
        return;
      }

      _aquarios = Api.lista(respAquarios);
      _aquarioSelecionado ??= _aquarios.isNotEmpty ? _aquarios.first : null;

      if (respEspecies['sucesso'] == true) {
        _especies = Api.lista(respEspecies);
        _escolherPelaBusca();
      } else {
        _erro = respEspecies['erro'];
      }

      await _carregarDadosDoAquario();
      await _contarARevisar();
    } catch (e) {
      _erro = 'Não foi possível carregar os peixes.';
      debugPrint('tela_peixes: falha ao carregar — $e');
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  /// Conta as fichas incompletas, só na conta da loja.
  ///
  /// Falha de rede aqui não é erro de tela: o selo some e o resto do
  /// catálogo continua funcionando. Avisar sobre um contador seria pior
  /// do que não mostrá-lo.
  Future<void> _contarARevisar() async {
    if (widget.tipoUsuario != 'dono') return;

    final r = await PeixeService.incompletas();
    if (!mounted) return;

    _aRevisar = r['sucesso'] == true ? (r['dados'] as List).length : 0;
  }

  /// Recarrega o que depende do aquário selecionado: selos e habitantes.
  Future<void> _carregarDadosDoAquario() async {
    if (_aquarioSelecionado == null) {
      _compat = {};
      _habitantes = [];
      return;
    }

    final id = _aquarioSelecionado!['id'].toString();
    final respCompat = await PeixeService.compatibilidades(id);
    final respHab = await PeixeService.habitantes(id);
    if (!mounted) return;

    if (respCompat['sucesso'] == true) {
      _compat = Map<String, Map<String, dynamic>>.from(respCompat['dados']);
    }
    if (respHab['sucesso'] == true) {
      _habitantes = Api.lista(respHab);
    }
  }

  Future<void> _trocarAquario(Map<String, dynamic> aq) async {
    setState(() {
      _aquarioSelecionado = aq;
      _carregando = true;
    });
    await _carregarDadosDoAquario();
    if (mounted) setState(() => _carregando = false);
  }

  Future<void> _buscar(String termo) async {
    setState(() => _busca = termo);
    final resp = await PeixeService.listarEspecies(busca: termo);
    if (!mounted) return;
    if (resp['sucesso'] == true) {
      setState(() => _especies = Api.lista(resp));
    }
  }

  void _aviso(String mensagem, {bool erro = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(mensagem),
        backgroundColor: erro ? AppTheme.error : AppTheme.ctaEntrar,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  // ─── Auxiliares ─────────────────────────────────────────
  String _n(dynamic v) {
    if (v == null) return '?';
    final d = (v as num).toDouble();
    return d == d.roundToDouble() ? d.toStringAsFixed(0) : d.toString();
  }

  Color _corEspecie(Map<String, dynamic> e) {
    final nome = e['nome_comum']?.toString() ?? '';
    return _paleta[nome.hashCode.abs() % _paleta.length];
  }

  String _decisaoDe(Map<String, dynamic> especie) {
    final id = especie['id'].toString();
    return _compat[id]?['decisao']?.toString() ?? 'liberado';
  }

  List<String> _avisosDe(Map<String, dynamic> especie) {
    final id = especie['id'].toString();
    final lista = _compat[id]?['avisos'];
    return lista == null ? [] : List<String>.from(lista);
  }

  bool _jaEstaNoAquario(String especieId) =>
      _habitantes.any((h) => h['especie_id'].toString() == especieId);

  // ─── Variedades ─────────────────────────────────────────
  List<Map<String, dynamic>> _variedadesDe(Map<String, dynamic> e) =>
      List<Map<String, dynamic>>.from(e['variedades'] ?? const []);

  /// Se a base ou qualquer variedade dela já vive no aquário.
  ///
  /// É o que acende o check do cabeçalho: um Halfmoon no aquário é um
  /// Betta no aquário. O botão, por outro lado, olha só a variedade
  /// escolhida — ter um Halfmoon não impede de escolher o Plakat; quem
  /// decide se ele cabe é a análise do servidor.
  bool _familiaNoAquario(Map<String, dynamic> e) =>
      _jaEstaNoAquario(e['id'].toString()) ||
      _variedadesDe(e).any((v) => _jaEstaNoAquario(v['id'].toString()));

  /// O que o card está mostrando: a base, ou a variedade escolhida.
  ///
  /// A variedade chega da API só com identidade e foto; a biologia é a da
  /// base, e por isso ela entra por baixo. Uma variedade que declare
  /// biologia própria — o albino mais sensível, com pH máximo menor —
  /// apareceria aqui com os números da base. A decisão de compatibilidade
  /// não depende disto: o diálogo de adicionar reanalisa pelo id da
  /// variedade, e é o servidor quem responde.
  Map<String, dynamic> _emExibicao(Map<String, dynamic> e) {
    final escolhida = _variedadeEscolhida[e['id'].toString()];
    if (escolhida == null) return e;
    final v = _variedadesDe(e).firstWhere(
      (v) => v['id'].toString() == escolhida,
      orElse: () => const <String, dynamic>{},
    );
    if (v.isEmpty) return e;
    return {
      ...e,
      'id': v['id'],
      'nome_comum': v['nome_comum'],
      'imagem': v['imagem'],
      'imagem_miniatura': v['imagem_miniatura'],
      'imagem_credito': v['imagem_credito'],
      'nome_variedade': v['nome_curto'],
    };
  }

  static const _acentos = {
    'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
    'é': 'e', 'ê': 'e', 'è': 'e', 'ë': 'e',
    'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
    'ó': 'o', 'ô': 'o', 'õ': 'o', 'ò': 'o', 'ö': 'o',
    'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u', 'ç': 'c',
  };

  String _semAcento(String texto) => texto
      .toLowerCase()
      .split('')
      .map((c) => _acentos[c] ?? c)
      .join();

  /// Quem buscou "marmorato" quer ver o Marmorato, e não o card fechado
  /// do Acará Bandeira. A API devolve a base; aqui o card já abre com a
  /// variedade procurada escolhida.
  void _escolherPelaBusca() {
    final termo = _semAcento(_busca.trim());
    if (termo.isEmpty) return;
    for (final e in _especies) {
      final base = e['id'].toString();
      for (final v in _variedadesDe(e)) {
        if (_semAcento(v['nome_comum']?.toString() ?? '').contains(termo)) {
          _variedadeEscolhida[base] = v['id'].toString();
          _abertos.add(base);
          break;
        }
      }
    }
  }

  void _onNavTap(int index) {
    if (index == 2) return;
    final t = widget.tipoUsuario;
    final destino = switch (index) {
      0 => TelaInicial(tipoUsuario: t),
      1 => TelaAquarios(tipoUsuario: t),
      _ => TelaClientes(tipoUsuario: t),
    };
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => destino));
  }

  // ─── Adicionar espécie ──────────────────────────────────
  void _abrirModalAdicionar(Map<String, dynamic> especie) {
    if (_aquarioSelecionado == null) return;

    showDialog(
      context: context,
      builder: (_) => _DialogAdicionar(
        especie: especie,
        aquario: _aquarioSelecionado!,
        cor: _corEspecie(especie),
        onConcluido: (mensagem) async {
          _aviso(mensagem);
          setState(() => _carregando = true);
          await _carregarDadosDoAquario();
          if (mounted) setState(() => _carregando = false);
        },
      ),
    );
  }

  // ─── Remover habitante ──────────────────────────────────
  Future<void> _removerHabitante(Map<String, dynamic> h) async {
    final resp = await PeixeService.remover(
      aquarioId: _aquarioSelecionado!['id'].toString(),
      itemId: h['id'].toString(),
    );

    if (resp['sucesso'] == true) {
      _aviso('${h['nome_comum']} removido do aquário');
      setState(() => _carregando = true);
      await _carregarDadosDoAquario();
      if (mounted) setState(() => _carregando = false);
    } else {
      _aviso(resp['erro'] ?? 'Erro ao remover', erro: true);
    }
  }

  // ═══════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: CabecalhoUsuario(tipoUsuario: widget.tipoUsuario),
            ),
            _buildBusca(),
            _buildFiltroAquarios(),
            if (_aquarioSelecionado != null) _buildParametrosAtuais(),
            const SizedBox(height: 8),
            Expanded(child: _buildConteudo()),
          ],
        ),
      ),
      bottomNavigationBar: BottomNav(
        currentIndex: 2,
        onTap: _onNavTap,
        isDono: widget.tipoUsuario == 'dono',
      ),
    );
  }

  Widget _buildBusca() {
    final campo = TextField(
      controller: _buscaCtrl,
      onChanged: _buscar,
      style: const TextStyle(fontSize: 14, color: AppTheme.textDark),
      decoration: InputDecoration(
        hintText: 'Buscar peixe...',
        prefixIcon: const Icon(Icons.search_rounded, color: AppTheme.hintCampo, size: 21),
        suffixIcon: _busca.isEmpty
            ? null
            : IconButton(
                icon: const Icon(Icons.close_rounded, size: 18, color: AppTheme.hintCampo),
                onPressed: () {
                  _buscaCtrl.clear();
                  _buscar('');
                },
              ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );

    // Conferir a lista de estoque é tarefa de quem vende, não de quem
    // tem o aquário: o botão só existe na conta da loja.
    if (widget.tipoUsuario != 'dono') {
      return Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
        child: campo,
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
      child: Row(
        children: [
          Expanded(child: campo),
          const SizedBox(width: 10),
          _acaoDaLoja(
            icone: Icons.upload_file_rounded,
            dica: 'Importar lista de estoque',
            destino: const TelaImportarPeixes(),
          ),
          const SizedBox(width: 8),
          // A revisão vem ao lado da importação porque é o passo
          // seguinte: a lista entra, e o que ficou incompleto é
          // preenchido aqui.
          _acaoDaLoja(
            icone: Icons.fact_check_outlined,
            dica: _aRevisar == 0
                ? 'Revisar fichas incompletas'
                : '$_aRevisar ${_aRevisar == 1 ? "ficha" : "fichas"} '
                    'a revisar',
            destino: const TelaRevisarEspecies(),
            contador: _aRevisar,
          ),
        ],
      ),
    );
  }

  /// Botão de ação que só existe na conta da loja.
  Widget _acaoDaLoja({
    required IconData icone,
    required String dica,
    required Widget destino,
    int contador = 0,
  }) {
    final botao = Material(
      color: AppTheme.superficieSuave,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => destino),
          );
          // A revisão muda a ficha das espécies, e o catálogo desta
          // tela já está em memória. Sem recarregar, o card continuaria
          // mostrando os campos vazios.
          if (mounted) _carregarTudo();
        },
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Icon(icone, size: 22, color: AppTheme.primaria),
        ),
      ),
    );

    if (contador == 0) return Tooltip(message: dica, child: botao);

    return Tooltip(
      message: dica,
      // `clipBehavior: none` deixa o selo passar da borda do botão. Sem
      // isso o Stack recorta o pedaço que sai para fora.
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          botao,
          Positioned(
            top: -3,
            right: -3,
            child: Container(
              constraints: const BoxConstraints(minWidth: 19),
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
              decoration: BoxDecoration(
                color: AppTheme.alerta,
                borderRadius: BorderRadius.circular(20),
                // A borda da cor do fundo separa o selo do ícone, senão
                // os dois se encostam e viram um borrão.
                border: Border.all(color: AppTheme.backgroundApp, width: 1.6),
              ),
              child: Text(
                // Acima de 99 o número não caberia, e a diferença entre
                // 100 e 300 fichas pendentes não muda o que fazer.
                contador > 99 ? '99+' : '$contador',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.white,
                  height: 1.1,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFiltroAquarios() {
    if (_aquarios.isEmpty) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: const Color(0xFFFFF9EC),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFFCE4B0)),
          ),
          child: const Row(
            children: [
              Icon(Icons.info_outline_rounded, size: 17, color: Color(0xFFD97706)),
              SizedBox(width: 9),
              Expanded(
                child: Text(
                  'Cadastre um aquário para ver a compatibilidade das espécies',
                  style: TextStyle(fontSize: 12.5, color: Color(0xFF92400E)),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return SizedBox(
      height: 62,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
        itemCount: _aquarios.length,
        itemBuilder: (_, i) {
          final aq = _aquarios[i];
          final ativo = _aquarioSelecionado?['id'] == aq['id'];
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: () => _trocarAquario(aq),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: ativo ? AppTheme.ctaEntrar : AppTheme.white,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: ativo ? AppTheme.ctaEntrar : AppTheme.bordaCard,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        ativo ? Icons.check_circle_rounded : Icons.water_drop_outlined,
                        size: 16,
                        color: ativo ? Colors.white : AppTheme.hintCampo,
                      ),
                      const SizedBox(width: 7),
                      Text(
                        aq['nome']?.toString() ?? '—',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: ativo ? Colors.white : AppTheme.tituloBemVindo,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildParametrosAtuais() {
    final aq = _aquarioSelecionado!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          color: AppTheme.superficieAzul,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            const Icon(Icons.tune_rounded, size: 16, color: AppTheme.primaria),
            const SizedBox(width: 9),
            const Text(
              'Seus parâmetros:',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTheme.azulMedio,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'pH ${_n(aq['ph'])}   ·   ${_n(aq['temperatura'])} °C   ·   ${_n(aq['volume_litros'])}L',
                style: const TextStyle(fontSize: 12, color: AppTheme.azulMedio),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  Widget _buildConteudo() {
    if (_carregando) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.ctaEntrar));
    }

    if (_erro != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_off_rounded, size: 52, color: AppTheme.hintCampo),
              const SizedBox(height: 14),
              Text(
                _erro!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: AppTheme.hintCampo),
              ),
              const SizedBox(height: 18),
              ElevatedButton.icon(
                onPressed: _carregarTudo,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Tentar novamente'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(0, 44),
                  padding: const EdgeInsets.symmetric(horizontal: 22),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _carregarTudo,
      color: AppTheme.ctaEntrar,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
        children: [
          if (_habitantes.isNotEmpty) ...[
            _buildSecaoHabitantes(),
            const SizedBox(height: 20),
          ],
          _buildTituloCatalogo(),
          const SizedBox(height: 12),
          if (_especies.isEmpty)
            _buildVazioBusca()
          else
            ..._especies.map(_buildCardEspecie),
        ],
      ),
    );
  }

  Widget _buildVazioBusca() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40),
      child: Column(
        children: [
          Icon(Icons.search_off_rounded, size: 52, color: AppTheme.hintCampo.withValues(alpha: 0.4)),
          const SizedBox(height: 12),
          const Text(
            'Nenhuma espécie encontrada',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: AppTheme.tituloBemVindo,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Tente buscar por outro nome',
            style: TextStyle(fontSize: 13, color: AppTheme.hintCampo.withValues(alpha: 0.9)),
          ),
        ],
      ),
    );
  }

  Widget _buildTituloCatalogo() {
    return Row(
      children: [
        const Icon(Icons.menu_book_rounded, size: 17, color: AppTheme.ctaEntrar),
        const SizedBox(width: 8),
        const Text(
          'Catálogo de espécies',
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w800,
            color: AppTheme.tituloBemVindo,
          ),
        ),
        const Spacer(),
        Text(
          '${_especies.length} espécies',
          style: const TextStyle(fontSize: 12, color: AppTheme.hintCampo),
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════
  // HABITANTES DO AQUÁRIO
  // ═══════════════════════════════════════════════════
  Widget _buildSecaoHabitantes() {
    final totalPeixes = _habitantes.fold<int>(
      0,
      (soma, h) => soma + (h['quantidade'] as int? ?? 0),
    );

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.bordaCard),
        boxShadow: AppTheme.sombraCard,
      ),
      child: Column(
        children: [
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
              onTap: () => setState(() => _habitantesAbertos = !_habitantesAbertos),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                decoration: BoxDecoration(
                  color: const Color(0xFFF4FAFE),
                  borderRadius: BorderRadius.vertical(
                    top: const Radius.circular(15),
                    bottom: Radius.circular(_habitantesAbertos ? 0 : 15),
                  ),
                  border: _habitantesAbertos
                      ? const Border(bottom: BorderSide(color: AppTheme.bordaCard))
                      : null,
                ),
                child: Row(
                  children: [
                    Container(
                      width: 30,
                      height: 30,
                      decoration: BoxDecoration(
                        color: const Color(0xFF00A878).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(9),
                      ),
                      child: const Center(
                        child: FaIcon(FontAwesomeIcons.fish, size: 14, color: Color(0xFF00A878)),
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'No aquário',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.tituloBemVindo,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFF00A878).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '$totalPeixes peixes',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF00694A),
                        ),
                      ),
                    ),
                    const Spacer(),
                    AnimatedRotation(
                      turns: _habitantesAbertos ? 0.5 : 0,
                      duration: const Duration(milliseconds: 200),
                      child: Icon(
                        Icons.keyboard_arrow_down_rounded,
                        color: AppTheme.hintCampo.withValues(alpha: 0.7),
                        size: 22,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (_habitantesAbertos)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Column(
                children: List.generate(_habitantes.length, (i) {
                  final h = _habitantes[i];
                  return Column(
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 11),
                        child: Row(
                          children: [
                            FotoEspecie(
                              caminho: h['imagem_miniatura']?.toString(),
                              cor: _corEspecie(h),
                              tamanho: 34,
                              circular: false,
                              proporcaoIcone: 0.41,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    h['nome_comum']?.toString() ?? '—',
                                    style: const TextStyle(
                                      fontSize: 13.5,
                                      fontWeight: FontWeight.w700,
                                      color: AppTheme.tituloBemVindo,
                                    ),
                                  ),
                                  Text(
                                    '${h['quantidade']} indivíduo${h['quantidade'] == 1 ? "" : "s"}',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: AppTheme.hintCampo,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () => _removerHabitante(h),
                                borderRadius: BorderRadius.circular(8),
                                child: const Padding(
                                  padding: EdgeInsets.all(6),
                                  child: Icon(
                                    Icons.delete_outline_rounded,
                                    color: AppTheme.error,
                                    size: 19,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (i < _habitantes.length - 1)
                        Divider(
                          height: 1,
                          color: AppTheme.bordaCard.withValues(alpha: 0.7),
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
  // CARD DA ESPÉCIE
  // ═══════════════════════════════════════════════════
  Widget _buildCardEspecie(Map<String, dynamic> e) {
    final id = e['id'].toString();
    final expandido = _abertos.contains(id);
    final decisao = _decisaoDe(e);
    final avisos = _avisosDe(e);
    final cor = _corEspecie(e);
    final exibida = _emExibicao(e);
    final jaTem = _familiaNoAquario(e);
    final variedades = _variedadesDe(e);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        // Fechado o card é a linha azul-clara da lista; aberto, branco.
        color: expandido ? AppTheme.white : AppTheme.superficieAzul,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: expandido ? _corBorda(decisao) : Colors.transparent,
        ),
      ),
      child: Column(
        children: [
          Material(
            color: AppTheme.superficieAzul,
            child: InkWell(
              onTap: () => setState(() {
                expandido ? _abertos.remove(id) : _abertos.add(id);
              }),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                child: Row(
                  children: [
                    FotoEspecie(
                      caminho: e['imagem_miniatura']?.toString(),
                      cor: cor,
                      tamanho: 42,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Flexible(
                                child: Text(
                                  e['nome_comum']?.toString() ?? '—',
                                  style: const TextStyle(
                                    fontSize: 15.5,
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.tituloBemVindo,
                                  ),
                                ),
                              ),
                              if (jaTem) ...[
                                const SizedBox(width: 6),
                                const Icon(
                                  Icons.check_circle_rounded,
                                  size: 15,
                                  color: Color(0xFF00A878),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text(
                            e['nome_cientifico']?.toString() ?? '',
                            style: TextStyle(
                              fontSize: 12,
                              fontStyle: FontStyle.italic,
                              color: AppTheme.hintCampo.withValues(alpha: 0.95),
                            ),
                          ),
                          // Sem este aviso ninguém saberia que há variedades
                          // até abrir o card por acaso.
                          if (variedades.isNotEmpty) ...[
                            const SizedBox(height: 3),
                            Text(
                              variedades.length == 1
                                  ? '+ 1 variedade'
                                  : '+ ${variedades.length} variedades',
                              style: const TextStyle(
                                fontSize: 11.5,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.ctaEntrar,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (_aquarioSelecionado != null) _selo(decisao),
                    const SizedBox(width: 6),
                    AnimatedRotation(
                      turns: expandido ? 0.5 : 0,
                      duration: const Duration(milliseconds: 200),
                      child: Icon(
                        Icons.keyboard_arrow_down_rounded,
                        color: AppTheme.hintCampo.withValues(alpha: 0.7),
                        size: 22,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          if (expandido) ...[
            const Divider(height: 1, color: AppTheme.bordaCard),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Com foto no catálogo, o banner vira a foto de verdade;
                  // sem ela, continua o degradê com o ícone, que é melhor
                  // do que um buraco no meio do card.
                  // A foto é a da variedade escolhida. Se ela não tiver
                  // foto, fica o degradê — e não a foto da base: um acará
                  // prateado com o nome "Leopardo Azul" embaixo engana quem
                  // está justamente escolhendo pela aparência.
                  if (exibida['imagem'] != null)
                    FotoEspecieGrande(
                      caminho: exibida['imagem']?.toString(),
                      credito: exibida['imagem_credito']?.toString(),
                    )
                  else
                    Container(
                      height: 96,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            cor.withValues(alpha: 0.16),
                            cor.withValues(alpha: 0.05),
                          ],
                        ),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            FaIcon(
                              FontAwesomeIcons.fish,
                              size: 42,
                              color: cor.withValues(alpha: 0.55),
                            ),
                            if (exibida['nome_variedade'] != null) ...[
                              const SizedBox(height: 6),
                              Text(
                                'Sem foto desta variedade ainda',
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: cor.withValues(alpha: 0.8),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  if (variedades.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    _buildVariedades(e, cor),
                  ],
                  const SizedBox(height: 14),

                  Row(
                    children: [
                      Expanded(
                        child: _requisito(
                          Icons.thermostat_rounded,
                          'Temperatura',
                          '${_n(e['temp_min'])}–${_n(e['temp_max'])} °C',
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _requisito(
                          Icons.science_outlined,
                          'pH',
                          '${_n(e['ph_min'])} – ${_n(e['ph_max'])}',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: _requisito(
                          Icons.water_drop_rounded,
                          'Volume mínimo',
                          '${e['volume_minimo_l'] ?? "?"}L',
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _requisito(
                          Icons.straighten_rounded,
                          'Tamanho adulto',
                          '${_n(e['tamanho_adulto_cm'])} cm',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: _requisito(
                          Icons.groups_rounded,
                          _rotuloComportamento(e['comportamento']?.toString()),
                          _rotuloAgrupamento(e),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _requisito(
                          Icons.restaurant_rounded,
                          'Alimentação',
                          _capitalizar(e['alimentacao']?.toString()),
                        ),
                      ),
                    ],
                  ),

                  _buildCredito(e),

                  if (e['observacoes'] != null &&
                      e['observacoes'].toString().isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.backgroundApp,
                        borderRadius: BorderRadius.circular(11),
                        border: Border.all(color: AppTheme.bordaCard),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.info_outline_rounded,
                              size: 15, color: AppTheme.ctaEntrar),
                          const SizedBox(width: 9),
                          Expanded(
                            child: Text(
                              e['observacoes'].toString(),
                              style: TextStyle(
                                fontSize: 12.5,
                                height: 1.4,
                                color: Colors.black.withValues(alpha: 0.62),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],

                  if (_aquarioSelecionado != null) ...[
                    const SizedBox(height: 14),
                    if (avisos.isEmpty)
                      _avisoBox(
                        'Compatível com ${_aquarioSelecionado!['nome']}',
                        'liberado',
                      )
                    else
                      ...avisos.map((a) => _avisoBox(a, decisao)),
                  ],

                  const SizedBox(height: 16),
                  _botaoAdicionar(
                    exibida,
                    decisao,
                    _jaEstaNoAquario(exibida['id'].toString()),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// Faixa horizontal com a base e cada variedade dela.
  static const Map<String, String> _climas = {
    'tropical': 'Tropical',
    'subtropical': 'Subtropical',
    'temperado': 'Temperado',
    'boreal': 'Boreal',
    'polar': 'Polar',
    'altitude': 'Altitude',
    'agua_profunda': 'Água profunda',
  };

  /// Clima da espécie e crédito de quem publicou as medidas.
  ///
  /// O crédito não é cortesia: as medidas importadas vêm da FishBase,
  /// cuja licença CC BY-NC exige atribuição onde o dado aparecer. Some
  /// da tela quando a ficha foi preenchida à mão, que é quando não há
  /// o que atribuir.
  ///
  /// O clima aparece junto porque é o que existe no lugar da faixa de
  /// temperatura nas fichas recém-importadas: a FishBase publica a
  /// faixa de sobrevivência na natureza, que para o kinguio vai de 0 a
  /// 41 graus, e aquilo não serve como recomendação de aquário.
  Widget _buildCredito(Map<String, dynamic> e) {
    final clima = _climas[e['clima']?.toString()];
    final fonte = e['fonte_dados']?.toString();
    final temFonte = fonte != null && fonte.isNotEmpty;

    if (clima == null && !temFonte) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            clima != null ? Icons.public_rounded : Icons.menu_book_rounded,
            size: 14,
            color: AppTheme.textoFraco,
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              [
                if (clima != null) 'Clima: $clima',
                if (temFonte) 'Medidas de $fonte',
              ].join('  ·  '),
              style: const TextStyle(
                fontSize: 11.5,
                color: AppTheme.textoFraco,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVariedades(Map<String, dynamic> e, Color cor) {
    final base = e['id'].toString();
    final escolhida = _variedadeEscolhida[base];
    final variedades = _variedadesDe(e);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Variedades',
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: FontWeight.w700,
            color: AppTheme.tituloBemVindo.withValues(alpha: 0.85),
          ),
        ),
        const SizedBox(height: 8),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _chipVariedade(
                rotulo: 'Padrão',
                miniatura: e['imagem_miniatura']?.toString(),
                cor: cor,
                ativo: escolhida == null,
                noAquario: _jaEstaNoAquario(base),
                onTap: () => setState(() => _variedadeEscolhida.remove(base)),
              ),
              for (final v in variedades)
                _chipVariedade(
                  rotulo: v['nome_curto']?.toString() ?? '',
                  miniatura: v['imagem_miniatura']?.toString(),
                  cor: cor,
                  ativo: escolhida == v['id'].toString(),
                  noAquario: _jaEstaNoAquario(v['id'].toString()),
                  onTap: () => setState(
                    () => _variedadeEscolhida[base] = v['id'].toString(),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _chipVariedade({
    required String rotulo,
    required String? miniatura,
    required Color cor,
    required bool ativo,
    required bool noAquario,
    required VoidCallback onTap,
  }) {
    // Material, e não Container com cor: a ondulação do toque é pintada
    // no Material mais próximo, e um Container colorido por cima a
    // esconderia — o mesmo defeito corrigido na tela de configurações.
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Material(
        color: ativo ? cor.withValues(alpha: 0.14) : AppTheme.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(
            color: ativo ? cor : AppTheme.bordaCard,
            width: ativo ? 1.6 : 1,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(5, 5, 12, 5),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                FotoEspecie(
                  caminho: miniatura,
                  cor: cor,
                  tamanho: 28,
                  proporcaoIcone: 0.5,
                ),
                const SizedBox(width: 7),
                Text(
                  rotulo,
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: ativo ? FontWeight.w700 : FontWeight.w500,
                    color: AppTheme.tituloBemVindo,
                  ),
                ),
                if (noAquario) ...[
                  const SizedBox(width: 5),
                  const Icon(
                    Icons.check_circle_rounded,
                    size: 14,
                    color: Color(0xFF00A878),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _botaoAdicionar(Map<String, dynamic> e, String decisao, bool jaTem) {
    if (_aquarioSelecionado == null) {
      return const SizedBox.shrink();
    }

    if (jaTem) {
      return OutlinedButton.icon(
        onPressed: null,
        icon: const Icon(Icons.check_rounded, size: 18),
        label: const Text('Já está no aquário'),
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(double.infinity, 52),
          side: BorderSide(color: AppTheme.bordaCard),
          foregroundColor: AppTheme.hintCampo,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
    }

    if (decisao == 'bloqueado') {
      return Column(
        children: [
          OutlinedButton.icon(
            onPressed: null,
            icon: const Icon(Icons.block_rounded, size: 18),
            label: const Text('Incompatível com este aquário'),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(double.infinity, 52),
              side: const BorderSide(color: Color(0xFFF5C6C6)),
              foregroundColor: AppTheme.error,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      );
    }

    return ElevatedButton.icon(
      onPressed: () => _abrirModalAdicionar(e),
      icon: const Icon(Icons.add_rounded, size: 19),
      label: const Text('Adicionar Peixe no Aquário'),
    );
  }

  // ─── Componentes visuais ────────────────────────────────
  Color _corBorda(String decisao) => switch (decisao) {
        'bloqueado' => const Color(0xFFF5C6C6),
        'requer_confirmacao' => const Color(0xFFFCE4B0),
        _ => AppTheme.bordaCard,
      };

  Widget _selo(String decisao) {
    final (cor, fundo, icone, texto) = switch (decisao) {
      'bloqueado' => (
          AppTheme.error,
          const Color(0xFFFDECEC),
          Icons.cancel_rounded,
          'Evitar',
        ),
      'requer_confirmacao' => (
          const Color(0xFFD97706),
          const Color(0xFFFFF9EC),
          Icons.warning_amber_rounded,
          'Atenção',
        ),
      _ => (
          const Color(0xFF00875A),
          const Color(0xFFE7F8EF),
          Icons.check_circle_rounded,
          'Ideal',
        ),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: fundo,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: cor.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icone, size: 13, color: cor),
          const SizedBox(width: 4),
          Text(
            texto,
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: cor),
          ),
        ],
      ),
    );
  }

  Widget _requisito(IconData icon, String label, String valor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.backgroundApp,
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: AppTheme.bordaCard),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppTheme.ctaEntrar),
          const SizedBox(width: 9),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontSize: 10.5, color: AppTheme.hintCampo)),
                const SizedBox(height: 1),
                Text(
                  valor,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.tituloBemVindo,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _avisoBox(String texto, String decisao) {
    final (cor, fundo, borda, icone) = switch (decisao) {
      'bloqueado' => (
          const Color(0xFF9B1C1C),
          const Color(0xFFFDECEC),
          const Color(0xFFF5C6C6),
          Icons.cancel_rounded,
        ),
      'requer_confirmacao' => (
          const Color(0xFF92400E),
          const Color(0xFFFFF9EC),
          const Color(0xFFFCE4B0),
          Icons.warning_amber_rounded,
        ),
      _ => (
          const Color(0xFF00694A),
          const Color(0xFFE7F8EF),
          const Color(0xFF9BDDBB),
          Icons.check_circle_rounded,
        ),
    };

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: fundo,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borda),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icone, size: 16, color: cor),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              texto,
              style: TextStyle(
                fontSize: 12.5,
                color: cor,
                fontWeight: FontWeight.w600,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _rotuloComportamento(String? c) => switch (c) {
        'pacifico' => 'Pacífico',
        'semi_agressivo' => 'Semi-agressivo',
        'territorial' => 'Territorial',
        'agressivo' => 'Agressivo',
        _ => 'Comportamento',
      };

  String _rotuloAgrupamento(Map<String, dynamic> e) => switch (e['agrupamento']) {
        'cardume' => 'Cardume de ${e['cardume_minimo'] ?? 6}+',
        'par' => 'Viver em par',
        'harem' => 'Harém',
        'solitario' => 'Solitário',
        _ => '—',
      };

  String _capitalizar(String? texto) {
    if (texto == null || texto.isEmpty) return '—';
    return texto[0].toUpperCase() + texto.substring(1);
  }
}

// ═══════════════════════════════════════════════════════════
// MODAL DE ADIÇÃO — analisa em tempo real e trata as 3 decisões
// ═══════════════════════════════════════════════════════════
class _DialogAdicionar extends StatefulWidget {
  final Map<String, dynamic> especie;
  final Map<String, dynamic> aquario;
  final Color cor;
  final Function(String) onConcluido;

  const _DialogAdicionar({
    required this.especie,
    required this.aquario,
    required this.cor,
    required this.onConcluido,
  });

  @override
  State<_DialogAdicionar> createState() => _DialogAdicionarState();
}

class _DialogAdicionarState extends State<_DialogAdicionar> {
  late int _quantidade;
  Map<String, dynamic>? _analise;
  bool _analisando = true;
  bool _salvando = false;
  int _requisicao = 0;

  @override
  void initState() {
    super.initState();
    // Já sugere o cardume mínimo quando a espécie precisa de grupo
    _quantidade = (widget.especie['cardume_minimo'] as int?) ?? 1;
    _analisar();
  }

  Future<void> _analisar() async {
    final minhaRequisicao = ++_requisicao;
    setState(() => _analisando = true);

    final resp = await PeixeService.analisar(
      especieId: widget.especie['id'].toString(),
      aquarioId: widget.aquario['id'].toString(),
      quantidade: _quantidade,
    );

    // Descarta respostas antigas se o usuário mudou a quantidade rápido
    if (!mounted || minhaRequisicao != _requisicao) return;

    setState(() {
      _analisando = false;
      _analise = resp['sucesso'] == true ? resp['dados'] : null;
    });
  }

  void _mudarQuantidade(int novo) {
    if (novo < 1) return;
    setState(() => _quantidade = novo);
    _analisar();
  }

  Future<void> _confirmar() async {
    final decisao = _analise?['decisao']?.toString() ?? 'liberado';
    if (decisao == 'bloqueado') return;

    setState(() => _salvando = true);

    final resp = await PeixeService.adicionar(
      aquarioId: widget.aquario['id'].toString(),
      especieId: widget.especie['id'].toString(),
      quantidade: _quantidade,
      confirmar: decisao == 'requer_confirmacao',
    );

    if (!mounted) return;
    setState(() => _salvando = false);

    if (resp['sucesso'] == true) {
      Navigator.pop(context);
      widget.onConcluido(
        '$_quantidade ${widget.especie['nome_comum']} adicionado(s) a ${widget.aquario['nome']}',
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(resp['erro']?.toString() ?? 'Erro ao adicionar'),
          backgroundColor: AppTheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final e = widget.especie;
    final decisao = _analise?['decisao']?.toString() ?? 'liberado';
    final avisos = _analise == null
        ? <String>[]
        : List<Map<String, dynamic>>.from(_analise!['avisos'] ?? [])
            .map((a) => a['mensagem'].toString())
            .toList();

    return Dialog(
      backgroundColor: AppTheme.white,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── Cabeçalho ────────────────────────────
              Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: widget.cor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(11),
                    ),
                    child: Center(
                      child: FaIcon(FontAwesomeIcons.fish, size: 16, color: widget.cor),
                    ),
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          e['nome_comum']?.toString() ?? '—',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            color: AppTheme.tituloBemVindo,
                          ),
                        ),
                        Text(
                          'em ${widget.aquario['nome']}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.hintCampo),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // ─── Contador ─────────────────────────────
              const Text(
                'Quantidade de peixes',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.labelCampo,
                ),
              ),
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _botaoContador(
                    Icons.remove_rounded,
                    _quantidade > 1 ? () => _mudarQuantidade(_quantidade - 1) : null,
                  ),
                  Container(
                    width: 86,
                    height: 52,
                    margin: const EdgeInsets.symmetric(horizontal: 14),
                    decoration: BoxDecoration(
                      color: AppTheme.backgroundApp,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.bordaCampo),
                    ),
                    child: Center(
                      child: Text(
                        '$_quantidade',
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.tituloBemVindo,
                        ),
                      ),
                    ),
                  ),
                  _botaoContador(
                    Icons.add_rounded,
                    () => _mudarQuantidade(_quantidade + 1),
                  ),
                ],
              ),
              const SizedBox(height: 18),

              // ─── Resultado da análise ─────────────────
              if (_analisando)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Center(
                    child: SizedBox(
                      height: 22,
                      width: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: AppTheme.ctaEntrar,
                      ),
                    ),
                  ),
                )
              else ...[
                if (avisos.isEmpty)
                  _caixa(
                    'Tudo certo para adicionar',
                    'liberado',
                    Icons.check_circle_rounded,
                  )
                else
                  ...avisos.map(
                    (a) => _caixa(
                      a,
                      decisao,
                      decisao == 'bloqueado'
                          ? Icons.cancel_rounded
                          : Icons.warning_amber_rounded,
                    ),
                  ),
              ],
              const SizedBox(height: 16),

              // ─── Ações ────────────────────────────────
              if (decisao == 'bloqueado')
                OutlinedButton.icon(
                  onPressed: null,
                  icon: const Icon(Icons.block_rounded, size: 18),
                  label: const Text('Não é possível adicionar'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 52),
                    side: const BorderSide(color: Color(0xFFF5C6C6)),
                    foregroundColor: AppTheme.error,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                )
              else
                ElevatedButton(
                  onPressed: (_salvando || _analisando) ? null : _confirmar,
                  style: decisao == 'requer_confirmacao'
                      ? ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFFD97706),
                          foregroundColor: Colors.white,
                          minimumSize: const Size(double.infinity, 52),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        )
                      : null,
                  child: _salvando
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2,
                          ),
                        )
                      : Text(
                          decisao == 'requer_confirmacao'
                              ? 'Adicionar mesmo assim'
                              : 'Adicionar',
                        ),
                ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: _salvando ? null : () => Navigator.pop(context),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 52),
                  side: const BorderSide(color: AppTheme.error),
                  foregroundColor: AppTheme.error,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                ),
                child: const Text('Cancelar'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _caixa(String texto, String decisao, IconData icone) {
    final (cor, fundo, borda) = switch (decisao) {
      'bloqueado' => (
          const Color(0xFF9B1C1C),
          const Color(0xFFFDECEC),
          const Color(0xFFF5C6C6),
        ),
      'requer_confirmacao' => (
          const Color(0xFF92400E),
          const Color(0xFFFFF9EC),
          const Color(0xFFFCE4B0),
        ),
      _ => (
          const Color(0xFF00694A),
          const Color(0xFFE7F8EF),
          const Color(0xFF9BDDBB),
        ),
    };

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: fundo,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borda),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icone, size: 16, color: cor),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              texto,
              style: TextStyle(
                fontSize: 12.5,
                color: cor,
                fontWeight: FontWeight.w600,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _botaoContador(IconData icon, VoidCallback? onTap) {
    final ativo = onTap != null;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: ativo ? AppTheme.ctaEntrar.withValues(alpha: 0.10) : AppTheme.backgroundApp,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: ativo ? AppTheme.bordaCampo : AppTheme.bordaCard,
            ),
          ),
          child: Icon(
            icon,
            size: 20,
            color: ativo ? AppTheme.ctaEntrar : AppTheme.hintCampo.withValues(alpha: 0.4),
          ),
        ),
      ),
    );
  }
}