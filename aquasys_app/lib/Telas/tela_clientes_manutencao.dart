import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../Services/ficha_service.dart';
import '../widgets/escolha_cliente.dart';

class TelaClientesManutencao extends StatefulWidget {
  const TelaClientesManutencao({super.key});

  @override
  State<TelaClientesManutencao> createState() => _TelaClientesManutencaoState();
}

class _TelaClientesManutencaoState extends State<TelaClientesManutencao> {
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
    setState(() {
      _carregando = true;
      _erro = null;
    });

    final r = await FichaService.listarClientes();
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (r['sucesso'] == true) {
        _clientes = List<Map<String, dynamic>>.from(r['dados']);
      } else {
        _erro = r['erro'];
      }
    });
  }

  List<Map<String, dynamic>> get _filtrados {
    final termo = _busca.text.trim().toLowerCase();
    if (termo.isEmpty) return _clientes;
    return _clientes
        .where((c) => '${c['nome']}'.toLowerCase().contains(termo))
        .toList();
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
                      titulo: 'Clientes de manutenção',
                      centralizado: true,
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),
            if (_clientes.length > 4)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
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
            Expanded(child: _conteudo()),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: Column(
                children: [
                  ElevatedButton(
                    onPressed: () => _abrirFormulario(),
                    child: const Text('Adicionar cliente'),
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

  Widget _conteudo() {
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

    final lista = _filtrados;
    if (lista.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.handyman_outlined,
                  size: 48, color: AppTheme.textoFraco.withValues(alpha: 0.5)),
              const SizedBox(height: 12),
              Text(
                _clientes.isEmpty
                    ? 'Nenhum cliente de manutenção'
                    : 'Nenhum cliente com esse nome',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              const SizedBox(height: 4),
              if (_clientes.isEmpty)
                const Text(
                  'São as pessoas que você atende em casa. Cadastre uma vez '
                  'e os dados vêm prontos nas próximas fichas.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13, color: AppTheme.textoFraco),
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
        itemBuilder: (_, i) => _card(lista[i]),
      ),
    );
  }

  Widget _card(Map<String, dynamic> cliente) {
    final visitas = cliente['total_fichas'] ?? 0;
    final ultima = cliente['ultima_visita'] as String?;

    final instalacao = <String>[];
    if (cliente['tipo_instalacao'] != null) {
      instalacao.add('${cliente['tipo_instalacao']}');
    }
    if (cliente['volume_litros'] != null) {
      instalacao.add('${cliente['volume_litros']}L');
    }
    if (cliente['agua_doce'] != null) {
      instalacao.add(cliente['agua_doce'] == true ? 'água doce' : 'marinho');
    }

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.bordaCard),
        boxShadow: AppTheme.sombraCard,
      ),
      padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const ChipIcone(
            icone: Icon(Icons.person_rounded, color: AppTheme.white, size: 21),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${cliente['nome']}',
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.azulMedio,
                  ),
                ),
                if (cliente['telefone'] != null) ...[
                  const SizedBox(height: 3),
                  _linha(Icons.phone_rounded, '${cliente['telefone']}'),
                ],
                if (cliente['endereco'] != null) ...[
                  const SizedBox(height: 3),
                  _linha(Icons.place_rounded, '${cliente['endereco']}'),
                ],
                if (instalacao.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  _linha(Icons.water_drop_rounded, instalacao.join('  ·  ')),
                ],
                const SizedBox(height: 6),
                Text(
                  visitas == 0
                      ? 'Nenhuma visita registrada'
                      : '$visitas ${visitas == 1 ? "visita" : "visitas"}'
                          '${ultima != null ? "  ·  última em ${_data(ultima)}" : ""}',
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    color: visitas == 0
                        ? AppTheme.textoFraco
                        : AppTheme.sucesso,
                  ),
                ),
              ],
            ),
          ),
          Column(
            children: [
              IconButton(
                icon: const Icon(Icons.edit_outlined,
                    size: 19, color: AppTheme.primaria),
                tooltip: 'Editar',
                onPressed: () => _abrirFormulario(cliente: cliente),
              ),
              IconButton(
                icon: const Icon(Icons.delete_outline_rounded,
                    size: 19, color: AppTheme.error),
                tooltip: 'Remover',
                onPressed: () => _confirmarRemocao(cliente),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _linha(IconData icone, String texto) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icone, size: 13, color: AppTheme.textoFraco),
        const SizedBox(width: 5),
        Expanded(
          child: Text(
            texto,
            style: const TextStyle(fontSize: 12.5, color: AppTheme.textoFraco),
          ),
        ),
      ],
    );
  }

  /// yyyy-MM-dd → dd/MM/yyyy
  String _data(String iso) => iso.length == 10
      ? '${iso.substring(8)}/${iso.substring(5, 7)}/${iso.substring(0, 4)}'
      : iso;

  void _abrirFormulario({Map<String, dynamic>? cliente}) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => FormularioClienteManutencao(
        cliente: cliente,
        aoSalvar: (_) {
          Navigator.pop(context);
          _aviso(cliente == null ? 'Cliente cadastrado.' : 'Cliente atualizado.');
          _carregar();
        },
      ),
    );
  }

  void _confirmarRemocao(Map<String, dynamic> cliente) {
    final visitas = cliente['total_fichas'] ?? 0;

    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Remover cliente',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: Text(
          '${cliente['nome']} sai da lista de manutenção.'
          '${visitas > 0 ? "\n\nAs $visitas ficha${visitas == 1 ? "" : "s"} já "
              "registrada${visitas == 1 ? "" : "s"} continua"
              "${visitas == 1 ? "" : "m"} valendo." : ""}',
          style: TextStyle(
              fontSize: 14, color: Colors.black.withValues(alpha: 0.65)),
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
              final r = await FichaService.removerCliente(cliente['id']);
              if (!mounted) return;

              if (r['sucesso'] == true) {
                _aviso('Cliente removido.');
                _carregar();
              } else {
                _aviso(r['erro'], erro: true);
              }
            },
            child: const Text('Remover'),
          ),
        ],
      ),
    );
  }
}
