import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../widgets/bottom_nav.dart';
import '../services/aquario_service.dart';
import 'tela_inicial.dart';
import 'tela_peixes.dart';
import 'tela_clientes.dart';

// ═══════════════════════════════════════════════════════════
// FAIXAS IDEAIS E DICAS DOS PARÂMETROS
// ═══════════════════════════════════════════════════════════
class ParametroInfo {
  final String nome;
  final String campoApi;
  final String faixaIdeal;
  final String oQueE;
  final List<String> dicas;
  final double? min;
  final double? max;

  const ParametroInfo({
    required this.nome,
    required this.campoApi,
    required this.faixaIdeal,
    required this.oQueE,
    required this.dicas,
    this.min,
    this.max,
  });
}

const Map<String, ParametroInfo> parametrosInfo = {
  'temperatura': ParametroInfo(
    nome: 'Temperatura',
    campoApi: 'temperatura',
    faixaIdeal: '24 °C – 28 °C (peixes tropicais)',
    oQueE: 'A temperatura ideal varia por espécie. Peixes tropicais geralmente '
        'precisam de água aquecida e estável ao longo do dia.',
    dicas: [
      'Use termostato para manter estável',
      'Temperatura muito baixa deixa peixes lentos',
      'Temperatura muito alta reduz o oxigênio',
    ],
    min: 24,
    max: 28,
  ),
  'ph': ParametroInfo(
    nome: 'pH',
    campoApi: 'ph',
    faixaIdeal: '6.5 – 7.0 (comunitário)',
    oQueE: 'O pH mede a acidez da água, numa escala de 0 a 14. Valores próximos de 7 são '
        'neutros. Cada espécie tem sua faixa de conforto.',
    dicas: [
      'Alterações bruscas estressam mais que valores fora do ideal',
      'Corrija sempre de forma gradual, ao longo de dias',
      'Meça sempre no mesmo horário do dia',
    ],
    min: 6.5,
    max: 7.0,
  ),
  'amonia': ParametroInfo(
    nome: 'Amônia (NH₃)',
    campoApi: 'amonia_ppm',
    faixaIdeal: '0 ppm — sempre zero',
    oQueE: 'A amônia vem das fezes e da ração não consumida. É altamente tóxica: '
        'qualquer valor acima de zero já indica problema no aquário.',
    dicas: [
      'Presença de amônia pede troca parcial de água imediata',
      'Reduza a alimentação até normalizar',
      'Nunca lave a mídia do filtro em água clorada',
    ],
    min: 0,
    max: 0,
  ),
  'nitrito': ParametroInfo(
    nome: 'Nitrito (NO₂)',
    campoApi: 'nitrito_ppm',
    faixaIdeal: '0 ppm — sempre zero',
    oQueE: 'É o segundo estágio do ciclo do nitrogênio: as bactérias convertem amônia '
        'em nitrito. Continua sendo tóxico para os peixes.',
    dicas: [
      'Nitrito acima de zero indica ciclagem incompleta',
      'Evite adicionar novos peixes nessa fase',
      'Faça trocas parciais até zerar',
    ],
    min: 0,
    max: 0,
  ),
  'nitrato': ParametroInfo(
    nome: 'Nitrato (NO₃)',
    campoApi: 'nitrato_ppm',
    faixaIdeal: 'Abaixo de 40 ppm',
    oQueE: 'É o produto final do ciclo do nitrogênio. Bem menos tóxico que amônia e '
        'nitrito, mas o acúmulo favorece algas e estressa os peixes.',
    dicas: [
      'Trocas parciais semanais mantêm o nitrato baixo',
      'Plantas naturais ajudam a consumir nitrato',
      'Excesso de nitrato costuma causar algas',
    ],
    min: 0,
    max: 40,
  ),
};

// ═══════════════════════════════════════════════════════════
// TELA DE AQUÁRIOS
// ═══════════════════════════════════════════════════════════
class TelaAquarios extends StatefulWidget {
  final String tipoUsuario;
  const TelaAquarios({super.key, required this.tipoUsuario});

  @override
  State<TelaAquarios> createState() => _TelaAquariosState();
}

class _TelaAquariosState extends State<TelaAquarios> {
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

  List<Map<String, dynamic>> _aquarios = [];
  final Set<String> _abertos = {};
  bool _carregando = true;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  // ─── Carrega os aquários da API ─────────────────────────
  Future<void> _carregar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    final resultado = await AquarioService.listar();
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (resultado['sucesso'] == true) {
        _aquarios = List<Map<String, dynamic>>.from(resultado['dados']);
      } else {
        _erro = resultado['erro'];
      }
    });
  }

  void _aviso(String mensagem, {bool erro = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(mensagem),
        backgroundColor: erro ? AppTheme.error : AppTheme.ctaEntrar,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  // ─── Detecta parâmetros fora da faixa ───────────────────
  List<String> _parametrosComAlerta(Map<String, dynamic> aq) {
    final problemas = <String>[];
    for (final info in parametrosInfo.values) {
      if (info.min == null || info.max == null) continue;
      final valor = (aq[info.campoApi] as num?)?.toDouble();
      if (valor == null) continue;
      if (valor < info.min! || valor > info.max!) problemas.add(info.nome);
    }
    return problemas;
  }

  String _textoAlerta(List<String> problemas) {
    if (problemas.length == 1) {
      return 'O parâmetro ${problemas.first} precisa de atenção';
    }
    final anteriores = problemas.sublist(0, problemas.length - 1).join(', ');
    return 'Os parâmetros $anteriores e ${problemas.last} precisam de atenção';
  }

  // Converte ISO 8601 da API em dd/MM/aaaa
  String _formatarData(dynamic iso) {
    if (iso == null) return 'Sem registro';
    final data = DateTime.tryParse(iso.toString());
    if (data == null) return 'Sem registro';
    final d = data.day.toString().padLeft(2, '0');
    final m = data.month.toString().padLeft(2, '0');
    return '$d/$m/${data.year}';
  }

  String _num(dynamic valor) {
    if (valor == null) return '0';
    final n = (valor as num).toDouble();
    return n == n.roundToDouble() ? n.toStringAsFixed(0) : n.toString();
  }

  void _onNavTap(int index) {
    if (index == 1) return;
    final t = widget.tipoUsuario;
    final destino = switch (index) {
      0 => TelaInicial(tipoUsuario: t),
      2 => TelaPeixes(tipoUsuario: t),
      _ => TelaClientes(tipoUsuario: t),
    };
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => destino));
  }

  void _mostrarDica(String chave) {
    final info = parametrosInfo[chave];
    if (info == null) return;
    showDialog(context: context, builder: (_) => _DialogDica(info: info));
  }

  // ─── Formulário: criar ou editar ────────────────────────
  void _abrirFormulario({Map<String, dynamic>? aquario}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _FormularioAquario(
        aquario: aquario,
        onMostrarDica: _mostrarDica,
        onSalvar: (dados) async {
          final editando = aquario != null;

          final resultado = editando
              ? await AquarioService.editar(
                  id: aquario['id'],
                  nome: dados['nome'],
                  volumeLitros: dados['volume_litros'],
                  temperatura: dados['temperatura'],
                  ph: dados['ph'],
                  amonia: dados['amonia_ppm'],
                  nitrito: dados['nitrito_ppm'],
                  nitrato: dados['nitrato_ppm'],
                )
              : await AquarioService.criar(
                  nome: dados['nome'],
                  volumeLitros: dados['volume_litros'],
                  temperatura: dados['temperatura'],
                  ph: dados['ph'],
                  amonia: dados['amonia_ppm'],
                  nitrito: dados['nitrito_ppm'],
                  nitrato: dados['nitrato_ppm'],
                );

          if (resultado['sucesso'] == true) {
            _aviso(editando ? 'Aquário atualizado' : 'Aquário criado');
            await _carregar();
          } else {
            _aviso(resultado['erro'] ?? 'Erro ao salvar', erro: true);
          }
        },
      ),
    );
  }

  // ─── Excluir ────────────────────────────────────────────
  void _excluir(String id, String nome) {
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Excluir aquário',
          style: TextStyle(
            fontSize: 17,
            color: AppTheme.tituloBemVindo,
            fontWeight: FontWeight.w700,
          ),
        ),
        content: Text(
          'Tem certeza que deseja excluir o aquário "$nome"? '
          'Todo o histórico de parâmetros será perdido.',
          style: TextStyle(
            fontSize: 13.5,
            color: Colors.black.withOpacity(0.65),
            height: 1.4,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancelar', style: TextStyle(color: AppTheme.hintCampo)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.error,
              minimumSize: const Size(0, 42),
              padding: const EdgeInsets.symmetric(horizontal: 20),
            ),
            onPressed: () async {
              Navigator.pop(dialogContext);
              final resultado = await AquarioService.excluir(id);
              if (resultado['sucesso'] == true) {
                _abertos.remove(id);
                _aviso('Aquário excluído');
                await _carregar();
              } else {
                _aviso(resultado['erro'] ?? 'Erro ao excluir', erro: true);
              }
            },
            child: const Text('Excluir'),
          ),
        ],
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
            _buildCardTitulo(),
            Expanded(child: _buildConteudo()),
          ],
        ),
      ),
      bottomNavigationBar: BottomNav(
        currentIndex: 1,
        onTap: _onNavTap,
        isDono: widget.tipoUsuario == 'dono',
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // HEADER
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
  // CARD DE TÍTULO + CTA
  // ═══════════════════════════════════════════════════
  Widget _buildCardTitulo() {
    final total = _aquarios.length;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFEAF6FD), Color(0xFFF4FAFE)],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.bordaCampo),
          boxShadow: _sombraCard,
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Meus Aquários',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.tituloBemVindo,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _carregando
                        ? 'Carregando...'
                        : '$total ${total == 1 ? "aquário cadastrado" : "aquários cadastrados"}',
                    style: const TextStyle(fontSize: 12.5, color: AppTheme.hintCampo),
                  ),
                ],
              ),
            ),
            ElevatedButton.icon(
              onPressed: () => _abrirFormulario(),
              icon: const Icon(Icons.add_rounded, size: 19),
              label: const Text('Novo'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.ctaEntrar,
                foregroundColor: Colors.white,
                minimumSize: const Size(0, 44),
                padding: const EdgeInsets.symmetric(horizontal: 20),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
              ).copyWith(
                elevation: WidgetStateProperty.all(4),
                shadowColor: WidgetStateProperty.all(AppTheme.ctaEntrar.withOpacity(0.4)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // CONTEÚDO: loading / erro / vazio / lista
  // ═══════════════════════════════════════════════════
  Widget _buildConteudo() {
    if (_carregando) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.ctaEntrar),
      );
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
                onPressed: _carregar,
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

    if (_aquarios.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.water_drop_outlined,
              size: 56,
              color: AppTheme.hintCampo.withOpacity(0.4),
            ),
            const SizedBox(height: 12),
            const Text(
              'Nenhum aquário cadastrado',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: AppTheme.tituloBemVindo,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Toque em "Novo" para cadastrar o primeiro',
              style: TextStyle(fontSize: 13, color: AppTheme.hintCampo),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _carregar,
      color: AppTheme.ctaEntrar,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        itemCount: _aquarios.length,
        itemBuilder: (_, i) => _buildCard(_aquarios[i]),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // CARD DO AQUÁRIO
  // ═══════════════════════════════════════════════════
  Widget _buildCard(Map<String, dynamic> aq) {
    final id = aq['id'].toString();
    final expandido = _abertos.contains(id);
    final problemas = _parametrosComAlerta(aq);
    final temAlerta = problemas.isNotEmpty;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: temAlerta ? const Color(0xFFFCE4B0) : AppTheme.bordaCard,
        ),
        boxShadow: _sombraCard,
      ),
      child: Column(
        children: [
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(15),
              onTap: () => setState(() {
                expandido ? _abertos.remove(id) : _abertos.add(id);
              }),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: AppTheme.ctaEntrar.withOpacity(0.10),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.water_drop_rounded,
                        color: AppTheme.ctaEntrar,
                        size: 20,
                      ),
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
                                  aq['nome']?.toString() ?? '—',
                                  style: const TextStyle(
                                    fontSize: 15.5,
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.tituloBemVindo,
                                  ),
                                ),
                              ),
                              if (temAlerta) ...[
                                const SizedBox(width: 8),
                                Container(
                                  width: 7,
                                  height: 7,
                                  decoration: const BoxDecoration(
                                    color: Color(0xFFF59E0B),
                                    shape: BoxShape.circle,
                                  ),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${_num(aq['volume_litros'])}L',
                            style: const TextStyle(
                              fontSize: 12.5,
                              color: AppTheme.hintCampo,
                            ),
                          ),
                        ],
                      ),
                    ),
                    _acaoIcone(
                      Icons.edit_outlined,
                      AppTheme.hintCampo,
                      () => _abrirFormulario(aquario: aq),
                    ),
                    const SizedBox(width: 4),
                    _acaoIcone(
                      Icons.delete_outline_rounded,
                      AppTheme.error,
                      () => _excluir(id, aq['nome']?.toString() ?? ''),
                    ),
                    const SizedBox(width: 4),
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
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: _paramFisico(
                          'temperatura',
                          '${_num(aq['temperatura'])}°C',
                          Icons.thermostat_rounded,
                          problemas.contains('Temperatura'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _paramFisico(
                          'ph',
                          _num(aq['ph']),
                          Icons.science_outlined,
                          problemas.contains('pH'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  _buildQuimicos(aq, problemas),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Icon(
                        Icons.event_rounded,
                        size: 15,
                        color: AppTheme.hintCampo.withOpacity(0.8),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Última manutenção: ${_formatarData(aq['ultima_manutencao'])}',
                        style: const TextStyle(fontSize: 12, color: AppTheme.hintCampo),
                      ),
                    ],
                  ),
                  if (temAlerta) ...[
                    const SizedBox(height: 12),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFF9EC),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0xFFFCE4B0)),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.warning_amber_rounded,
                            color: Color(0xFFD97706),
                            size: 17,
                          ),
                          const SizedBox(width: 9),
                          Expanded(
                            child: Text(
                              _textoAlerta(problemas),
                              style: const TextStyle(
                                fontSize: 12.5,
                                color: Color(0xFF92400E),
                                fontWeight: FontWeight.w600,
                                height: 1.3,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _acaoIcone(IconData icon, Color cor, VoidCallback onTap) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Icon(icon, color: cor, size: 20),
        ),
      ),
    );
  }

  Widget _paramFisico(String chave, String valor, IconData icon, bool alerta) {
    final info = parametrosInfo[chave]!;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
      decoration: BoxDecoration(
        color: alerta ? const Color(0xFFFFF9EC) : AppTheme.backgroundApp,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: alerta ? const Color(0xFFFCE4B0) : AppTheme.bordaCard,
        ),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            size: 17,
            color: alerta ? const Color(0xFFD97706) : AppTheme.ctaEntrar,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  info.nome,
                  style: const TextStyle(fontSize: 10.5, color: AppTheme.hintCampo),
                ),
                Text(
                  valor,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: alerta ? const Color(0xFFD97706) : AppTheme.tituloBemVindo,
                  ),
                ),
              ],
            ),
          ),
          _botaoAjuda(chave),
        ],
      ),
    );
  }

  Widget _buildQuimicos(Map<String, dynamic> aq, List<String> problemas) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      decoration: BoxDecoration(
        color: AppTheme.backgroundApp,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.bordaCard),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.biotech_outlined, size: 15, color: AppTheme.ctaEntrar),
              SizedBox(width: 6),
              Text(
                'Parâmetros Químicos',
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.tituloBemVindo,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _quimico(
                  'amonia',
                  _num(aq['amonia_ppm']),
                  problemas.contains('Amônia (NH₃)'),
                ),
              ),
              Expanded(
                child: _quimico(
                  'nitrito',
                  _num(aq['nitrito_ppm']),
                  problemas.contains('Nitrito (NO₂)'),
                ),
              ),
              Expanded(
                child: _quimico(
                  'nitrato',
                  _num(aq['nitrato_ppm']),
                  problemas.contains('Nitrato (NO₃)'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _quimico(String chave, String valor, bool alerta) {
    final nomeCurto = {
      'amonia': 'Amônia',
      'nitrito': 'Nitrito',
      'nitrato': 'Nitrato',
    }[chave]!;

    return Column(
      children: [
        Text(
          '$valor ppm',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: alerta ? const Color(0xFFD97706) : const Color(0xFF00A878),
          ),
        ),
        const SizedBox(height: 2),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              nomeCurto,
              style: const TextStyle(fontSize: 11, color: AppTheme.hintCampo),
            ),
            const SizedBox(width: 2),
            _botaoAjuda(chave, tamanho: 15),
          ],
        ),
      ],
    );
  }

  Widget _botaoAjuda(String chave, {double tamanho = 18}) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _mostrarDica(chave),
        customBorder: const CircleBorder(),
        child: Padding(
          padding: const EdgeInsets.all(3),
          child: Icon(
            Icons.help_outline_rounded,
            size: tamanho,
            color: AppTheme.ctaEntrar.withOpacity(0.75),
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// DIALOG DE DICA
// ═══════════════════════════════════════════════════════════
class _DialogDica extends StatelessWidget {
  final ParametroInfo info;
  const _DialogDica({required this.info});

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.white,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      info.nome,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.tituloBemVindo,
                      ),
                    ),
                  ),
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: () => Navigator.pop(context),
                      customBorder: const CircleBorder(),
                      child: const Padding(
                        padding: EdgeInsets.all(4),
                        child: Icon(Icons.close_rounded, color: AppTheme.error, size: 20),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFE7F8EF),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF9BDDBB)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        Icon(Icons.check_circle_rounded, size: 16, color: Color(0xFF00875A)),
                        SizedBox(width: 6),
                        Text(
                          'Faixa Ideal',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF00875A),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      info.faixaIdeal,
                      style: const TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF00694A),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              const Text(
                'O que é?',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.tituloBemVindo,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                info.oQueE,
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.black.withOpacity(0.68),
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 18),
              const Text(
                'Dicas importantes',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.tituloBemVindo,
                ),
              ),
              const SizedBox(height: 8),
              ...info.dicas.map(
                (d) => Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        margin: const EdgeInsets.only(top: 6),
                        width: 5,
                        height: 5,
                        decoration: BoxDecoration(
                          color: AppTheme.ctaEntrar.withOpacity(0.7),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          d,
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.black.withOpacity(0.68),
                            height: 1.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Entendi'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// FORMULÁRIO
// ═══════════════════════════════════════════════════════════
class _FormularioAquario extends StatefulWidget {
  final Map<String, dynamic>? aquario;
  final Future<void> Function(Map<String, dynamic>) onSalvar;
  final Function(String) onMostrarDica;

  const _FormularioAquario({
    this.aquario,
    required this.onSalvar,
    required this.onMostrarDica,
  });

  @override
  State<_FormularioAquario> createState() => _FormularioAquarioState();
}

class _FormularioAquarioState extends State<_FormularioAquario> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nomeCtrl;
  late final TextEditingController _volumeCtrl;
  late final TextEditingController _tempCtrl;
  late final TextEditingController _phCtrl;
  late final TextEditingController _amoniaCtrl;
  late final TextEditingController _nitritoCtrl;
  late final TextEditingController _nitratoCtrl;
  bool _salvando = false;

  @override
  void initState() {
    super.initState();
    final a = widget.aquario;
    _nomeCtrl    = TextEditingController(text: a?['nome']?.toString() ?? '');
    _volumeCtrl  = TextEditingController(text: a?['volume_litros']?.toString() ?? '');
    _tempCtrl    = TextEditingController(text: a?['temperatura']?.toString() ?? '');
    _phCtrl      = TextEditingController(text: a?['ph']?.toString() ?? '');
    _amoniaCtrl  = TextEditingController(text: a?['amonia_ppm']?.toString() ?? '0');
    _nitritoCtrl = TextEditingController(text: a?['nitrito_ppm']?.toString() ?? '0');
    _nitratoCtrl = TextEditingController(text: a?['nitrato_ppm']?.toString() ?? '0');
  }

  @override
  void dispose() {
    for (final c in [
      _nomeCtrl, _volumeCtrl, _tempCtrl, _phCtrl,
      _amoniaCtrl, _nitritoCtrl, _nitratoCtrl,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  double _paraDouble(String texto, [double padrao = 0]) {
    return double.tryParse(texto.trim().replaceAll(',', '.')) ?? padrao;
  }

  Future<void> _salvar() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _salvando = true);

    final dados = {
      'nome': _nomeCtrl.text.trim(),
      'volume_litros': _paraDouble(_volumeCtrl.text),
      'temperatura': _paraDouble(_tempCtrl.text),
      'ph': _paraDouble(_phCtrl.text),
      'amonia_ppm': _paraDouble(_amoniaCtrl.text),
      'nitrito_ppm': _paraDouble(_nitritoCtrl.text),
      'nitrato_ppm': _paraDouble(_nitratoCtrl.text),
    };

    Navigator.pop(context);
    await widget.onSalvar(dados);
  }

  @override
  Widget build(BuildContext context) {
    final editando = widget.aquario != null;

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.92,
      ),
      decoration: const BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      padding: EdgeInsets.only(
        left: 22,
        right: 22,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 22,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: AppTheme.bordaCampo,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      editando ? 'Editar Aquário' : 'Novo Aquário',
                      style: const TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.tituloBemVindo,
                      ),
                    ),
                  ),
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: () => Navigator.pop(context),
                      customBorder: const CircleBorder(),
                      child: const Padding(
                        padding: EdgeInsets.all(4),
                        child: Icon(Icons.close_rounded, color: AppTheme.hintCampo, size: 22),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Campos com * são obrigatórios',
                style: TextStyle(fontSize: 12, color: Colors.black.withOpacity(0.45)),
              ),
              const SizedBox(height: 20),

              _label('Nome do Aquário', obrigatorio: true),
              _campo(_nomeCtrl, 'Ex: Comunitário', obrigatorio: true),
              const SizedBox(height: 16),

              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _label('Volume (Litros)', obrigatorio: true),
                        _campo(_volumeCtrl, 'Ex: 100', numero: true, obrigatorio: true),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _label('Temperatura (°C)', obrigatorio: true, ajuda: 'temperatura'),
                        _campo(_tempCtrl, 'Ex: 26', numero: true, obrigatorio: true),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              _label('pH', obrigatorio: true, ajuda: 'ph'),
              _campo(_phCtrl, 'Ex: 7.0', numero: true, obrigatorio: true),
              const SizedBox(height: 20),

              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.backgroundApp,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.bordaCard),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Parâmetros químicos (opcional)',
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.tituloBemVindo,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Deixe em branco se ainda não testou',
                      style: TextStyle(fontSize: 11.5, color: Colors.black.withOpacity(0.45)),
                    ),
                    const SizedBox(height: 14),
                    _label('Amônia (ppm)', ajuda: 'amonia'),
                    _campo(_amoniaCtrl, '0', numero: true),
                    const SizedBox(height: 12),
                    _label('Nitrito (ppm)', ajuda: 'nitrito'),
                    _campo(_nitritoCtrl, '0', numero: true),
                    const SizedBox(height: 12),
                    _label('Nitrato (ppm)', ajuda: 'nitrato'),
                    _campo(_nitratoCtrl, '0', numero: true),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              ElevatedButton(
                onPressed: _salvando ? null : _salvar,
                child: _salvando
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          color: AppTheme.white,
                          strokeWidth: 2,
                        ),
                      )
                    : Text(editando ? 'Salvar Alterações' : 'Criar Aquário'),
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

  Widget _label(String texto, {bool obrigatorio = false, String? ajuda}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          RichText(
            text: TextSpan(
              text: texto,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppTheme.labelCampo,
              ),
              children: obrigatorio
                  ? const [
                      TextSpan(
                        text: ' *',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.error,
                        ),
                      ),
                    ]
                  : null,
            ),
          ),
          if (ajuda != null) ...[
            const SizedBox(width: 4),
            Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => widget.onMostrarDica(ajuda),
                customBorder: const CircleBorder(),
                child: Padding(
                  padding: const EdgeInsets.all(3),
                  child: Icon(
                    Icons.help_outline_rounded,
                    size: 16,
                    color: AppTheme.ctaEntrar.withOpacity(0.75),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _campo(
    TextEditingController ctrl,
    String hint, {
    bool numero = false,
    bool obrigatorio = false,
  }) {
    return TextFormField(
      controller: ctrl,
      keyboardType: numero
          ? const TextInputType.numberWithOptions(decimal: true)
          : TextInputType.text,
      style: const TextStyle(fontSize: 14, color: AppTheme.textDark),
      decoration: InputDecoration(hintText: hint),
      validator: obrigatorio
          ? (v) => (v == null || v.trim().isEmpty) ? 'Campo obrigatório' : null
          : null,
    );
  }
}