import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import '../Tema/app_tema.dart';
import '../widgets/bottom_nav.dart';
import '../widgets/cabecalho_usuario.dart';
import '../Services/painel_service.dart';
import '../Services/notificacao_service.dart';
import 'tela_aquarios.dart';
import 'tela_peixes.dart';
import 'tela_clientes.dart';

class TelaInicial extends StatefulWidget {
  final String tipoUsuario;
  const TelaInicial({super.key, required this.tipoUsuario});

  @override
  State<TelaInicial> createState() => _TelaInicialState();
}

class _TelaInicialState extends State<TelaInicial>
    with WidgetsBindingObserver {
  Map<String, dynamic>? _painel;
  bool _carregando = true;
  String? _erro;
  bool _pediuPermissao = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _carregar();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    // Ao voltar do background, recarrega: o lembrete tem de refletir a
    // última medição, não a de quando o app foi minimizado.
    if (estado == AppLifecycleState.resumed) _carregar();
  }

  Future<void> _carregar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    final resultado = await PainelService.carregar();
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (resultado['sucesso'] == true) {
        _painel = resultado['dados'] as Map<String, dynamic>;
      } else {
        _erro = resultado['erro'];
      }
    });

    if (resultado['sucesso'] == true) {
      await _sincronizarLembretes();
    }
  }

  /// Reflete os alertas abertos nos lembretes do aparelho.
  ///
  /// A permissão só é pedida quando existe algo a notificar — pedir na
  /// abertura, sem contexto, é o caminho mais curto para o usuário negar.
  Future<void> _sincronizarLembretes() async {
    final alertas = (_painel?['alertas'] as List?) ?? const [];

    if (alertas.isNotEmpty && !_pediuPermissao) {
      _pediuPermissao = true;
      await NotificacaoService.pedirPermissao();
    }

    await NotificacaoService.sincronizar(alertas);
  }

  Future<void> _dispensarAlerta(String id) async {
    final ok = await PainelService.marcarLido(id);
    if (ok) _carregar();
  }

  void _onNavTap(int index) {
    if (index == 0) return;
    final t = widget.tipoUsuario;
    final destino = switch (index) {
      1 => TelaAquarios(tipoUsuario: t),
      2 => TelaPeixes(tipoUsuario: t),
      _ => TelaClientes(tipoUsuario: t),
    };
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => destino));
  }

  @override
  Widget build(BuildContext context) {
    final isDono = widget.tipoUsuario == 'dono';

    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppTheme.primaria,
          onRefresh: _carregar,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CabecalhoUsuario(tipoUsuario: widget.tipoUsuario),
                const SizedBox(height: 26),
                _buildTituloSecao('Meu Painel', 'Resumo dos seus aquários'),
                const SizedBox(height: 14),
                if (_erro != null)
                  _buildErro()
                else ...[
                  _buildCardsResumo(),
                  const SizedBox(height: 18),
                  ..._buildAlertas(),
                  ..._buildDicas(),
                ],
                _buildAtalhos(isDono),
              ],
            ),
          ),
        ),
      ),
      bottomNavigationBar: BottomNav(
        currentIndex: 0,
        onTap: _onNavTap,
        isDono: isDono,
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // TÍTULO DE SEÇÃO
  // ═══════════════════════════════════════════════════
  Widget _buildTituloSecao(String titulo, String subtitulo) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          titulo,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
        const SizedBox(height: 2),
        Text(subtitulo,
            style: const TextStyle(fontSize: 13, color: AppTheme.textoFraco)),
      ],
    );
  }

  // ═══════════════════════════════════════════════════
  // CARDS DE RESUMO
  // ═══════════════════════════════════════════════════
  /// Enquanto o painel não chega, o card mostra "—" em vez de zero:
  /// zero é uma informação, "ainda carregando" não.
  String _numero(String campo, {String sufixo = ''}) {
    if (_carregando || _painel == null) return '—';
    final valor = _painel![campo];
    return valor == null ? '—' : '$valor$sufixo';
  }

  Widget _buildCardsResumo() {
    return SizedBox(
      height: 138,
      child: Row(
        children: [
          Expanded(
            child: _cardResumo(
              _numero('total_aquarios'),
              'Meus\nAquários',
              const Icon(Icons.water_drop_rounded,
                  color: AppTheme.white, size: 20),
              AppTheme.primaria,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _cardResumo(
              _numero('total_peixes'),
              'Peixes',
              const FaIcon(FontAwesomeIcons.fish,
                  color: AppTheme.white, size: 17),
              AppTheme.acentoVerde,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _cardResumo(
              _numero('saude_geral', sufixo: '%'),
              'Saúde\ngeral',
              const Icon(Icons.trending_up_rounded,
                  color: AppTheme.white, size: 21),
              AppTheme.acentoAzul,
            ),
          ),
        ],
      ),
    );
  }

  Widget _cardResumo(String valor, String label, Widget icone, Color cor) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.bordaCard),
        boxShadow: AppTheme.sombraCard,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          ChipIcone(icone: icone, cor: cor, tamanho: 42),
          const SizedBox(height: 10),
          Text(
            valor,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: AppTheme.azulEscuro,
              height: 1,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 11.5,
              color: AppTheme.textoFraco,
              height: 1.25,
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ERRO DE CARGA
  // ═══════════════════════════════════════════════════
  Widget _buildErro() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.bordaCard),
        boxShadow: AppTheme.sombraCard,
      ),
      child: Column(
        children: [
          const Icon(Icons.cloud_off_rounded,
              size: 40, color: AppTheme.textoFraco),
          const SizedBox(height: 10),
          Text(
            _erro!,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13.5, color: AppTheme.textoFraco),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: 170,
            child: ElevatedButton(
              onPressed: _carregar,
              style: ElevatedButton.styleFrom(minimumSize: const Size(0, 42)),
              child: const Text('Tentar de novo'),
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ALERTAS — vindos da tabela `alerta`
  // ═══════════════════════════════════════════════════
  List<Widget> _buildAlertas() {
    final alertas = (_painel?['alertas'] as List?) ?? const [];

    if (alertas.isEmpty) {
      // Sem problema aberto não faz sentido um card amarelo vazio.
      if (_carregando || _painel == null) return [];
      return [_buildTudoCerto(), const SizedBox(height: 18)];
    }

    return [
      Container(
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.alertaBorda),
          boxShadow: AppTheme.sombraCard,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
              decoration: const BoxDecoration(
                color: AppTheme.alertaFundo,
                borderRadius: BorderRadius.vertical(top: Radius.circular(15)),
                border: Border(bottom: BorderSide(color: AppTheme.alertaBorda)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: AppTheme.alertaPonto.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(9),
                    ),
                    child: const Icon(Icons.warning_amber_rounded,
                        color: AppTheme.alerta, size: 18),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'Atenção',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.alertaTexto,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final alerta in alertas)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            margin: const EdgeInsets.only(top: 5),
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(
                              color: AppTheme.alertaPonto,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  alerta['aquario'] ?? '',
                                  style: const TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.azulMedio,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  alerta['mensagem'] ?? '',
                                  style: TextStyle(
                                    fontSize: 12.5,
                                    color: Colors.black.withValues(alpha: 0.62),
                                    height: 1.35,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          // Dispensa o aviso sem corrigir o parâmetro; ele
                          // volta na próxima medição que continuar fora.
                          InkWell(
                            onTap: () => _dispensarAlerta(alerta['id']),
                            borderRadius: BorderRadius.circular(20),
                            child: const Padding(
                              padding: EdgeInsets.all(4),
                              child: Icon(Icons.close_rounded,
                                  size: 16, color: AppTheme.textoFraco),
                            ),
                          ),
                        ],
                      ),
                    ),
                  Center(
                    child: InkWell(
                      onTap: () => _onNavTap(1),
                      borderRadius: BorderRadius.circular(8),
                      child: const Padding(
                        padding: EdgeInsets.symmetric(vertical: 2),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              'Ver meus aquários',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.primaria,
                              ),
                            ),
                            SizedBox(width: 4),
                            Icon(Icons.chevron_right_rounded,
                                size: 18, color: AppTheme.primaria),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 18),
    ];
  }

  Widget _buildTudoCerto() {
    final semAquario = (_painel?['total_aquarios'] ?? 0) == 0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: semAquario ? AppTheme.superficieSuave : AppTheme.sucessoFundo,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: semAquario ? AppTheme.bordaCard : AppTheme.sucessoBorda,
        ),
      ),
      child: Row(
        children: [
          Icon(
            semAquario ? Icons.water_drop_outlined : Icons.check_circle_rounded,
            color: semAquario ? AppTheme.primaria : AppTheme.sucesso,
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              semAquario
                  ? 'Cadastre seu primeiro aquário para acompanhar os parâmetros'
                  : 'Todos os parâmetros estão dentro da faixa ideal',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: semAquario ? AppTheme.azulMedio : AppTheme.sucesso,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // DICAS — vindas da tabela `dica`
  // ═══════════════════════════════════════════════════
  List<Widget> _buildDicas() {
    final dicas = (_painel?['dicas'] as List?) ?? const [];
    if (dicas.isEmpty) return [];

    return [
      Container(
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.bordaCard),
          boxShadow: AppTheme.sombraCard,
        ),
        child: Column(
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
              decoration: const BoxDecoration(
                color: AppTheme.superficieSuave,
                borderRadius: BorderRadius.vertical(top: Radius.circular(15)),
                border: Border(bottom: BorderSide(color: AppTheme.bordaCard)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: AppTheme.primaria.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(9),
                    ),
                    child: const Icon(Icons.lightbulb_outline_rounded,
                        color: AppTheme.primaria, size: 17),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'Dicas para você',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.azulMedio,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Column(
                children: List.generate(dicas.length, (i) {
                  return Column(
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 13),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 24,
                              height: 24,
                              decoration: const BoxDecoration(
                                color: AppTheme.superficieAzul,
                                shape: BoxShape.circle,
                              ),
                              child: Center(
                                child: Text(
                                  '${i + 1}',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.azulMedio,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                dicas[i]['conteudo'] ?? '',
                                style: TextStyle(
                                  fontSize: 12.5,
                                  color: Colors.black.withValues(alpha: 0.62),
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (i < dicas.length - 1)
                        Divider(
                          height: 1,
                          color: AppTheme.bordaCard.withValues(alpha: 0.7),
                          indent: 36,
                        ),
                    ],
                  );
                }),
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 18),
    ];
  }

  // ═══════════════════════════════════════════════════
  // ATALHOS
  // ═══════════════════════════════════════════════════
  Widget _buildAtalhos(bool isDono) {
    // IntrinsicHeight no lugar de altura fixa: os dois cards passam a ter
    // exatamente a mesma altura — a do mais alto — e nada é cortado quando
    // o celular está com a fonte do sistema aumentada. Era a altura travada
    // em 108 que cortava a escrita e fazia um card parecer menor que o outro.
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: _cardAtalho(
              'Aquários',
              'Gerenciar',
              const Icon(Icons.water_drop_rounded,
                  color: AppTheme.white, size: 20),
              AppTheme.primaria,
              () => _onNavTap(1),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _cardAtalho(
              isDono ? 'Clientes' : 'Aprender',
              isDono ? 'Gerenciar' : 'Mini cursos',
              Icon(
                isDono ? Icons.groups_rounded : Icons.school_rounded,
                color: AppTheme.white,
                size: 21,
              ),
              AppTheme.acentoRosa,
              () => _onNavTap(3),
            ),
          ),
        ],
      ),
    );
  }

  Widget _cardAtalho(
    String titulo,
    String subtitulo,
    Widget icone,
    Color cor,
    VoidCallback onTap,
  ) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppTheme.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.bordaCard),
            boxShadow: AppTheme.sombraCard,
          ),
          // Empilhado, e não lado a lado: em meia tela de celular o ícone,
          // o texto e a seta na mesma linha deixavam menos de 50 px para a
          // palavra, e "Aquários" não cabia. Na vertical o texto usa a
          // largura inteira do card.
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  ChipIcone(icone: icone, cor: cor, tamanho: 40),
                  const Spacer(),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: AppTheme.textoFraco.withValues(alpha: 0.6),
                    size: 20,
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                titulo,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 14.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.azulMedio,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitulo,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    fontSize: 12, color: AppTheme.textoFraco),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
