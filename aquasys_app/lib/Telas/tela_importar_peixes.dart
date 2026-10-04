import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../Services/peixe_service.dart';
import '../Tema/app_tema.dart';

/// Confere a lista de peixes da loja contra o catálogo do AquaSys.
///
/// Só a conta empresarial chega aqui. Nada é cadastrado: o que a tela
/// mostra é o que o catálogo já cobre, o que ficou ambíguo e o que não
/// existe, para que a loja saiba o que pedir para incluir.
class TelaImportarPeixes extends StatefulWidget {
  const TelaImportarPeixes({super.key});

  @override
  State<TelaImportarPeixes> createState() => _TelaImportarPeixesState();
}

class _TelaImportarPeixesState extends State<TelaImportarPeixes> {
  Map<String, dynamic>? _relatorio;
  // Guardados para o segundo envio: a conferência e a gravação são a
  // mesma rota, e pedir o arquivo de novo para confirmar seria rude.
  List<int>? _bytes;
  String? _arquivo;
  String? _erro;
  bool _enviando = false;
  String _filtro = 'todos';

  // Fora do build: criado ali, o controlador nasceria de novo a cada
  // redesenho e levaria junto o que a loja tivesse acabado de colar.
  final _colado = TextEditingController();

  @override
  void dispose() {
    _colado.dispose();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════
  // ENVIO
  // ═══════════════════════════════════════════════════
  Future<void> _escolherArquivo() async {
    PlatformFile? arquivo;
    Uint8List bytes;
    try {
      arquivo = await FilePicker.pickFile(
        dialogTitle: 'Lista de peixes da loja',
        type: FileType.custom,
        allowedExtensions: const ['csv', 'txt'],
      );
      if (arquivo == null) return;          // o usuário cancelou
      // O seletor não entrega os bytes junto: no navegador o arquivo é um
      // blob, e no celular pode estar em provedor de nuvem. Lê-se aqui.
      bytes = await arquivo.readAsBytes();
    } catch (_) {
      if (!mounted) return;
      setState(() => _erro =
          'Não foi possível abrir o arquivo neste aparelho. '
          'Use o campo abaixo para colar a lista.');
      return;
    }

    await _enviar(bytes, arquivo.name);
  }

  Future<void> _enviarTexto(String texto) async {
    if (texto.trim().isEmpty) return;
    await _enviar(utf8.encode(texto), 'lista colada');
  }

  Future<void> _enviar(List<int> bytes, String origem,
      {bool aplicar = false}) async {
    setState(() {
      _enviando = true;
      _erro = null;
      if (!aplicar) _relatorio = null;
      _bytes = bytes;
      _arquivo = origem;
    });

    final resultado =
        await PeixeService.importarLista(bytes, aplicar: aplicar);
    if (!mounted) return;

    setState(() {
      _enviando = false;
      if (resultado['sucesso'] == true) {
        _relatorio = resultado['dados'] as Map<String, dynamic>;
        _filtro = 'todos';
      } else {
        _erro = resultado['erro'];
      }
    });
  }

  Future<void> _confirmarImportacao() async {
    if (_bytes == null) return;
    await _enviar(_bytes!, _arquivo ?? 'lista', aplicar: true);
    if (!mounted) return;

    final gravacao = _relatorio?['gravacao'] as Map<String, dynamic>?;
    if (gravacao == null) return;

    final partes = <String>[
      if (gravacao['vinculados'] > 0) '${gravacao['vinculados']} do catálogo',
      if (gravacao['criados'] > 0) '${gravacao['criados']} criados',
      if (gravacao['ja_estavam'] > 0) '${gravacao['ja_estavam']} já tinha',
    ];
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(partes.isEmpty
            ? 'Nada novo para importar.'
            : 'Importado: ${partes.join(', ')}.'),
        backgroundColor: AppTheme.sucesso,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // TELA
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
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_rounded,
                        color: AppTheme.azulMedio),
                    onPressed: () => Navigator.pop(context),
                  ),
                  const Expanded(
                    child: BarraSecao(
                      titulo: 'Conferir lista de peixes',
                      centralizado: true,
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),
            Expanded(
              child: _relatorio == null ? _buildInicio() : _buildRelatorio(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInicio() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.superficieSuave,
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Como funciona',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              SizedBox(height: 6),
              Text(
                'Envie a lista dos peixes que a loja vende, um nome por '
                'linha. O AquaSys procura cada um no catálogo e mostra o '
                'que já existe, o que precisa ser especificado melhor e o '
                'que ainda não está cadastrado.',
                style: TextStyle(
                    fontSize: 13.5, color: AppTheme.textoCorpo, height: 1.45),
              ),
              SizedBox(height: 8),
              Text(
                'Nada é cadastrado nesta etapa.',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.primaria,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        if (_enviando)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 28),
            child: Center(
              child: CircularProgressIndicator(color: AppTheme.primaria),
            ),
          )
        else
          ElevatedButton.icon(
            onPressed: _escolherArquivo,
            icon: const Icon(Icons.upload_file_rounded, size: 20),
            label: const Text('Escolher arquivo CSV'),
            style: ElevatedButton.styleFrom(minimumSize: const Size(0, 48)),
          ),
        if (_erro != null) ...[
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.errorFundo,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.error_outline_rounded,
                    size: 18, color: AppTheme.error),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _erro!,
                    style: const TextStyle(
                        fontSize: 13, color: AppTheme.error, height: 1.35),
                  ),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 24),
        const Row(
          children: [
            Expanded(child: Divider(color: AppTheme.bordaCard)),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: 10),
              child: Text('ou cole a lista',
                  style: TextStyle(fontSize: 12.5, color: AppTheme.textoFraco)),
            ),
            Expanded(child: Divider(color: AppTheme.bordaCard)),
          ],
        ),
        const SizedBox(height: 14),
        // Colar resolve dois casos: o seletor de arquivos que não abre em
        // alguns aparelhos, e a loja que tem a lista na tela do sistema
        // de estoque mas não consegue exportar.
        TextField(
          controller: _colado,
          maxLines: 7,
          style: const TextStyle(fontSize: 14, color: AppTheme.textDark),
          decoration: const InputDecoration(
            hintText: 'Betta\nNeon Tetra\nAcará Bandeira\n...',
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _enviando ? null : () => _enviarTexto(_colado.text),
          icon: const Icon(Icons.checklist_rounded, size: 19),
          label: const Text('Conferir a lista colada'),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 46),
            foregroundColor: AppTheme.primaria,
            side: const BorderSide(color: AppTheme.bordaCampo),
          ),
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════
  // RELATÓRIO
  // ═══════════════════════════════════════════════════
  Widget _buildRelatorio() {
    final relatorio = _relatorio!;
    final itens = List<Map<String, dynamic>>.from(relatorio['itens']);
    final visiveis = _filtro == 'todos'
        ? itens
        : itens.where((i) => i['situacao'] == _filtro).toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
          child: Column(
            children: [
              Text(
                '$_arquivo, ${relatorio['total_linhas']} linhas lidas',
                style: const TextStyle(
                    fontSize: 12.5, color: AppTheme.textoFraco),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  _placar('Encontrados', relatorio['encontrados'],
                      AppTheme.sucesso, 'encontrado'),
                  const SizedBox(width: 8),
                  _placar('Ambíguos', relatorio['ambiguos'], AppTheme.alerta,
                      'ambiguo'),
                  const SizedBox(width: 8),
                  _placar('Faltando', relatorio['nao_encontrados'],
                      AppTheme.error, 'nao_encontrado'),
                ],
              ),
            ],
          ),
        ),
        Expanded(
          child: visiveis.isEmpty
              ? const Center(
                  child: Text('Nada nesta categoria',
                      style: TextStyle(
                          fontSize: 14, color: AppTheme.textoFraco)),
                )
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                  itemCount: visiveis.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (_, i) => _linha(visiveis[i]),
                ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
          child: Column(
            children: [
              if (_aplicado) _buildResultadoGravacao() else _buildBotaoImportar(),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _enviando
                    ? null
                    : () => setState(() {
                          _relatorio = null;
                          _bytes = null;
                          _erro = null;
                        }),
                icon: const Icon(Icons.refresh_rounded, size: 19),
                label: const Text('Conferir outra lista'),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(0, 46),
                  foregroundColor: AppTheme.azulMedio,
                  side: const BorderSide(color: AppTheme.bordaCampo),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  bool get _aplicado => _relatorio?['aplicado'] == true;

  Widget _buildBotaoImportar() {
    final r = _relatorio!;
    final entram = (r['encontrados'] as int) + (r['nao_encontrados'] as int);

    if (_enviando) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: CircularProgressIndicator(color: AppTheme.primaria),
      );
    }
    if (entram == 0) {
      return const Text(
        'Nada a importar nesta lista',
        style: TextStyle(fontSize: 13, color: AppTheme.textoFraco),
      );
    }

    return Column(
      children: [
        ElevatedButton.icon(
          onPressed: _confirmarImportacao,
          icon: const Icon(Icons.download_done_rounded, size: 20),
          label: Text('Importar $entram peixes para a minha loja'),
          style: ElevatedButton.styleFrom(minimumSize: const Size(0, 48)),
        ),
        if ((r['ambiguos'] as int) > 0)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              '${r['ambiguos']} nome ambíguo fica de fora até você '
              'especificar qual espécie é',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: AppTheme.alertaTexto),
            ),
          ),
      ],
    );
  }

  Widget _buildResultadoGravacao() {
    final g = _relatorio!['gravacao'] as Map<String, dynamic>?;
    if (g == null) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.sucessoFundo,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.sucessoBorda),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle_rounded,
                  size: 18, color: AppTheme.sucesso),
              const SizedBox(width: 8),
              Text(
                'Lista importada',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.sucesso,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${g['vinculados']} do catálogo entraram no seu estoque, '
            '${g['criados']} foram criados como rascunho.'
            '${(g['criados'] as int) > 0 ? ' Os rascunhos aparecem no app, '
                'mas o motor de compatibilidade vai pedir confirmação até '
                'a ficha ser preenchida.' : ''}',
            style: const TextStyle(
                fontSize: 12.5, color: AppTheme.textoCorpo, height: 1.4),
          ),
          if (g['sem_busca'] == true)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'A busca do nome científico não respondeu; os rascunhos '
                'ficaram só com o nome.',
                style: TextStyle(fontSize: 12, color: AppTheme.alertaTexto),
              ),
            ),
        ],
      ),
    );
  }

  /// Cartão de contagem que também serve de filtro da lista.
  Widget _placar(String rotulo, int quantos, Color cor, String situacao) {
    final ativo = _filtro == situacao;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _filtro = ativo ? 'todos' : situacao),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: ativo ? cor.withValues(alpha: 0.12) : AppTheme.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: ativo ? cor : AppTheme.bordaCard,
              width: ativo ? 1.5 : 1,
            ),
          ),
          child: Column(
            children: [
              Text('$quantos',
                  style: TextStyle(
                      fontSize: 19, fontWeight: FontWeight.w700, color: cor)),
              const SizedBox(height: 2),
              Text(rotulo,
                  style: const TextStyle(
                      fontSize: 11.5, color: AppTheme.textoFraco)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _linha(Map<String, dynamic> item) {
    final situacao = item['situacao'];
    final (cor, icone) = switch (situacao) {
      'encontrado' => (AppTheme.sucesso, Icons.check_circle_rounded),
      'criado' => (AppTheme.primaria, Icons.add_circle_outline_rounded),
      'ambiguo' => (AppTheme.alerta, Icons.help_outline_rounded),
      _ => (AppTheme.error, Icons.remove_circle_outline_rounded),
    };

    final candidatos = List<Map<String, dynamic>>.from(item['candidatos']);
    final sugestoes = List<String>.from(item['sugestoes']);
    final vezes = item['vezes'] as int;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.bordaCard),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icone, size: 20, color: cor),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        item['nome_lido'] ?? '',
                        style: const TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.azulMedio,
                        ),
                      ),
                    ),
                    if (vezes > 1)
                      Text('${vezes}x',
                          style: const TextStyle(
                              fontSize: 12, color: AppTheme.textoFraco)),
                  ],
                ),
                const SizedBox(height: 3),
                if (situacao == 'criado')
                  Text(
                    'Criado no seu catálogo. ${item['como']}',
                    style: const TextStyle(
                        fontSize: 12.5,
                        color: AppTheme.primaria,
                        height: 1.35),
                  )
                else if (situacao == 'encontrado')
                  Text(
                    item['variedade_de'] == null
                        ? '${item['nome_comum']}  ·  ${item['como']}'
                        : '${item['nome_comum']}, variedade de '
                            '${item['variedade_de']}',
                    style: const TextStyle(
                        fontSize: 12.5, color: AppTheme.textoFraco),
                  )
                else if (situacao == 'ambiguo')
                  Text(
                    'Pode ser ${candidatos.map((c) => c['nome_comum']).join(' ou ')}. '
                    'Escreva o nome completo na lista.',
                    style: const TextStyle(
                        fontSize: 12.5, color: AppTheme.textoFraco, height: 1.35),
                  )
                else
                  Text(
                    sugestoes.isEmpty
                        ? 'Não está no catálogo'
                        : 'Não está no catálogo. Você quis dizer '
                            '${sugestoes.join(', ')}?',
                    style: const TextStyle(
                        fontSize: 12.5, color: AppTheme.textoFraco, height: 1.35),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
