import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../Services/peixe_service.dart';
import '../Tema/app_tema.dart';

/// Revisão das fichas que a importação deixou pela metade.
///
/// A importação cria a espécie e a FishBase preenche o que é medida:
/// porte, tipo de água, pH e dureza. Temperamento, agrupamento e a
/// faixa de temperatura não vêm de base nenhuma, e é aqui que a loja os
/// informa.
///
/// A tela tem duas partes: a fila do que falta revisar e o formulário de
/// uma ficha. Enquanto a ficha não fecha, o botão de conferir fica
/// desligado e diz o que ainda falta, em vez de deixar marcar e receber
/// a recusa do servidor.
class TelaRevisarEspecies extends StatefulWidget {
  const TelaRevisarEspecies({super.key});

  @override
  State<TelaRevisarEspecies> createState() => _TelaRevisarEspeciesState();
}

class _TelaRevisarEspeciesState extends State<TelaRevisarEspecies> {
  List<Map<String, dynamic>> _fila = [];
  bool _carregando = true;
  String? _erro;

  // Ficha aberta no formulário. Nulo mostra a fila.
  Map<String, dynamic>? _aberta;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    final r = await PeixeService.incompletas();
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (r['sucesso'] == true) {
        _fila = (r['dados'] as List).cast<Map<String, dynamic>>();
      } else {
        _erro = r['erro'] as String?;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      appBar: AppBar(
        backgroundColor: AppTheme.white,
        surfaceTintColor: AppTheme.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppTheme.azulEscuro),
        title: Text(
          _aberta == null ? 'Fichas a revisar' : _aberta!['nome_comum'],
          style: const TextStyle(
            color: AppTheme.azulEscuro,
            fontSize: 17,
            fontWeight: FontWeight.w700,
          ),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () {
            if (_aberta == null) {
              Navigator.pop(context);
            } else {
              setState(() => _aberta = null);
            }
          },
        ),
      ),
      body: _conteudo(),
    );
  }

  Widget _conteudo() {
    if (_aberta != null) {
      return _Formulario(
        especie: _aberta!,
        aoGravar: (fechou) async {
          await _carregar();
          if (!mounted) return;
          setState(() => _aberta = null);
          _avisar(
            fechou
                ? 'Ficha conferida. O motor já pode liberar esta espécie.'
                : 'Alterações salvas. A ficha continua a revisar.',
            fechou ? AppTheme.sucesso : AppTheme.primaria,
          );
        },
      );
    }

    if (_carregando) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaria),
      );
    }

    if (_erro != null) {
      return _Recado(
        icone: Icons.cloud_off_rounded,
        cor: AppTheme.error,
        titulo: 'Não foi possível carregar',
        texto: _erro!,
        acao: _carregar,
      );
    }

    if (_fila.isEmpty) {
      return const _Recado(
        icone: Icons.check_circle_outline_rounded,
        cor: AppTheme.sucesso,
        titulo: 'Nada a revisar',
        texto: 'Todas as espécies do seu catálogo estão com a ficha '
            'conferida. Fichas incompletas aparecem aqui depois de uma '
            'importação de lista.',
      );
    }

    return RefreshIndicator(
      onRefresh: _carregar,
      color: AppTheme.primaria,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        children: [
          _explicacao(),
          const SizedBox(height: 16),
          for (final e in _fila) ...[
            _cartao(e),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }

  Widget _explicacao() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.alertaFundo,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.alertaBorda),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline_rounded,
              size: 19, color: AppTheme.alerta),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              '${_fila.length} ${_fila.length == 1 ? "espécie" : "espécies"} '
              'com ficha incompleta. Enquanto estiverem assim, a análise de '
              'compatibilidade pede confirmação em vez de liberar, porque '
              'temperamento e porte são o que ela usa para decidir.',
              style: const TextStyle(
                fontSize: 12.5,
                color: AppTheme.alertaTexto,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _cartao(Map<String, dynamic> e) {
    final faltam = (e['faltam'] as List).cast<String>();
    final cientifico = e['nome_cientifico'] as String?;

    return Material(
      color: AppTheme.backgroundCard,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => setState(() => _aberta = e),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.bordaCard),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      e['nome_comum'] as String,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.azulEscuro,
                      ),
                    ),
                    if (cientifico != null && cientifico.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        cientifico,
                        style: const TextStyle(
                          fontSize: 12.5,
                          fontStyle: FontStyle.italic,
                          color: AppTheme.textoFraco,
                        ),
                      ),
                    ],
                    const SizedBox(height: 8),
                    Text(
                      'Falta: ${faltam.join(", ")}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppTheme.alertaTexto,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.alertaFundo,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppTheme.alertaBorda),
                ),
                child: Text(
                  '${faltam.length}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.alertaTexto,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _avisar(String texto, Color cor) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(texto),
        backgroundColor: cor,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════
// FORMULÁRIO DE UMA FICHA
// ═══════════════════════════════════════════════════════
/// Os rótulos vêm da API, em `faltam`, e são os mesmos que o motor de
/// compatibilidade usa. Esta tabela liga cada rótulo ao campo do
/// formulário, para que o aviso de "falta preencher X" aponte para o
/// campo certo sem a tela ter uma segunda lista própria.
const Map<String, String> _campoPorRotulo = {
  'tipo de água': 'tipo_agua',
  'temperatura mínima': 'temp_min',
  'temperatura máxima': 'temp_max',
  'pH mínimo': 'ph_min',
  'pH máximo': 'ph_max',
  'tamanho adulto': 'tamanho_adulto_cm',
  'volume mínimo': 'volume_minimo_l',
  'temperamento': 'comportamento',
  'agrupamento': 'agrupamento',
  'nível de natação': 'nivel_natacao',
  'alimentação': 'alimentacao',
  'cardume mínimo': 'cardume_minimo',
};

const Map<String, String> _rotuloComportamento = {
  'pacifico': 'Pacífico',
  'semi_agressivo': 'Semiagressivo',
  'territorial': 'Territorial',
  'agressivo': 'Agressivo',
};

const Map<String, String> _rotuloAgrupamento = {
  'cardume': 'Cardume',
  'par': 'Casal',
  'harem': 'Harém',
  'solitario': 'Solitário',
};

const Map<String, String> _rotuloNatacao = {
  'fundo': 'Fundo',
  'meio': 'Meio',
  'superficie': 'Superfície',
  'todos': 'Todos os níveis',
};

const Map<String, String> _rotuloAgua = {
  'doce': 'Doce',
  'salobra': 'Salobra',
  'marinho': 'Marinho',
};

const Map<String, String> _rotuloAlimentacao = {
  'herbivoro': 'Herbívoro',
  'carnivoro': 'Carnívoro',
  'onivoro': 'Onívoro',
  'limnivoro': 'Limnívoro',
};

class _Formulario extends StatefulWidget {
  const _Formulario({required this.especie, required this.aoGravar});

  final Map<String, dynamic> especie;
  final Future<void> Function(bool fechou) aoGravar;

  @override
  State<_Formulario> createState() => _FormularioState();
}

class _FormularioState extends State<_Formulario> {
  final _numeros = <String, TextEditingController>{};
  final _escolhas = <String, String?>{};
  // Quando a lista da loja traz o nome científico, a espécie nasce com
  // o nome popular da FishBase, que é em inglês. Dar onde trocar é o
  // mínimo: é esse nome que o cliente da loja vê na aba de peixes.
  final _nome = TextEditingController();

  bool _gravando = false;
  bool _carregando = true;
  String? _erro;

  /// Rótulos que ainda faltam, recalculados a cada digitação.
  late Set<String> _pendentes;

  /// A ficha como está gravada hoje, buscada ao abrir.
  ///
  /// A fila de revisão só diz o que falta; os campos que a FishBase já
  /// preencheu vêm daqui. Sem isto o formulário abriria com o pH e o
  /// porte em branco, e a loja digitaria por cima do que já estava
  /// certo, ou pensaria que ainda falta.
  Map<String, dynamic> _ficha = const {};

  static const _camposNumericos = {
    'temp_min': ('Temperatura mínima', '°C'),
    'temp_max': ('Temperatura máxima', '°C'),
    'ph_min': ('pH mínimo', ''),
    'ph_max': ('pH máximo', ''),
    'tamanho_adulto_cm': ('Tamanho adulto', 'cm'),
    'volume_minimo_l': ('Volume mínimo', 'L'),
    'cardume_minimo': ('Cardume mínimo', 'peixes'),
  };

  @override
  void initState() {
    super.initState();

    for (final campo in _camposNumericos.keys) {
      _numeros[campo] = TextEditingController()
        ..addListener(_recalcular);
    }
    _pendentes = (widget.especie['faltam'] as List).cast<String>().toSet();
    _buscarFicha();
  }

  Future<void> _buscarFicha() async {
    final r = await PeixeService.detalhar(widget.especie['id'] as String);
    if (!mounted) return;

    if (r['sucesso'] != true) {
      setState(() {
        _carregando = false;
        _erro = r['erro'] as String?;
      });
      return;
    }

    final ficha = r['dados'] as Map<String, dynamic>;

    _nome.text = (ficha['nome_comum'] ?? '').toString();

    for (final campo in _camposNumericos.keys) {
      final valor = ficha[campo];
      if (valor != null) _numeros[campo]!.text = _texto(valor);
    }
    for (final campo in const ['tipo_agua', 'comportamento', 'agrupamento',
                               'nivel_natacao', 'alimentacao']) {
      final valor = ficha[campo];
      if (valor != null) _escolhas[campo] = valor.toString();
    }

    setState(() {
      _carregando = false;
      _ficha = ficha;
    });
    _recalcular();
  }

  /// Número sem o `.0` pendurado: 60.0 vira "60", 6.5 continua "6.5".
  static String _texto(Object valor) {
    if (valor is num && valor == valor.roundToDouble()) {
      return valor.toInt().toString();
    }
    return valor.toString();
  }

  @override
  void dispose() {
    for (final c in _numeros.values) {
      c.dispose();
    }
    _nome.dispose();
    super.dispose();
  }

  /// O que falta, do ponto de vista da tela.
  ///
  /// Começa do que a API disse e vai riscando conforme a loja preenche.
  /// A regra do cardume é a mesma do servidor: só é exigido de quem vive
  /// em cardume, senão a ficha de um peixe solitário nunca fecharia.
  void _recalcular() {
    final faltam = <String>{};

    for (final rotulo in (widget.especie['faltam'] as List).cast<String>()) {
      final campo = _campoPorRotulo[rotulo];
      if (campo == null) continue;
      if (_valorDe(campo) == null) faltam.add(rotulo);
    }

    final agrupamento = _escolhas['agrupamento'];
    if (agrupamento == 'cardume' && _valorDe('cardume_minimo') == null) {
      faltam.add('cardume mínimo');
    } else {
      faltam.remove('cardume mínimo');
    }

    if (!mounted) return;
    setState(() => _pendentes = faltam);
  }

  Object? _valorDe(String campo) {
    if (_escolhas.containsKey(campo)) return _escolhas[campo];
    // Campo que a ficha já tem e esta tela não edita continua valendo:
    // é o caso da dureza, que a FishBase preenche e não entra aqui.
    if (_ficha[campo] != null && !_numeros.containsKey(campo)) {
      return _ficha[campo];
    }

    final texto = _numeros[campo]?.text.trim().replaceAll(',', '.');
    if (texto == null || texto.isEmpty) return null;

    if (campo == 'volume_minimo_l' || campo == 'cardume_minimo') {
      return int.tryParse(texto);
    }
    return double.tryParse(texto);
  }

  Map<String, dynamic> _corpo() {
    final dados = <String, dynamic>{};
    for (final campo in [..._camposNumericos.keys, ..._escolhas.keys]) {
      final valor = _valorDe(campo);
      if (valor != null) dados[campo] = valor;
    }

    // Só vai quando mudou de fato, e nunca em branco: o nome é
    // obrigatório na tabela.
    final nome = _nome.text.trim();
    if (nome.isNotEmpty && nome != _ficha['nome_comum']) {
      dados['nome_comum'] = nome;
    }
    return dados;
  }

  Future<void> _gravar({required bool fechar}) async {
    setState(() {
      _gravando = true;
      _erro = null;
    });

    final corpo = _corpo();
    if (fechar) corpo['revisada'] = true;

    final r = await PeixeService.revisar(
      widget.especie['id'] as String,
      corpo,
    );
    if (!mounted) return;

    if (r['sucesso'] == true) {
      await widget.aoGravar(fechar);
      return;
    }

    setState(() {
      _gravando = false;
      _erro = r['erro'] as String?;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_carregando) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaria),
      );
    }

    final cientifico = widget.especie['nome_cientifico'] as String?;
    final fonte = widget.especie['fonte_dados'] as String?;
    final clima = widget.especie['clima'] as String?;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
      children: [
        if (cientifico != null && cientifico.isNotEmpty)
          Text(
            cientifico,
            style: const TextStyle(
              fontSize: 13.5,
              fontStyle: FontStyle.italic,
              color: AppTheme.textoFraco,
            ),
          ),

        if (fonte != null && fonte.isNotEmpty) ...[
          const SizedBox(height: 10),
          _VindoDeFora(fonte: fonte, clima: clima),
        ],

        const SizedBox(height: 18),
        _secao('Identificação'),
        TextField(
          controller: _nome,
          textCapitalization: TextCapitalization.words,
          style: const TextStyle(fontSize: 14.5, color: AppTheme.azulEscuro),
          decoration: InputDecoration(
            labelText: 'Nome que aparece no aplicativo',
            labelStyle:
                const TextStyle(fontSize: 13, color: AppTheme.textoFraco),
            filled: true,
            fillColor: AppTheme.white,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppTheme.bordaCampo),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppTheme.bordaCampo),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide:
                  const BorderSide(color: AppTheme.primaria, width: 1.6),
            ),
          ),
        ),

        const SizedBox(height: 18),
        _secao('Água'),
        _escolha('tipo_agua', 'Tipo de água', _rotuloAgua),
        _par('temp_min', 'temp_max'),
        _par('ph_min', 'ph_max'),

        const SizedBox(height: 18),
        _secao('Porte e espaço'),
        _par('tamanho_adulto_cm', 'volume_minimo_l'),

        const SizedBox(height: 18),
        _secao('Comportamento'),
        _escolha('comportamento', 'Temperamento', _rotuloComportamento),
        _escolha('agrupamento', 'Como vive', _rotuloAgrupamento),
        if (_escolhas['agrupamento'] == 'cardume') ...[
          const SizedBox(height: 10),
          _numero('cardume_minimo'),
        ],
        _escolha('nivel_natacao', 'Onde nada', _rotuloNatacao),
        _escolha('alimentacao', 'Alimentação', _rotuloAlimentacao),

        const SizedBox(height: 22),
        if (_erro != null) ...[
          _Recado(
            icone: Icons.error_outline_rounded,
            cor: AppTheme.error,
            titulo: 'Não foi possível gravar',
            texto: _erro!,
            compacto: true,
          ),
          const SizedBox(height: 12),
        ],
        _botoes(),
      ],
    );
  }

  Widget _secao(String titulo) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text(
        titulo.toUpperCase(),
        style: const TextStyle(
          fontSize: 11.5,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
          color: AppTheme.azulMedio,
        ),
      ),
    );
  }

  Widget _par(String esquerda, String direita) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: _numero(esquerda)),
          const SizedBox(width: 10),
          Expanded(child: _numero(direita)),
        ],
      ),
    );
  }

  Widget _numero(String campo) {
    final (rotulo, unidade) = _camposNumericos[campo]!;
    final inteiro = campo == 'volume_minimo_l' || campo == 'cardume_minimo';

    return TextField(
      controller: _numeros[campo],
      keyboardType:
          inteiro ? TextInputType.number : const TextInputType.numberWithOptions(
              decimal: true, signed: true),
      inputFormatters: [
        FilteringTextInputFormatter.allow(
          inteiro ? RegExp(r'[0-9]') : RegExp(r'[0-9.,\-]'),
        ),
      ],
      style: const TextStyle(fontSize: 14.5, color: AppTheme.azulEscuro),
      decoration: InputDecoration(
        labelText: rotulo,
        suffixText: unidade.isEmpty ? null : unidade,
        labelStyle: const TextStyle(fontSize: 13, color: AppTheme.textoFraco),
        filled: true,
        fillColor: AppTheme.white,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppTheme.bordaCampo),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppTheme.bordaCampo),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppTheme.primaria, width: 1.6),
        ),
      ),
    );
  }

  Widget _escolha(String campo, String rotulo, Map<String, String> opcoes) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            rotulo,
            style: const TextStyle(fontSize: 13, color: AppTheme.textoFraco),
          ),
          const SizedBox(height: 7),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final entrada in opcoes.entries)
                _pastilha(
                  entrada.value,
                  selecionada: _escolhas[campo] == entrada.key,
                  aoTocar: () {
                    setState(() {
                      // Tocar na que já está escolhida desmarca: é como
                      // se desfaz um clique errado sem recarregar a tela.
                      _escolhas[campo] = _escolhas[campo] == entrada.key
                          ? null
                          : entrada.key;
                    });
                    _recalcular();
                  },
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _pastilha(String texto,
      {required bool selecionada, required VoidCallback aoTocar}) {
    return Material(
      color: selecionada ? AppTheme.primaria : AppTheme.white,
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: aoTocar,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: selecionada ? AppTheme.primaria : AppTheme.bordaCampo,
            ),
          ),
          child: Text(
            texto,
            style: TextStyle(
              fontSize: 13,
              fontWeight: selecionada ? FontWeight.w600 : FontWeight.w400,
              color: selecionada ? AppTheme.white : AppTheme.azulEscuro,
            ),
          ),
        ),
      ),
    );
  }

  Widget _botoes() {
    if (_gravando) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 14),
          child: CircularProgressIndicator(color: AppTheme.primaria),
        ),
      );
    }

    final fecha = _pendentes.isEmpty;

    return Column(
      children: [
        ElevatedButton.icon(
          onPressed: fecha ? () => _gravar(fechar: true) : null,
          icon: const Icon(Icons.verified_rounded, size: 20),
          label: const Text('Salvar e marcar como conferida'),
          style: ElevatedButton.styleFrom(minimumSize: const Size(0, 48)),
        ),
        if (!fecha)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Para conferir a ficha, falta preencher: '
              '${_pendentes.join(", ")}',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 12,
                color: AppTheme.alertaTexto,
                height: 1.35,
              ),
            ),
          ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () => _gravar(fechar: false),
          icon: const Icon(Icons.save_outlined, size: 19),
          label: const Text('Salvar e continuar depois'),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 46),
            foregroundColor: AppTheme.azulMedio,
            side: const BorderSide(color: AppTheme.bordaCampo),
          ),
        ),
      ],
    );
  }
}

/// Crédito do que já veio preenchido de fora.
///
/// Não é cortesia: a licença da FishBase é CC BY-NC e exige atribuição
/// onde o dado aparecer. Mostrar aqui também explica à loja por que
/// alguns campos já estão respondidos.
class _VindoDeFora extends StatelessWidget {
  const _VindoDeFora({required this.fonte, this.clima});

  final String fonte;
  final String? clima;

  static const _rotulos = {
    'tropical': 'tropical',
    'subtropical': 'subtropical',
    'temperado': 'temperado',
    'boreal': 'boreal',
    'polar': 'polar',
    'altitude': 'de altitude',
    'agua_profunda': 'de água profunda',
  };

  @override
  Widget build(BuildContext context) {
    final nome = _rotulos[clima];

    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: AppTheme.superficieSuave,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.bordaCard),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.menu_book_rounded,
                  size: 16, color: AppTheme.azulMedio),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  'Medidas de $fonte',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppTheme.azulMedio,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          if (nome != null) ...[
            const SizedBox(height: 7),
            Text(
              'A base classifica esta espécie como $nome. A faixa de '
              'temperatura em graus não vem de lá de propósito: o que ela '
              'publica é a faixa de sobrevivência na natureza, que para '
              'peixes introduzidos chega a ir de 0 a 41 °C, e isso não '
              'serve como recomendação de aquário.',
              style: TextStyle(
                fontSize: 11.5,
                color: AppTheme.textoCorpo,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Recado extends StatelessWidget {
  const _Recado({
    required this.icone,
    required this.cor,
    required this.titulo,
    required this.texto,
    this.acao,
    this.compacto = false,
  });

  final IconData icone;
  final Color cor;
  final String titulo;
  final String texto;
  final VoidCallback? acao;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final corpo = Column(
      crossAxisAlignment:
          compacto ? CrossAxisAlignment.start : CrossAxisAlignment.center,
      children: [
        if (!compacto) Icon(icone, size: 46, color: cor),
        if (!compacto) const SizedBox(height: 12),
        Text(
          titulo,
          textAlign: compacto ? TextAlign.start : TextAlign.center,
          style: TextStyle(
            fontSize: compacto ? 13 : 16,
            fontWeight: FontWeight.w700,
            color: compacto ? cor : AppTheme.azulEscuro,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          texto,
          textAlign: compacto ? TextAlign.start : TextAlign.center,
          style: const TextStyle(
            fontSize: 13,
            color: AppTheme.textoCorpo,
            height: 1.4,
          ),
        ),
        if (acao != null) ...[
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: acao,
            icon: const Icon(Icons.refresh_rounded, size: 19),
            label: const Text('Tentar de novo'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.azulMedio,
              side: const BorderSide(color: AppTheme.bordaCampo),
            ),
          ),
        ],
      ],
    );

    if (compacto) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppTheme.errorFundo,
          borderRadius: BorderRadius.circular(10),
        ),
        child: corpo,
      );
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 36),
        child: corpo,
      ),
    );
  }
}
