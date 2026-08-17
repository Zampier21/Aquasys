import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import '../Tema/app_tema.dart';
import '../widgets/bottom_nav.dart';
import '../services/aquario_service.dart';
import 'tela_inicial.dart';
import 'tela_aquarios.dart';
import 'tela_clientes.dart';

// ═══════════════════════════════════════════════════════════
// CATÁLOGO DE ESPÉCIES (mockado — virá da tabela `especie`)
// ═══════════════════════════════════════════════════════════
class Especie {
  final String id;
  final String nomeComum;
  final String nomeCientifico;
  final double tempMin;
  final double tempMax;
  final double phMin;
  final double phMax;
  final int volumeMinimo;
  final String comportamento; // pacifico | territorial | agressivo
  final String agrupamento;   // cardume | par | solitario
  final int? cardumeMinimo;
  final String dificuldade;   // facil | medio | dificil
  final String alimentacao;
  final Color cor;

  const Especie({
    required this.id,
    required this.nomeComum,
    required this.nomeCientifico,
    required this.tempMin,
    required this.tempMax,
    required this.phMin,
    required this.phMax,
    required this.volumeMinimo,
    required this.comportamento,
    required this.agrupamento,
    this.cardumeMinimo,
    required this.dificuldade,
    required this.alimentacao,
    required this.cor,
  });
}

const List<Especie> catalogoEspecies = [
  Especie(
    id: 'e1',
    nomeComum: 'Neon Tetra',
    nomeCientifico: 'Paracheirodon innesi',
    tempMin: 20, tempMax: 26,
    phMin: 6, phMax: 7,
    volumeMinimo: 40,
    comportamento: 'pacifico',
    agrupamento: 'cardume',
    cardumeMinimo: 10,
    dificuldade: 'facil',
    alimentacao: 'Onívoro — ração em flocos e alimento vivo',
    cor: Color(0xFF2E86C1),
  ),
  Especie(
    id: 'e2',
    nomeComum: 'Betta',
    nomeCientifico: 'Betta splendens',
    tempMin: 24, tempMax: 28,
    phMin: 6.5, phMax: 7.5,
    volumeMinimo: 10,
    comportamento: 'territorial',
    agrupamento: 'solitario',
    dificuldade: 'facil',
    alimentacao: 'Carnívoro — ração específica e larvas',
    cor: Color(0xFFC0392B),
  ),
  Especie(
    id: 'e3',
    nomeComum: 'Coridora Panda',
    nomeCientifico: 'Corydoras panda',
    tempMin: 22, tempMax: 26,
    phMin: 6, phMax: 7.4,
    volumeMinimo: 60,
    comportamento: 'pacifico',
    agrupamento: 'cardume',
    cardumeMinimo: 6,
    dificuldade: 'facil',
    alimentacao: 'Onívoro de fundo — pastilhas',
    cor: Color(0xFF566573),
  ),
  Especie(
    id: 'e4',
    nomeComum: 'Acará Disco',
    nomeCientifico: 'Symphysodon aequifasciatus',
    tempMin: 28, tempMax: 30,
    phMin: 5.5, phMax: 6.5,
    volumeMinimo: 200,
    comportamento: 'pacifico',
    agrupamento: 'cardume',
    cardumeMinimo: 5,
    dificuldade: 'dificil',
    alimentacao: 'Carnívoro — alimento congelado e ração premium',
    cor: Color(0xFFCA6F1E),
  ),
  Especie(
    id: 'e5',
    nomeComum: 'Barbo Sumatra',
    nomeCientifico: 'Puntigrus tetrazona',
    tempMin: 23, tempMax: 27,
    phMin: 6, phMax: 7.5,
    volumeMinimo: 80,
    comportamento: 'agressivo',
    agrupamento: 'cardume',
    cardumeMinimo: 8,
    dificuldade: 'medio',
    alimentacao: 'Onívoro — flocos e vegetais',
    cor: Color(0xFFD4AC0D),
  ),
];

// ═══════════════════════════════════════════════════════════
// RESULTADO DA ANÁLISE DE COMPATIBILIDADE
// ═══════════════════════════════════════════════════════════
enum NivelCompat { otimo, atencao, incompativel }

class Compatibilidade {
  final NivelCompat nivel;
  final List<String> avisos;
  const Compatibilidade(this.nivel, this.avisos);
}

// ═══════════════════════════════════════════════════════════
// TELA
// ═══════════════════════════════════════════════════════════
class TelaPeixes extends StatefulWidget {
  final String tipoUsuario;
  const TelaPeixes({super.key, required this.tipoUsuario});

  @override
  State<TelaPeixes> createState() => _TelaPeixesState();
}

class _TelaPeixesState extends State<TelaPeixes> {
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

  final _buscaCtrl = TextEditingController();
  String _busca = '';
  final Set<String> _abertos = {};

  List<Map<String, dynamic>> _aquarios = [];
  Map<String, dynamic>? _aquarioSelecionado;
  bool _carregandoAquarios = true;

  @override
  void initState() {
    super.initState();
    _carregarAquarios();
  }

  @override
  void dispose() {
    _buscaCtrl.dispose();
    super.dispose();
  }

  Future<void> _carregarAquarios() async {
    final resultado = await AquarioService.listar();
    if (!mounted) return;
    setState(() {
      _carregandoAquarios = false;
      if (resultado['sucesso'] == true) {
        _aquarios = List<Map<String, dynamic>>.from(resultado['dados']);
        if (_aquarios.isNotEmpty) _aquarioSelecionado = _aquarios.first;
      }
    });
  }

  // ─── Análise de compatibilidade ─────────────────────────
  Compatibilidade _analisar(Especie e, Map<String, dynamic>? aq) {
    if (aq == null) return const Compatibilidade(NivelCompat.otimo, []);

    final avisos = <String>[];
    var incompativel = false;

    final temp = (aq['temperatura'] as num?)?.toDouble() ?? 0;
    final ph = (aq['ph'] as num?)?.toDouble() ?? 0;
    final volume = (aq['volume_litros'] as num?)?.toDouble() ?? 0;

    if (temp < e.tempMin) {
      avisos.add('Temperatura baixa: precisa de ${_n(e.tempMin)}–${_n(e.tempMax)} °C');
    } else if (temp > e.tempMax) {
      avisos.add('Temperatura alta: precisa de ${_n(e.tempMin)}–${_n(e.tempMax)} °C');
    }

    if (ph < e.phMin) {
      avisos.add('Requer pH acima de ${_n(e.phMin)}');
    } else if (ph > e.phMax) {
      avisos.add('Requer pH abaixo de ${_n(e.phMax)}');
    }

    if (volume < e.volumeMinimo) {
      avisos.add('Volume insuficiente: mínimo de ${e.volumeMinimo}L');
      incompativel = true;
    }

    if (e.comportamento == 'agressivo') {
      avisos.add('Espécie agressiva — não é boa para comunitário');
      incompativel = true;
    } else if (e.comportamento == 'territorial') {
      avisos.add('Territorial — evite machos da mesma espécie juntos');
    }

    if (avisos.isEmpty) return const Compatibilidade(NivelCompat.otimo, []);
    return Compatibilidade(
      incompativel ? NivelCompat.incompativel : NivelCompat.atencao,
      avisos,
    );
  }

  String _n(double v) => v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toString();

  List<Especie> get _especiesFiltradas {
    if (_busca.trim().isEmpty) return catalogoEspecies;
    final termo = _busca.toLowerCase().trim();
    return catalogoEspecies
        .where((e) =>
            e.nomeComum.toLowerCase().contains(termo) ||
            e.nomeCientifico.toLowerCase().contains(termo))
        .toList();
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

  // ─── Modal de quantidade ────────────────────────────────
  void _adicionarAoAquario(Especie e) {
    final compat = _analisar(e, _aquarioSelecionado);

    showDialog(
      context: context,
      builder: (_) => _DialogQuantidade(
        especie: e,
        aquario: _aquarioSelecionado,
        compatibilidade: compat,
        onConfirmar: (qtd) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                '$qtd ${e.nomeComum} adicionado(s) a ${_aquarioSelecionado?['nome'] ?? "aquário"}',
              ),
              backgroundColor: AppTheme.ctaEntrar,
              behavior: SnackBarBehavior.floating,
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            _buildBusca(),
            _buildFiltroAquarios(),
            if (_aquarioSelecionado != null) _buildParametrosAtuais(),
            const SizedBox(height: 6),
            Expanded(child: _buildLista()),
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

  // ═══════════════════════════════════════════════════
  Widget _buildHeader() {
    final isDono = widget.tipoUsuario == 'dono';
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
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
            onPressed: () {},
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  Widget _buildBusca() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
      child: TextField(
        controller: _buscaCtrl,
        onChanged: (v) => setState(() => _busca = v),
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
                    setState(() => _busca = '');
                  },
                ),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  Widget _buildFiltroAquarios() {
    if (_carregandoAquarios) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 18),
        child: SizedBox(
          height: 18,
          width: 18,
          child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.ctaEntrar),
        ),
      );
    }

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
                onTap: () => setState(() => _aquarioSelecionado = aq),
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

  // ═══════════════════════════════════════════════════
  Widget _buildParametrosAtuais() {
    final aq = _aquarioSelecionado!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          color: const Color(0xFFEAF6FD),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.bordaCampo),
        ),
        child: Row(
          children: [
            const Icon(Icons.tune_rounded, size: 16, color: AppTheme.ctaEntrar),
            const SizedBox(width: 9),
            const Text(
              'Seus parâmetros:',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTheme.tituloBemVindo,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'pH ${_n((aq['ph'] as num).toDouble())}   ·   '
                '${_n((aq['temperatura'] as num).toDouble())} °C   ·   '
                '${_n((aq['volume_litros'] as num).toDouble())}L',
                style: const TextStyle(fontSize: 12, color: AppTheme.tituloBemVindo),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  Widget _buildLista() {
    final especies = _especiesFiltradas;

    if (especies.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off_rounded, size: 52, color: AppTheme.hintCampo.withOpacity(0.4)),
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
              style: TextStyle(fontSize: 13, color: AppTheme.hintCampo.withOpacity(0.9)),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
      itemCount: especies.length,
      itemBuilder: (_, i) => _buildCardEspecie(especies[i]),
    );
  }

  // ═══════════════════════════════════════════════════
  // CARD DA ESPÉCIE
  // ═══════════════════════════════════════════════════
  Widget _buildCardEspecie(Especie e) {
    final expandido = _abertos.contains(e.id);
    final compat = _analisar(e, _aquarioSelecionado);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _corBorda(compat.nivel)),
        boxShadow: _sombraCard,
      ),
      child: Column(
        children: [
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(15),
              onTap: () => setState(() {
                expandido ? _abertos.remove(e.id) : _abertos.add(e.id);
              }),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                child: Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: e.cor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Center(
                        child: FaIcon(FontAwesomeIcons.fish, size: 18, color: e.cor),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            e.nomeComum,
                            style: const TextStyle(
                              fontSize: 15.5,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.tituloBemVindo,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            e.nomeCientifico,
                            style: TextStyle(
                              fontSize: 12,
                              fontStyle: FontStyle.italic,
                              color: AppTheme.hintCampo.withOpacity(0.95),
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (_aquarioSelecionado != null) _selo(compat.nivel),
                    const SizedBox(width: 6),
                    AnimatedRotation(
                      turns: expandido ? 0.5 : 0,
                      duration: const Duration(milliseconds: 200),
                      child: Icon(
                        Icons.keyboard_arrow_down_rounded,
                        color: AppTheme.hintCampo.withOpacity(0.7),
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
                  // Faixa ilustrativa da espécie
                  Container(
                    height: 96,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          e.cor.withOpacity(0.16),
                          e.cor.withOpacity(0.05),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Center(
                      child: FaIcon(
                        FontAwesomeIcons.fish,
                        size: 42,
                        color: e.cor.withOpacity(0.55),
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Requisitos em grade
                  Row(
                    children: [
                      Expanded(
                        child: _requisito(
                          Icons.thermostat_rounded,
                          'Temperatura',
                          '${_n(e.tempMin)}–${_n(e.tempMax)} °C',
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _requisito(
                          Icons.science_outlined,
                          'pH',
                          '${_n(e.phMin)} – ${_n(e.phMax)}',
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
                          '${e.volumeMinimo}L',
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _requisito(
                          Icons.groups_rounded,
                          _rotuloComportamento(e.comportamento),
                          _rotuloAgrupamento(e),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  _requisito(
                    Icons.restaurant_rounded,
                    'Alimentação',
                    e.alimentacao,
                    largura: true,
                  ),

                  // Avisos de compatibilidade
                  if (_aquarioSelecionado != null && compat.avisos.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    ...compat.avisos.map((a) => _aviso(a, compat.nivel)),
                  ],

                  if (_aquarioSelecionado != null && compat.avisos.isEmpty) ...[
                    const SizedBox(height: 14),
                    _aviso(
                      'Compatível com ${_aquarioSelecionado!['nome']}',
                      NivelCompat.otimo,
                    ),
                  ],

                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _aquarioSelecionado == null
                        ? null
                        : () => _adicionarAoAquario(e),
                    icon: const Icon(Icons.add_rounded, size: 19),
                    label: const Text('Adicionar Peixe no Aquário'),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // ─── Auxiliares visuais ─────────────────────────────────
  Color _corBorda(NivelCompat n) => switch (n) {
        NivelCompat.otimo => AppTheme.bordaCard,
        NivelCompat.atencao => const Color(0xFFFCE4B0),
        NivelCompat.incompativel => const Color(0xFFF5C6C6),
      };

  Widget _selo(NivelCompat n) {
    final (cor, fundo, icone, texto) = switch (n) {
      NivelCompat.otimo => (
          const Color(0xFF00875A),
          const Color(0xFFE7F8EF),
          Icons.check_circle_rounded,
          'Ideal',
        ),
      NivelCompat.atencao => (
          const Color(0xFFD97706),
          const Color(0xFFFFF9EC),
          Icons.warning_amber_rounded,
          'Atenção',
        ),
      NivelCompat.incompativel => (
          AppTheme.error,
          const Color(0xFFFDECEC),
          Icons.cancel_rounded,
          'Evitar',
        ),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: fundo,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: cor.withOpacity(0.35)),
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

  Widget _requisito(IconData icon, String label, String valor, {bool largura = false}) {
    return Container(
      width: largura ? double.infinity : null,
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

  Widget _aviso(String texto, NivelCompat nivel) {
    final (cor, fundo, borda, icone) = switch (nivel) {
      NivelCompat.otimo => (
          const Color(0xFF00694A),
          const Color(0xFFE7F8EF),
          const Color(0xFF9BDDBB),
          Icons.check_circle_rounded,
        ),
      NivelCompat.atencao => (
          const Color(0xFF92400E),
          const Color(0xFFFFF9EC),
          const Color(0xFFFCE4B0),
          Icons.warning_amber_rounded,
        ),
      NivelCompat.incompativel => (
          const Color(0xFF9B1C1C),
          const Color(0xFFFDECEC),
          const Color(0xFFF5C6C6),
          Icons.cancel_rounded,
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

  String _rotuloComportamento(String c) => switch (c) {
        'pacifico' => 'Pacífico',
        'territorial' => 'Territorial',
        _ => 'Agressivo',
      };

  String _rotuloAgrupamento(Especie e) => switch (e.agrupamento) {
        'cardume' => 'Cardume de ${e.cardumeMinimo ?? 6}+',
        'par' => 'Viver em par',
        _ => 'Solitário',
      };
}

// ═══════════════════════════════════════════════════════════
// MODAL DE QUANTIDADE
// ═══════════════════════════════════════════════════════════
class _DialogQuantidade extends StatefulWidget {
  final Especie especie;
  final Map<String, dynamic>? aquario;
  final Compatibilidade compatibilidade;
  final Function(int) onConfirmar;

  const _DialogQuantidade({
    required this.especie,
    required this.aquario,
    required this.compatibilidade,
    required this.onConfirmar,
  });

  @override
  State<_DialogQuantidade> createState() => _DialogQuantidadeState();
}

class _DialogQuantidadeState extends State<_DialogQuantidade> {
  late int _quantidade;

  @override
  void initState() {
    super.initState();
    // Sugere o cardume mínimo quando a espécie precisa viver em grupo
    _quantidade = widget.especie.cardumeMinimo ?? 1;
  }

  @override
  Widget build(BuildContext context) {
    final e = widget.especie;
    final precisaCardume = e.agrupamento == 'cardume' && e.cardumeMinimo != null;
    final abaixoDoIdeal = precisaCardume && _quantidade < e.cardumeMinimo!;

    return Dialog(
      backgroundColor: AppTheme.white,
      insetPadding: const EdgeInsets.symmetric(horizontal: 28),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: e.cor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Center(
                    child: FaIcon(FontAwesomeIcons.fish, size: 16, color: e.cor),
                  ),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        e.nomeComum,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.tituloBemVindo,
                        ),
                      ),
                      Text(
                        'em ${widget.aquario?['nome'] ?? "—"}',
                        style: const TextStyle(fontSize: 12, color: AppTheme.hintCampo),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            const Text(
              'Quantidade de peixes',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppTheme.labelCampo,
              ),
            ),
            const SizedBox(height: 10),

            // Contador
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _botaoContador(
                  Icons.remove_rounded,
                  _quantidade > 1 ? () => setState(() => _quantidade--) : null,
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
                  () => setState(() => _quantidade++),
                ),
              ],
            ),

            if (precisaCardume) ...[
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: abaixoDoIdeal ? const Color(0xFFFFF9EC) : const Color(0xFFE7F8EF),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: abaixoDoIdeal ? const Color(0xFFFCE4B0) : const Color(0xFF9BDDBB),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      abaixoDoIdeal ? Icons.warning_amber_rounded : Icons.check_circle_rounded,
                      size: 16,
                      color: abaixoDoIdeal ? const Color(0xFFD97706) : const Color(0xFF00875A),
                    ),
                    const SizedBox(width: 9),
                    Expanded(
                      child: Text(
                        abaixoDoIdeal
                            ? 'Esta espécie vive melhor em cardume de ${e.cardumeMinimo}+ indivíduos'
                            : 'Quantidade adequada para cardume',
                        style: TextStyle(
                          fontSize: 12,
                          height: 1.3,
                          color: abaixoDoIdeal
                              ? const Color(0xFF92400E)
                              : const Color(0xFF00694A),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                widget.onConfirmar(_quantidade);
              },
              child: const Text('Adicionar'),
            ),
            const SizedBox(height: 10),
            OutlinedButton(
              onPressed: () => Navigator.pop(context),
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
            color: ativo ? AppTheme.ctaEntrar.withOpacity(0.10) : AppTheme.backgroundApp,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: ativo ? AppTheme.bordaCampo : AppTheme.bordaCard,
            ),
          ),
          child: Icon(
            icon,
            size: 20,
            color: ativo ? AppTheme.ctaEntrar : AppTheme.hintCampo.withOpacity(0.4),
          ),
        ),
      ),
    );
  }
}