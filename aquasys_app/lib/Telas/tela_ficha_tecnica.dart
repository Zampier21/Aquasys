import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../Services/ficha_service.dart';
import '../widgets/escolha_cliente.dart';

class TelaFichaTecnica extends StatefulWidget {
  final String? fichaId;

  const TelaFichaTecnica({super.key, this.fichaId});

  @override
  State<TelaFichaTecnica> createState() => _TelaFichaTecnicaState();
}

/// Maquinário do check-list.
class _Equipamento {
  final String nome;
  bool presente;

  _Equipamento(this.nome, {this.presente = false});
}

class _Teste {
  final String codigo;
  final String rotulo;
  final String unidade;
  bool marcado;
  final TextEditingController valor;

  _Teste({
    required this.codigo,
    required this.rotulo,
    this.unidade = '',
    this.marcado = false,
    String valorInicial = '',
  }) : valor = TextEditingController(text: valorInicial);
}

class _TelaFichaTecnicaState extends State<TelaFichaTecnica>
    with SingleTickerProviderStateMixin {
  late final TabController _abas;

  // ─── Informações do atendimento ────────────────────
  final _empresa = TextEditingController();
  final _chegada = TextEditingController();
  final _saida = TextEditingController();
  final _nomeCliente = TextEditingController();
  final _litros = TextEditingController();
  DateTime? _data;
  String? _tipoInstalacao; // aquario | lago

  /// Cliente escolhido do cadastro. Nulo enquanto ninguém foi escolhido.
  Map<String, dynamic>? _cliente;
  bool? _aguaDoce;         // true = doce, false = marinho

  // ─── Check-list e testes ───────────────────────────
  List<_Equipamento> _equipamentos = [];
  List<_Teste> _testes = [];
  bool _equipamentosAberto = true;
  bool _testesAberto = true;

  // ─── Descrição ─────────────────────────────────────
  bool? _chaoMolhado;
  bool? _conferido2x;
  bool? _stabilityAplicado;
  final _itensDeixados = TextEditingController();
  final _descricaoLivre = TextEditingController();

  final _chaveForm = GlobalKey<FormState>();
  bool _carregando = true;
  bool _salvando = false;

  @override
  void initState() {
    super.initState();
    _abas = TabController(length: 4, vsync: this);
    _abas.addListener(() => setState(() {}));
    _carregarDados();
  }

  @override
  void dispose() {
    _abas.dispose();
    for (final c in [
      _empresa,
      _chegada,
      _saida,
      _nomeCliente,
      _litros,
      _itensDeixados,
      _descricaoLivre,
    ]) {
      c.dispose();
    }
    for (final t in _testes) {
      t.valor.dispose();
    }
    super.dispose();
  }

  // ═══════════════════════════════════════════════════
  // CARGA INICIAL
  // ═══════════════════════════════════════════════════
  Future<void> _carregarDados() async {
    final catalogos = await FichaService.catalogos();
    if (!mounted) return;

    if (catalogos['sucesso'] == true) {
      _equipamentos = (catalogos['maquinarios'] as List<String>)
          .map((n) => _Equipamento(n))
          .toList();
      _testes = (catalogos['testes'] as List<Map<String, dynamic>>)
          .map((t) => _Teste(
                codigo: t['parametro'],
                rotulo: t['rotulo'] ?? t['parametro'],
                unidade: t['unidade'] ?? '',
              ))
          .toList();
    }

    if (widget.fichaId != null) {
      final resultado = await FichaService.detalhar(widget.fichaId!);
      if (!mounted) return;
      if (resultado['sucesso'] == true) {
        _preencher(resultado['dados'] as Map<String, dynamic>);
      }
    }

    setState(() => _carregando = false);
  }

  void _preencher(Map<String, dynamic> ficha) {
    _empresa.text = ficha['nome_empresa'] ?? '';
    _nomeCliente.text = ficha['nome_cliente'] ?? '';
    if (ficha['cliente_id'] != null) {
      _cliente = {'id': ficha['cliente_id'], 'nome': ficha['nome_cliente']};
    }
    _chegada.text = ficha['horario_chegada'] ?? '';
    _saida.text = ficha['horario_saida'] ?? '';
    _litros.text =
        ficha['volume_litros'] == null ? '' : '${ficha['volume_litros']}';
    _tipoInstalacao = ficha['tipo_instalacao'];
    _aguaDoce = ficha['agua_doce'];

    final data = ficha['data_atendimento'] as String?;
    if (data != null) _data = DateTime.tryParse(data);

    final descricao = ficha['descricao'] as Map<String, dynamic>?;
    if (descricao != null) {
      _chaoMolhado = descricao['chao_malhado'];
      _conferido2x = descricao['conferido_2x'];
      _stabilityAplicado = descricao['stability_aplicado'];
      _itensDeixados.text = descricao['itens_deixados'] ?? '';
      _descricaoLivre.text = descricao['descricao_livre'] ?? '';
    }

    _mesclarEquipamentos(ficha['equipamentos']);
    _mesclarTestes(ficha['testes']);
  }

  void _mesclarEquipamentos(dynamic salvos) {
    if (salvos is! List) return;
    final porNome = {for (final e in _equipamentos) e.nome: e};

    for (final salvo in salvos) {
      final nome = salvo['equipamento'] as String;
      final item = porNome.putIfAbsent(nome, () => _Equipamento(nome));
      item.presente = salvo['presente'] == true;
    }
    _equipamentos = porNome.values.toList();
  }

  void _mesclarTestes(dynamic salvos) {
    if (salvos is! List) return;
    final porCodigo = {for (final t in _testes) t.codigo: t};

    for (final salvo in salvos) {
      final codigo = salvo['parametro'] as String;
      final existente = porCodigo[codigo];
      final valor = salvo['valor'];

      if (existente != null) {
        existente.marcado = true;
        existente.valor.text = valor == null ? '' : '$valor';
      } else {
        // Teste personalizado: não está no catálogo padrão.
        porCodigo[codigo] = _Teste(
          codigo: codigo,
          rotulo: codigo,
          unidade: salvo['unidade'] ?? '',
          marcado: true,
          valorInicial: valor == null ? '' : '$valor',
        );
      }
    }
    _testes = porCodigo.values.toList();
  }

  // ═══════════════════════════════════════════════════
  // SALVAR
  // ═══════════════════════════════════════════════════
  Future<void> _salvar() async {
    if (!_chaveForm.currentState!.validate()) {
      // Os campos obrigatórios estão na primeira aba.
      _abas.animateTo(0);
      return;
    }

    setState(() => _salvando = true);

    final corpo = <String, dynamic>{
      'cliente_id': ?_cliente?['id'],
      'nome_cliente': _nomeCliente.text.trim(),
      'nome_empresa': _vazioParaNulo(_empresa.text),
      'data_atendimento': _data?.toIso8601String().substring(0, 10),
      'horario_chegada': _vazioParaNulo(_chegada.text),
      'horario_saida': _vazioParaNulo(_saida.text),
      'tipo_instalacao': _tipoInstalacao,
      'volume_litros': int.tryParse(_litros.text.trim()),
      'agua_doce': _aguaDoce,
      'equipamentos': [
        for (final e in _equipamentos)
          {'equipamento': e.nome, 'presente': e.presente},
      ],
      // Só sobe teste marcado — o banco guarda medição, não a lista toda.
      'testes': [
        for (final t in _testes)
          if (t.marcado)
            {
              'parametro': t.codigo,
              'valor': double.tryParse(t.valor.text.replaceAll(',', '.')),
              'unidade': t.unidade.isEmpty ? null : t.unidade,
            },
      ],
      'descricao': {
        'chao_malhado': _chaoMolhado,
        'conferido_2x': _conferido2x,
        'stability_aplicado': _stabilityAplicado,
        'itens_deixados': _vazioParaNulo(_itensDeixados.text),
        'descricao_livre': _vazioParaNulo(_descricaoLivre.text),
      },
    };

    final resultado = widget.fichaId == null
        ? await FichaService.criar(corpo)
        : await FichaService.editar(widget.fichaId!, corpo);

    if (!mounted) return;
    setState(() => _salvando = false);

    if (resultado['sucesso'] == true) {
      Navigator.pop(context, true);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(resultado['erro']),
          backgroundColor: AppTheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  String? _vazioParaNulo(String texto) =>
      texto.trim().isEmpty ? null : texto.trim();

  // ═══════════════════════════════════════════════════
  // BUILD
  // ═══════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    final ultimaAba = _abas.index == 3;

    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_rounded,
                        color: AppTheme.azulMedio),
                    onPressed: () => Navigator.pop(context),
                  ),
                  const Expanded(
                    child: BarraSecao(
                      titulo: 'Ficha técnica',
                      centralizado: true,
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _carregando
                  ? const Center(
                      child: CircularProgressIndicator(color: AppTheme.primaria),
                    )
                  : Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Container(
                        decoration: BoxDecoration(
                          color: AppTheme.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppTheme.bordaCampo),
                          boxShadow: AppTheme.sombraCard,
                        ),
                        child: Column(
                          children: [
                            _buildAbas(),
                            Expanded(
                              child: Form(
                                key: _chaveForm,
                                child: TabBarView(
                                  controller: _abas,
                                  children: [
                                    _abaAtendimento(),
                                    _abaChecklist(),
                                    _abaTestes(),
                                    _abaDescricao(),
                                  ],
                                ),
                              ),
                            ),
                            _buildBotoes(ultimaAba),
                          ],
                        ),
                      ),
                    ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildAbas() {
    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppTheme.bordaCard)),
      ),
      child: TabBar(
        controller: _abas,
        isScrollable: true,
        tabAlignment: TabAlignment.start,
        labelColor: AppTheme.primaria,
        unselectedLabelColor: AppTheme.textoFraco,
        indicatorColor: AppTheme.primaria,
        indicatorWeight: 2.5,
        dividerColor: Colors.transparent,
        labelStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
        unselectedLabelStyle: const TextStyle(fontSize: 12.5),
        tabs: const [
          Tab(text: 'Informações do\natendimento', height: 52),
          Tab(text: 'Check-List', height: 52),
          Tab(text: 'Testes de\nágua', height: 52),
          Tab(text: 'Descrição', height: 52),
        ],
      ),
    );
  }

  Widget _buildBotoes(bool ultimaAba) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      child: Column(
        children: [
          ElevatedButton(
            onPressed: _salvando
                ? null
                : ultimaAba
                    ? _salvar
                    : () => _abas.animateTo(_abas.index + 1),
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 48),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: _salvando
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(
                      color: AppTheme.white,
                      strokeWidth: 2,
                    ),
                  )
                : Text(ultimaAba ? 'Salvar ficha' : 'Avançar'),
          ),
          const SizedBox(height: 10),
          BotaoCancelar(
            onPressed: _salvando ? null : () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ABA 1 — INFORMAÇÕES DO ATENDIMENTO
  // ═══════════════════════════════════════════════════
  Widget _abaAtendimento() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
      children: [
        _campo(_empresa, 'Nome da empresa'),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _campo(_chegada, 'Horário de chegada')),
            const SizedBox(width: 10),
            Expanded(child: _campo(_saida, 'Horário de saída')),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _seletorData()),
            const SizedBox(width: 10),
            Expanded(
              child: _seletor<String>(
                rotulo: 'Aquário ou lago',
                valor: _tipoInstalacao,
                opcoes: const {'aquario': 'Aquário', 'lago': 'Lago'},
                aoMudar: (v) => setState(() => _tipoInstalacao = v),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _seletorCliente(),
        const SizedBox(height: 12),
        _campo(
          _litros,
          'Quantos Litros?',
          teclado: TextInputType.number,
          validador: (v) {
            if (v == null || v.trim().isEmpty) return null;
            final n = int.tryParse(v.trim());
            if (n == null) return 'Use só números inteiros';
            if (n <= 0) return 'O volume tem de ser maior que zero';
            return null;
          },
        ),
        const SizedBox(height: 12),
        _seletor<bool>(
          rotulo: 'Água doce ou marinho?',
          valor: _aguaDoce,
          opcoes: const {true: 'Água doce', false: 'Marinho'},
          aoMudar: (v) => setState(() => _aguaDoce = v),
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════
  // ABA 2 — CHECK-LIST
  // ═══════════════════════════════════════════════════
  Widget _abaChecklist() {
    return _blocoRecolhivel(
      titulo: 'Maquinários de aquário ou lago',
      aberto: _equipamentosAberto,
      alternar: () =>
          setState(() => _equipamentosAberto = !_equipamentosAberto),
      filhos: [
        for (final e in _equipamentos)
          Row(
            children: [
              Checkbox(
                value: e.presente,
                activeColor: AppTheme.primaria,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(4),
                ),
                side: const BorderSide(color: AppTheme.bordaCampo, width: 1.5),
                onChanged: (v) => setState(() => e.presente = v ?? false),
              ),
              Expanded(
                child: Text(
                  e.nome,
                  style: const TextStyle(
                    fontSize: 13.5,
                    color: AppTheme.azulEscuro,
                  ),
                ),
              ),
            ],
          ),
      ],
      aoAdicionar: (nome) => setState(
        () => _equipamentos.add(_Equipamento(nome, presente: true)),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ABA 3 — TESTES DE ÁGUA
  // ═══════════════════════════════════════════════════
  Widget _abaTestes() {
    return _blocoRecolhivel(
      titulo: 'Testes de água',
      aberto: _testesAberto,
      alternar: () => setState(() => _testesAberto = !_testesAberto),
      filhos: [
        for (final t in _testes) ...[
          Row(
            children: [
              Checkbox(
                value: t.marcado,
                activeColor: AppTheme.primaria,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(4),
                ),
                side: const BorderSide(color: AppTheme.bordaCampo, width: 1.5),
                onChanged: (v) => setState(() => t.marcado = v ?? false),
              ),
              Expanded(
                child: Text(
                  t.rotulo,
                  style: const TextStyle(
                    fontSize: 13.5,
                    color: AppTheme.azulEscuro,
                  ),
                ),
              ),
            ],
          ),
          // Teste marcado ganha o campo do valor medido.
          if (t.marcado)
            Padding(
              padding: const EdgeInsets.only(left: 44, bottom: 10),
              child: TextFormField(
                controller: t.valor,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                style:
                    const TextStyle(fontSize: 13, color: AppTheme.azulEscuro),
                decoration: InputDecoration(
                  hintText: 'Valor medido',
                  suffixText: t.unidade.isEmpty ? null : t.unidade,
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 10),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null;
                  return double.tryParse(v.replaceAll(',', '.')) == null
                      ? 'Valor numérico'
                      : null;
                },
              ),
            ),
        ],
      ],
      aoAdicionar: (nome) => setState(
        () => _testes.add(_Teste(codigo: nome, rotulo: nome, marcado: true)),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ABA 4 — DESCRIÇÃO
  // ═══════════════════════════════════════════════════
  Widget _abaDescricao() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
      children: [
        _perguntaSimNao(
          'O chão está molhado?',
          _chaoMolhado,
          (v) => setState(() => _chaoMolhado = v),
        ),
        _perguntaSimNao(
          'Conferiu os itens 2x?',
          _conferido2x,
          (v) => setState(() => _conferido2x = v),
        ),
        _perguntaSimNao(
          'Foi dosado stability e stress guard?',
          _stabilityAplicado,
          (v) => setState(() => _stabilityAplicado = v),
        ),
        _perguntaTexto(
          'Foi deixado algo?',
          _itensDeixados,
          'Ex: foi deixado o termostato reserva',
        ),
        _perguntaTexto(
          'Descreva o que você fez',
          _descricaoLivre,
          'Ex: limpeza dos vidros e troca parcial de água',
          linhas: 4,
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════
  // COMPONENTES
  // ═══════════════════════════════════════════════════
  Widget _campo(
    TextEditingController controlador,
    String dica, {
    TextInputType teclado = TextInputType.text,
    String? Function(String?)? validador,
  }) {
    return TextFormField(
      controller: controlador,
      keyboardType: teclado,
      validator: validador,
      style: const TextStyle(fontSize: 14, color: AppTheme.azulEscuro),
      decoration: InputDecoration(
        hintText: dica,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      ),
    );
  }

  Widget _seletorCliente() {
    final escolhido = _cliente != null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InkWell(
          onTap: _abrirEscolhaCliente,
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(
              color: AppTheme.backgroundLabel,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: escolhido ? AppTheme.primaria : AppTheme.bordaCampo,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  escolhido ? Icons.person_rounded : Icons.person_search_rounded,
                  size: 19,
                  color: escolhido ? AppTheme.primaria : AppTheme.textoFraco,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    escolhido ? '${_cliente!['nome']}' : 'Escolher cliente',
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight:
                          escolhido ? FontWeight.w600 : FontWeight.w400,
                      color: escolhido
                          ? AppTheme.azulEscuro
                          : AppTheme.textoFraco,
                    ),
                  ),
                ),
                const Icon(Icons.keyboard_arrow_down_rounded,
                    color: AppTheme.textoFraco),
              ],
            ),
          ),
        ),
        if (!escolhido)
          const Padding(
            padding: EdgeInsets.only(top: 6, left: 2),
            child: Text(
              'Na primeira visita você cadastra; nas próximas é só escolher.',
              style: TextStyle(fontSize: 11.5, color: AppTheme.textoFraco),
            ),
          ),
      ],
    );
  }

  /// Preenche a ficha com o que veio do cadastro.
  void _usarCliente(Map<String, dynamic> cliente) {
    setState(() {
      _cliente = cliente;
      _nomeCliente.text = '${cliente['nome']}';
      _tipoInstalacao = cliente['tipo_instalacao'] ?? _tipoInstalacao;
      _aguaDoce = cliente['agua_doce'] as bool? ?? _aguaDoce;
      if (cliente['volume_litros'] != null) {
        _litros.text = '${cliente['volume_litros']}';
      }
    });
  }

  void _abrirEscolhaCliente() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => EscolhaCliente(
        aoEscolher: (cliente) {
          Navigator.pop(context);
          _usarCliente(cliente);
        },
      ),
    );
  }

  Widget _seletorData() {
    final texto = _data == null
        ? 'Incluir data'
        : '${_data!.day.toString().padLeft(2, '0')}/'
            '${_data!.month.toString().padLeft(2, '0')}/${_data!.year}';

    return InkWell(
      onTap: () async {
        final escolhida = await showDatePicker(
          context: context,
          initialDate: _data ?? DateTime.now(),
          firstDate: DateTime(2020),
          lastDate: DateTime(2100),
        );
        if (escolhida != null) setState(() => _data = escolhida);
      },
      borderRadius: BorderRadius.circular(10),
      child: Container(
        height: 52,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: AppTheme.backgroundLabel,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppTheme.bordaCampo),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                texto,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 13,
                  color: _data == null
                      ? AppTheme.textoFraco
                      : AppTheme.azulEscuro,
                ),
              ),
            ),
            const Icon(Icons.calendar_today_rounded,
                size: 16, color: AppTheme.textoFraco),
          ],
        ),
      ),
    );
  }

  Widget _seletor<T>({
    required String rotulo,
    required T? valor,
    required Map<T, String> opcoes,
    required ValueChanged<T?> aoMudar,
  }) {
    return DropdownButtonFormField<T>(
      initialValue: valor,
      isExpanded: true,
      style: const TextStyle(fontSize: 13, color: AppTheme.azulEscuro),
      decoration: const InputDecoration(
        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      ),
      hint: Text(
        rotulo,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 13, color: AppTheme.textoFraco),
      ),
      items: [
        for (final entrada in opcoes.entries)
          DropdownMenuItem(value: entrada.key, child: Text(entrada.value)),
      ],
      onChanged: aoMudar,
    );
  }

  Widget _perguntaSimNao(
    String pergunta,
    bool? valor,
    ValueChanged<bool?> aoMudar,
  ) {
    Widget opcao(String texto, bool alvo) {
      final ativo = valor == alvo;
      return Expanded(
        child: InkWell(
          // Tocar de novo na opção ativa limpa a resposta.
          onTap: () => aoMudar(ativo ? null : alvo),
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 11),
            decoration: BoxDecoration(
              color: ativo ? AppTheme.primaria : AppTheme.backgroundLabel,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: ativo ? AppTheme.primaria : AppTheme.bordaCampo,
              ),
            ),
            child: Center(
              child: Text(
                texto,
                style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                  color: ativo ? AppTheme.white : AppTheme.textoFraco,
                ),
              ),
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            pergunta,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.azulEscuro,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              opcao('Sim', true),
              const SizedBox(width: 10),
              opcao('Não', false),
            ],
          ),
        ],
      ),
    );
  }

  Widget _perguntaTexto(
    String pergunta,
    TextEditingController controlador,
    String dica, {
    int linhas = 1,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            pergunta,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.azulEscuro,
            ),
          ),
          const SizedBox(height: 6),
          TextFormField(
            controller: controlador,
            maxLines: linhas,
            style: const TextStyle(fontSize: 14, color: AppTheme.azulEscuro),
            decoration: InputDecoration(
              hintText: dica,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            ),
          ),
        ],
      ),
    );
  }

  /// Bloco recolhível com os itens marcáveis e o botão "Adicionar".
  Widget _blocoRecolhivel({
    required String titulo,
    required bool aberto,
    required VoidCallback alternar,
    required List<Widget> filhos,
    required ValueChanged<String> aoAdicionar,
  }) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
      children: [
        InkWell(
          onTap: alternar,
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(
              color: AppTheme.backgroundLabel,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.bordaCampo),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    titulo,
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppTheme.textoFraco,
                    ),
                  ),
                ),
                Icon(
                  aberto
                      ? Icons.keyboard_arrow_up_rounded
                      : Icons.keyboard_arrow_down_rounded,
                  color: AppTheme.textoFraco,
                ),
              ],
            ),
          ),
        ),
        if (aberto) ...[
          const SizedBox(height: 6),
          ...filhos,
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: ElevatedButton.icon(
              onPressed: () => _abrirAdicionarItem(titulo, aoAdicionar),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text('Adicionar'),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(0, 38),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                textStyle: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }

  void _abrirAdicionarItem(String titulo, ValueChanged<String> aoAdicionar) {
    final controlador = TextEditingController();

    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Adicionar em $titulo',
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: TextField(
          controller: controlador,
          autofocus: true,
          decoration: const InputDecoration(hintText: 'Nome do item'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto),
            child: const Text('Cancelar',
                style: TextStyle(color: AppTheme.textoFraco)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(minimumSize: const Size(120, 44)),
            onPressed: () {
              final nome = controlador.text.trim();
              if (nome.isEmpty) return;
              Navigator.pop(contexto);
              aoAdicionar(nome);
            },
            child: const Text('Adicionar'),
          ),
        ],
      ),
    );
  }
}
