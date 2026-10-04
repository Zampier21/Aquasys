import 'package:flutter/material.dart';
import '../Tema/app_tema.dart';
import '../Services/ficha_service.dart';
import 'tela_ficha_tecnica.dart';

class TelaManutencoes extends StatefulWidget {
  const TelaManutencoes({super.key});

  @override
  State<TelaManutencoes> createState() => _TelaManutencoesState();
}

class _TelaManutencoesState extends State<TelaManutencoes> {
  List<Map<String, dynamic>> _fichas = [];
  List<Map<String, dynamic>> _arquivadas = [];
  bool _carregando = true;
  bool _verArquivadas = false;
  String? _erro;

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

    final respostas = await Future.wait([
      FichaService.listar(),
      FichaService.listar(arquivadas: true),
    ]);
    if (!mounted) return;

    setState(() {
      _carregando = false;
      final ativas = respostas[0];
      final guardadas = respostas[1];

      if (ativas['sucesso'] == true) {
        _fichas = List<Map<String, dynamic>>.from(ativas['dados']);
        _arquivadas = guardadas['sucesso'] == true
            ? List<Map<String, dynamic>>.from(guardadas['dados'])
            : [];
        if (_arquivadas.isEmpty) _verArquivadas = false;
      } else {
        _erro = ativas['erro'];
      }
    });
  }

  Future<void> _abrirFicha({String? id}) async {
    final salvou = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => TelaFichaTecnica(fichaId: id)),
    );
    if (salvou == true) _carregar();
  }

  String _subtitulo(Map<String, dynamic> ficha) {
    final partes = <String>[];

    final data = ficha['data_atendimento'] as String?;
    if (data != null && data.length == 10) {
      // yyyy-MM-dd → dd/MM/yyyy
      partes.add('${data.substring(8)}/${data.substring(5, 7)}/${data.substring(0, 4)}');
    }
    if (ficha['tipo_instalacao'] != null) {
      partes.add(ficha['tipo_instalacao']);
    }
    if (ficha['nome_empresa'] != null &&
        '${ficha['nome_empresa']}'.isNotEmpty) {
      partes.add(ficha['nome_empresa']);
    }

    return partes.join('  ·  ');
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
                      titulo: 'Manutenções',
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
                    onPressed: () => _abrirFicha(),
                    child: const Text('Adicionar nova ficha'),
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

    final lista = _verArquivadas ? _arquivadas : _fichas;

    if (lista.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _verArquivadas
                    ? Icons.inventory_2_outlined
                    : Icons.assignment_outlined,
                size: 48,
                color: AppTheme.textoFraco.withValues(alpha: 0.5),
              ),
              const SizedBox(height: 12),
              Text(
                _verArquivadas
                    ? 'Nenhuma ficha arquivada'
                    : 'Nenhuma ficha registrada',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _verArquivadas
                    ? 'As fichas que você arquivar ficam aqui e podem voltar'
                    : 'Cada atendimento de manutenção gera uma ficha técnica',
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
          final ficha = lista[i];
          final subtitulo = _subtitulo(ficha);

          return LinhaLista(
            icone: Icon(
              _verArquivadas
                  ? Icons.inventory_2_outlined
                  : Icons.person_rounded,
              color: AppTheme.white,
              size: 22,
            ),
            titulo: ficha['nome_cliente'] ?? '',
            subtitulo: subtitulo.isEmpty ? null : subtitulo,
            onTap: () => _abrirFicha(id: ficha['id']),
            acoes: [
              _verArquivadas
                  ? IconButton(
                      icon: const Icon(Icons.restart_alt_rounded,
                          color: AppTheme.sucesso, size: 20),
                      tooltip: 'Restaurar',
                      onPressed: () => _restaurar(ficha),
                    )
                  : IconButton(
                      icon: const Icon(Icons.inventory_2_outlined,
                          color: AppTheme.alerta, size: 20),
                      tooltip: 'Arquivar',
                      onPressed: () => _confirmarExclusao(ficha),
                    ),
            ],
          );
        },
      ),
    );
  }

  /// Abas de ativas e arquivadas, que só aparecem quando há arquivo.
  Widget _buildFiltro() {
    if (_carregando || _erro != null) return const SizedBox.shrink();
    if (_arquivadas.isEmpty && !_verArquivadas) return const SizedBox.shrink();

    Widget aba(String rotulo, int quantos, bool arquivadas) {
      final selecionada = _verArquivadas == arquivadas;
      return Expanded(
        child: GestureDetector(
          onTap: () => setState(() => _verArquivadas = arquivadas),
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
            aba('Fichas', _fichas.length, false),
            aba('Arquivadas', _arquivadas.length, true),
          ],
        ),
      ),
    );
  }

  Future<void> _restaurar(Map<String, dynamic> ficha) async {
    final resultado = await FichaService.restaurar(ficha['id']);
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(resultado['sucesso'] == true
            ? 'Ficha de ${ficha['nome_cliente']} restaurada'
            : resultado['erro'] ?? 'Erro ao restaurar'),
        backgroundColor: resultado['sucesso'] == true
            ? AppTheme.primaria
            : AppTheme.error,
        behavior: SnackBarBehavior.floating,
      ),
    );
    if (resultado['sucesso'] == true) _carregar();
  }

  void _confirmarExclusao(Map<String, dynamic> ficha) {
    showDialog(
      context: context,
      builder: (contexto) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Excluir ficha',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        content: Text(
          'A ficha de ${ficha['nome_cliente']} sai da lista e vai para o '
          'arquivo. O atendimento continua registrado, e dá para '
          'restaurar pela aba "Arquivadas".',
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
              final resultado = await FichaService.excluir(ficha['id']);
              if (!mounted) return;

              if (resultado['sucesso'] == true) {
                _carregar();
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
            child: const Text('Arquivar'),
          ),
        ],
      ),
    );
  }
}
