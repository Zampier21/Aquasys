import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../Tema/app_tema.dart';
import '../Services/cliente_service.dart';
import '../utils/documento.dart';

/// Lista de acessos (credenciais) que a loja criou para seus clientes.
class TelaAcessosClientes extends StatefulWidget {
  const TelaAcessosClientes({super.key});

  @override
  State<TelaAcessosClientes> createState() => _TelaAcessosClientesState();
}

class _TelaAcessosClientesState extends State<TelaAcessosClientes> {
  List<Map<String, dynamic>> _clientes = [];
  bool _carregando = true;
  bool _verInativos = false;
  String? _erro;

  // Desativar não apaga o cadastro, só tira o acesso e devolve a vaga do
  // plano. Sem uma aba para os inativos, o cadastro ficava no banco sem
  // nenhum caminho de volta, e a loja tinha de criar tudo de novo.
  List<Map<String, dynamic>> get _ativos =>
      _clientes.where((c) => c['ativo'] != false).toList();

  List<Map<String, dynamic>> get _inativos =>
      _clientes.where((c) => c['ativo'] == false).toList();

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

    final resultado = await ClienteService.listar(incluirInativos: true);
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (resultado['sucesso'] == true) {
        _clientes = List<Map<String, dynamic>>.from(resultado['dados']);
        // Reativar o último inativo esvazia a aba: volta para a de ativos
        // em vez de deixar a tela numa lista vazia.
        if (_inativos.isEmpty) _verInativos = false;
      } else {
        _erro = resultado['erro'];
      }
    });
  }

  void _aviso(String mensagem, {bool erro = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(mensagem),
        backgroundColor: erro ? AppTheme.error : AppTheme.primaria,
        behavior: SnackBarBehavior.floating,
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
                      titulo: 'Acesso para clientes',
                      centralizado: true,
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),
            _buildFiltro(),
            Expanded(child: _buildConteudo()),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: Column(
                children: [
                  ElevatedButton(
                    onPressed: _abrirNovoCliente,
                    child: const Text('Adicionar Novo'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text(
                      'Voltar',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.azulMedio,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Abas de ativos e inativos. Só aparecem quando existe algum acesso
  /// desativado: numa loja que nunca desativou ninguém, dois botões para
  /// uma lista só seriam ruído.
  Widget _buildFiltro() {
    if (_carregando || _erro != null) return const SizedBox.shrink();
    if (_inativos.isEmpty && !_verInativos) return const SizedBox.shrink();

    Widget aba(String rotulo, int quantos, bool inativos) {
      final selecionada = _verInativos == inativos;
      return Expanded(
        child: GestureDetector(
          onTap: () => setState(() => _verInativos = inativos),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 9),
            decoration: BoxDecoration(
              color: selecionada ? AppTheme.white : Colors.transparent,
              borderRadius: BorderRadius.circular(9),
              border: Border.all(
                color: selecionada ? AppTheme.bordaCampo : Colors.transparent,
              ),
            ),
            child: Text(
              '$rotulo ($quantos)',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: selecionada ? AppTheme.azulMedio : AppTheme.textoFraco,
              ),
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: AppTheme.superficieSuave,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            aba('Ativos', _ativos.length, false),
            aba('Inativos', _inativos.length, true),
          ],
        ),
      ),
    );
  }

  Widget _buildConteudo() {
    if (_carregando) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaria),
      );
    }

    if (_erro != null) {
      return Center(
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
                style: const TextStyle(fontSize: 14, color: AppTheme.textoFraco),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: 160,
                child: ElevatedButton(
                  onPressed: _carregar,
                  child: const Text('Tentar de novo'),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final lista = _verInativos ? _inativos : _ativos;

    if (lista.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.person_off_outlined,
                  size: 48, color: AppTheme.textoFraco.withValues(alpha: 0.5)),
              const SizedBox(height: 12),
              Text(
                _verInativos
                    ? 'Nenhum acesso desativado'
                    : 'Nenhum acesso criado ainda',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _verInativos
                    ? 'Os acessos que você desativar aparecem aqui e podem '
                        'ser reativados'
                    : 'Use "Adicionar Novo" para liberar o app a um cliente',
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 13, color: AppTheme.textoFraco),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      color: AppTheme.primaria,
      onRefresh: _carregar,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
        itemCount: lista.length,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (_, i) {
          final cliente = lista[i];
          final inativo = cliente['ativo'] == false;
          return LinhaLista(
            icone: Icon(
              inativo ? Icons.person_off_rounded : Icons.person_rounded,
              color: AppTheme.white,
              size: 22,
            ),
            titulo: cliente['nome'] ?? '',
            subtitulo: inativo
                ? '${cliente['cpf_cnpj']}  ·  sem acesso'
                : cliente['cpf_cnpj'],
            onTap: () => _abrirAcoes(cliente),
            acoes: [
              IconButton(
                icon: Icon(
                  inativo
                      ? Icons.restart_alt_rounded
                      : Icons.more_vert_rounded,
                  color: inativo ? AppTheme.sucesso : AppTheme.azulMedio,
                  size: 20,
                ),
                onPressed: () => inativo
                    ? _confirmarReativar(cliente)
                    : _abrirAcoes(cliente),
              ),
            ],
          );
        },
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // AÇÕES DO ACESSO
  // ═══════════════════════════════════════════════════
  void _abrirAcoes(Map<String, dynamic> cliente) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (contexto) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
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
            const SizedBox(height: 16),
            Text(
              cliente['nome'] ?? '',
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: AppTheme.azulMedio,
              ),
            ),
            const SizedBox(height: 12),
            ListTile(
              leading: const Icon(Icons.key_rounded, color: AppTheme.primaria),
              title: const Text('Redefinir senha'),
              onTap: () {
                Navigator.pop(contexto);
                _abrirRedefinirSenha(cliente);
              },
            ),
            if (cliente['ativo'] == false)
              ListTile(
                leading: const Icon(Icons.restart_alt_rounded,
                    color: AppTheme.sucesso),
                title: const Text('Reativar acesso'),
                onTap: () {
                  Navigator.pop(contexto);
                  _confirmarReativar(cliente);
                },
              )
            else
              ListTile(
                leading:
                    const Icon(Icons.block_rounded, color: AppTheme.error),
                title: const Text('Desativar acesso'),
                onTap: () {
                  Navigator.pop(contexto);
                  _confirmarDesativar(cliente);
                },
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  void _abrirRedefinirSenha(Map<String, dynamic> cliente) {
    final controlador = TextEditingController();
    final chaveForm = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        title: const Text(
          'Redefinir senha',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: Form(
          key: chaveForm,
          child: TextFormField(
            controller: controlador,
            decoration: const InputDecoration(hintText: 'Nova senha'),
            validator: (v) => (v == null || v.length < 6)
                ? 'Mínimo de 6 caracteres'
                : null,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto),
            child: const Text('Cancelar',
                style: TextStyle(color: AppTheme.textoFraco)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(120, 44),
            ),
            onPressed: () async {
              if (!chaveForm.currentState!.validate()) return;
              Navigator.pop(contexto);

              final resultado = await ClienteService.editar(
                id: cliente['id'],
                senha: controlador.text,
              );
              if (!mounted) return;

              if (resultado['sucesso'] == true) {
                _aviso('Senha redefinida.');
              } else {
                _aviso(resultado['erro'], erro: true);
              }
            },
            child: const Text('Salvar'),
          ),
        ],
      ),
    );
  }

  void _confirmarDesativar(Map<String, dynamic> cliente) {
    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        title: const Text(
          'Desativar acesso',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: Text(
          'O acesso de ${cliente['nome']} deixa de funcionar no login. '
          'Os aquários e o histórico continuam salvos.',
          style: TextStyle(
            fontSize: 14,
            color: Colors.black.withValues(alpha: 0.65),
          ),
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

              final resultado = await ClienteService.desativar(cliente['id']);
              if (!mounted) return;

              if (resultado['sucesso'] == true) {
                _aviso('Acesso desativado.');
                _carregar();
              } else {
                _aviso(resultado['erro'], erro: true);
              }
            },
            child: const Text('Desativar'),
          ),
        ],
      ),
    );
  }

  void _confirmarReativar(Map<String, dynamic> cliente) {
    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        title: const Text(
          'Reativar acesso',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: Text(
          '${cliente['nome']} volta a entrar no aplicativo com a mesma '
          'senha de antes, e os aquários e o histórico continuam onde '
          'estavam. O acesso volta a ocupar uma vaga do seu plano.',
          style: TextStyle(
            fontSize: 14,
            color: Colors.black.withValues(alpha: 0.65),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto),
            child: const Text('Cancelar',
                style: TextStyle(color: AppTheme.textoFraco)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.sucesso,
              minimumSize: const Size(120, 44),
            ),
            onPressed: () async {
              Navigator.pop(contexto);

              final resultado = await ClienteService.editar(
                id: cliente['id'],
                ativo: true,
              );
              if (!mounted) return;

              if (resultado['sucesso'] == true) {
                _aviso('Acesso reativado.');
                _carregar();
              } else {
                // Quando o plano está cheio a API responde 409 com o texto
                // que explica o limite e o que fazer. Mostrar esse texto
                // vale mais do que um "não foi possível" genérico.
                _aviso(resultado['erro'], erro: true);
              }
            },
            child: const Text('Reativar'),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // MODAL — NOVO CLIENTE
  // ═══════════════════════════════════════════════════
  void _abrirNovoCliente() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => _DialogoNovoCliente(
        aoCriar: () {
          _aviso('Acesso criado com sucesso.');
          _carregar();
        },
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════
// DIÁLOGO DE CADASTRO
// ═══════════════════════════════════════════════════════
class _DialogoNovoCliente extends StatefulWidget {
  final VoidCallback aoCriar;
  const _DialogoNovoCliente({required this.aoCriar});

  @override
  State<_DialogoNovoCliente> createState() => _DialogoNovoClienteState();
}

class _DialogoNovoClienteState extends State<_DialogoNovoCliente> {
  final _chaveForm = GlobalKey<FormState>();
  final _nome = TextEditingController();
  final _cpf = TextEditingController();
  final _senha = TextEditingController();
  final _email = TextEditingController();

  bool _salvando = false;
  String? _erro;

  @override
  void dispose() {
    _nome.dispose();
    _cpf.dispose();
    _senha.dispose();
    _email.dispose();
    super.dispose();
  }

  Future<void> _criar() async {
    setState(() => _erro = null);
    if (!_chaveForm.currentState!.validate()) return;

    setState(() => _salvando = true);
    final resultado = await ClienteService.criar(
      nome: _nome.text.trim(),
      cpf: _cpf.text,
      senhaInicial: _senha.text,
      email: _email.text.trim(),
    );
    if (!mounted) return;
    setState(() => _salvando = false);

    if (resultado['sucesso'] == true) {
      Navigator.pop(context);
      widget.aoCriar();
    } else {
      setState(() => _erro = resultado['erro']);
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
              const Text(
                'Novo cliente',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulEscuro,
                ),
              ),
              const SizedBox(height: 18),

              if (_erro != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                      vertical: 12, horizontal: 14),
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

              _label('Nome do Cliente', obrigatorio: true),
              TextFormField(
                controller: _nome,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(hintText: 'Ex: Weslley'),
                validator: (v) => (v == null || v.trim().length < 2)
                    ? 'Informe o nome'
                    : null,
              ),
              const SizedBox(height: 14),

              _label('CPF', obrigatorio: true),
              TextFormField(
                controller: _cpf,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  CpfCnpjInputFormatter(),
                ],
                decoration: const InputDecoration(
                  hintText: '999.999.999-99',
                ),
                // No cadastro conferimos o dígito verificador: o documento
                // errado aqui vira um login que nunca funciona.
                validator: (v) => validarDocumento(v),
              ),
              const SizedBox(height: 14),

              _label('Senha inicial', obrigatorio: true),
              TextFormField(
                controller: _senha,
                decoration: const InputDecoration(hintText: 'Ex: 123456'),
                validator: (v) => (v == null || v.length < 6)
                    ? 'Mínimo de 6 caracteres'
                    : null,
              ),
              const SizedBox(height: 14),

              _label('Email'),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  hintText: 'Ex: cliente@email.com',
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null;
                  final ok = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
                      .hasMatch(v.trim());
                  return ok ? null : 'E-mail inválido';
                },
              ),
              const SizedBox(height: 22),

              ElevatedButton(
                onPressed: _salvando ? null : _criar,
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
                    : const Text('Criar'),
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

  Widget _label(String texto, {bool obrigatorio = false}) {
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
