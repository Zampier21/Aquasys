import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../Services/ficha_service.dart';

/// Escolha do cliente da visita, aberta de dentro da ficha.
class EscolhaCliente extends StatefulWidget {
  final void Function(Map<String, dynamic>) aoEscolher;
  const EscolhaCliente({super.key, required this.aoEscolher});

  @override
  State<EscolhaCliente> createState() => _EscolhaClienteState();
}

class _EscolhaClienteState extends State<EscolhaCliente> {
  final _busca = TextEditingController();
  List<Map<String, dynamic>> _clientes = [];
  bool _carregando = true;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  @override
  void dispose() {
    _busca.dispose();
    super.dispose();
  }

  Future<void> _carregar() async {
    setState(() => _carregando = true);
    final r = await FichaService.listarClientes();
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (r['sucesso'] == true) {
        _clientes = List<Map<String, dynamic>>.from(r['dados']);
        _erro = null;
      } else {
        _erro = r['erro'];
      }
    });
  }

  // A busca é local: a lista de clientes de uma loja é pequena, e
  // filtrar aqui responde a cada tecla sem ida ao servidor.
  List<Map<String, dynamic>> get _filtrados {
    final termo = _busca.text.trim().toLowerCase();
    if (termo.isEmpty) return _clientes;
    return _clientes
        .where((c) => '${c['nome']}'.toLowerCase().contains(termo))
        .toList();
  }

  /// Linha de apoio do card: o que a ficha vai herdar deste cliente.
  String _resumo(Map<String, dynamic> cliente) {
    final partes = <String>[];
    if (cliente['tipo_instalacao'] != null) {
      partes.add('${cliente['tipo_instalacao']}');
    }
    if (cliente['volume_litros'] != null) {
      partes.add('${cliente['volume_litros']}L');
    }
    if (cliente['agua_doce'] != null) {
      partes.add(cliente['agua_doce'] == true ? 'água doce' : 'marinho');
    }
    final visitas = cliente['total_fichas'] ?? 0;
    if (visitas > 0) {
      partes.add('$visitas ${visitas == 1 ? "visita" : "visitas"}');
    }
    return partes.join('  ·  ');
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SafeArea(
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.75,
          child: Column(
            children: [
              const SizedBox(height: 12),
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppTheme.bordaCampo,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 16, 20, 4),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Cliente da visita',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.azulMedio,
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                child: TextField(
                  controller: _busca,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(
                    hintText: 'Buscar pelo nome...',
                    prefixIcon: Icon(Icons.search_rounded,
                        size: 20, color: AppTheme.textoFraco),
                  ),
                ),
              ),
              Expanded(child: _lista()),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                child: ElevatedButton.icon(
                  onPressed: _abrirCadastro,
                  icon: const Icon(Icons.person_add_alt_1_rounded, size: 19),
                  label: const Text('Cadastrar novo cliente'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _lista() {
    if (_carregando) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaria),
      );
    }

    if (_erro != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            _erro!,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13.5, color: AppTheme.textoFraco),
          ),
        ),
      );
    }

    final lista = _filtrados;
    if (lista.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            _clientes.isEmpty
                ? 'Nenhum cliente cadastrado ainda.\nCadastre o primeiro no botão abaixo.'
                : 'Nenhum cliente com esse nome.',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13.5, color: AppTheme.textoFraco),
          ),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      itemCount: lista.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (_, i) {
        final cliente = lista[i];
        final resumo = _resumo(cliente);
        return LinhaLista(
          icone:
              const Icon(Icons.person_rounded, color: AppTheme.white, size: 21),
          titulo: '${cliente['nome']}',
          subtitulo: resumo.isEmpty ? null : resumo,
          onTap: () => widget.aoEscolher(cliente),
        );
      },
    );
  }

  void _abrirCadastro() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => FormularioClienteManutencao(
        aoSalvar: (cliente) {
          Navigator.pop(context);
          widget.aoEscolher(cliente);
        },
      ),
    );
  }
}

/// Formulário do cliente de manutenção.
class FormularioClienteManutencao extends StatefulWidget {
  final Map<String, dynamic>? cliente;
  final void Function(Map<String, dynamic>) aoSalvar;

  const FormularioClienteManutencao({
    super.key,
    this.cliente,
    required this.aoSalvar,
  });

  @override
  State<FormularioClienteManutencao> createState() =>
      _FormularioClienteManutencaoState();
}

class _FormularioClienteManutencaoState
    extends State<FormularioClienteManutencao> {
  final _chaveForm = GlobalKey<FormState>();
  final _nome = TextEditingController();
  final _telefone = TextEditingController();
  final _endereco = TextEditingController();
  final _litros = TextEditingController();
  String? _tipoInstalacao;
  bool? _aguaDoce;

  bool _salvando = false;
  String? _erro;

  bool get _editando => widget.cliente != null;

  @override
  void initState() {
    super.initState();
    final c = widget.cliente;
    if (c == null) return;

    _nome.text = '${c['nome'] ?? ''}';
    _telefone.text = '${c['telefone'] ?? ''}';
    _endereco.text = '${c['endereco'] ?? ''}';
    _litros.text = c['volume_litros'] == null ? '' : '${c['volume_litros']}';
    _tipoInstalacao = c['tipo_instalacao'];
    _aguaDoce = c['agua_doce'];
  }

  @override
  void dispose() {
    for (final c in [_nome, _telefone, _endereco, _litros]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _ouNulo(TextEditingController c) =>
      c.text.trim().isEmpty ? null : c.text.trim();

  Future<void> _salvar() async {
    setState(() => _erro = null);
    if (!_chaveForm.currentState!.validate()) return;

    setState(() => _salvando = true);

    final r = _editando
        ? await FichaService.editarCliente(widget.cliente!['id'], {
            'nome': _nome.text.trim(),
            'telefone': _ouNulo(_telefone),
            'endereco': _ouNulo(_endereco),
            'tipo_instalacao': _tipoInstalacao,
            'volume_litros': int.tryParse(_litros.text.trim()),
            'agua_doce': _aguaDoce,
          })
        : await FichaService.criarCliente(
            nome: _nome.text.trim(),
            telefone: _ouNulo(_telefone),
            endereco: _ouNulo(_endereco),
            tipoInstalacao: _tipoInstalacao,
            volumeLitros: int.tryParse(_litros.text.trim()),
            aguaDoce: _aguaDoce,
          );
    if (!mounted) return;
    setState(() => _salvando = false);

    if (r['sucesso'] == true) {
      widget.aoSalvar(r['dados'] as Map<String, dynamic>);
    } else {
      setState(() => _erro = r['erro']);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.white,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 40),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _chaveForm,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _editando ? 'Editar cliente' : 'Novo cliente de manutenção',
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulEscuro,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _editando
                    ? 'As fichas já registradas não mudam.'
                    : 'Preenchido uma vez. Nas próximas visitas é só escolher da lista.',
                style: const TextStyle(
                    fontSize: 12, color: AppTheme.textoFraco),
              ),
              const SizedBox(height: 18),
              if (_erro != null) ...[
                Container(
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
                  decoration: BoxDecoration(
                    color: AppTheme.errorFundo,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.error),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline,
                          color: AppTheme.error, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _erro!,
                          style: const TextStyle(
                              fontSize: 13, color: AppTheme.error),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],
              _rotulo('Nome', obrigatorio: true),
              TextFormField(
                controller: _nome,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(hintText: 'Ex: Seu João'),
                validator: (v) =>
                    (v == null || v.trim().length < 2) ? 'Informe o nome' : null,
              ),
              const SizedBox(height: 14),
              _rotulo('Telefone'),
              TextFormField(
                controller: _telefone,
                keyboardType: TextInputType.phone,
                decoration:
                    const InputDecoration(hintText: 'Ex: (41) 99999-0000'),
              ),
              const SizedBox(height: 14),
              _rotulo('Endereço'),
              TextFormField(
                controller: _endereco,
                decoration: const InputDecoration(
                    hintText: 'Ex: Rua das Palmeiras, 120'),
              ),
              const SizedBox(height: 18),
              const Text(
                'Dados da instalação',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              const SizedBox(height: 2),
              const Text(
                'Vêm preenchidos na ficha a cada visita.',
                style: TextStyle(fontSize: 11.5, color: AppTheme.textoFraco),
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                initialValue: _tipoInstalacao,
                isExpanded: true,
                style: const TextStyle(fontSize: 14, color: AppTheme.azulEscuro),
                hint: const Text('Aquário ou lago',
                    style: TextStyle(fontSize: 13, color: AppTheme.textoFraco)),
                items: const [
                  DropdownMenuItem(value: 'aquario', child: Text('Aquário')),
                  DropdownMenuItem(value: 'lago', child: Text('Lago')),
                ],
                onChanged: (v) => setState(() => _tipoInstalacao = v),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _litros,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(hintText: 'Quantos litros?'),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null;
                  final n = int.tryParse(v.trim());
                  if (n == null) return 'Use só números inteiros';
                  if (n <= 0) return 'Precisa ser maior que zero';
                  return null;
                },
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<bool>(
                initialValue: _aguaDoce,
                isExpanded: true,
                style: const TextStyle(fontSize: 14, color: AppTheme.azulEscuro),
                hint: const Text('Água doce ou marinho?',
                    style: TextStyle(fontSize: 13, color: AppTheme.textoFraco)),
                items: const [
                  DropdownMenuItem(value: true, child: Text('Água doce')),
                  DropdownMenuItem(value: false, child: Text('Marinho')),
                ],
                onChanged: (v) => setState(() => _aguaDoce = v),
              ),
              const SizedBox(height: 22),
              ElevatedButton(
                onPressed: _salvando ? null : _salvar,
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
                    : Text(_editando ? 'Salvar' : 'Cadastrar e usar'),
              ),
              const SizedBox(height: 10),
              BotaoCancelar(
                onPressed: _salvando ? null : () => Navigator.pop(context),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _rotulo(String texto, {bool obrigatorio = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Text(
            texto,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.azulEscuro,
            ),
          ),
          if (obrigatorio)
            const Text(' *', style: TextStyle(color: AppTheme.error)),
        ],
      ),
    );
  }
}
