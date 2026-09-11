import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../Tema/app_tema.dart';
import '../Services/auth_service.dart';
import '../Services/notificacao_service.dart';
import '../Services/perfil_service.dart';
import 'tela_login.dart';

class TelaConfiguracoes extends StatefulWidget {
  const TelaConfiguracoes({super.key});

  @override
  State<TelaConfiguracoes> createState() => _TelaConfiguracoesState();
}

class _TelaConfiguracoesState extends State<TelaConfiguracoes> {
  Map<String, dynamic>? _perfil;
  bool _carregando = true;
  bool _salvandoFoto = false;
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

    final resposta = await PerfilService.carregar();
    if (!mounted) return;

    setState(() {
      _carregando = false;
      if (resposta['sucesso'] == true) {
        _perfil = Map<String, dynamic>.from(resposta['dados']);
      } else {
        _erro = resposta['erro'];
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
        duration: const Duration(seconds: 3),
      ),
    );
  }

  bool get _isDono => _perfil?['tipo'] == 'dono';

  // ─── Foto / logo ────────────────────────────────────────
  Future<void> _escolherFoto(ImageSource origem) async {
    final arquivo = await ImagePicker().pickImage(
      source: origem,
      maxWidth: 512,
      maxHeight: 512,
      imageQuality: 85,
    );
    if (arquivo == null || !mounted) return;

    setState(() => _salvandoFoto = true);
    final bytes = await arquivo.readAsBytes();
    final resposta = await PerfilService.trocarAvatar(base64Encode(bytes));
    if (!mounted) return;

    setState(() {
      _salvandoFoto = false;
      if (resposta['sucesso'] == true) {
        _perfil = Map<String, dynamic>.from(resposta['dados']);
      }
    });

    _aviso(
      resposta['sucesso'] == true
          ? (_isDono ? 'Logo atualizada' : 'Foto atualizada')
          : resposta['erro'] ?? 'Não foi possível enviar a imagem',
      erro: resposta['sucesso'] != true,
    );
  }

  Future<void> _removerFoto() async {
    setState(() => _salvandoFoto = true);
    final resposta = await PerfilService.removerAvatar();
    if (!mounted) return;

    setState(() {
      _salvandoFoto = false;
      if (resposta['sucesso'] == true) _perfil?['avatar'] = null;
    });

    _aviso(
      resposta['sucesso'] == true
          ? 'Voltou ao ícone padrão'
          : resposta['erro'] ?? 'Não foi possível remover',
      erro: resposta['sucesso'] != true,
    );
  }

  void _abrirOpcoesDeFoto() {
    final temFoto = (_perfil?['avatar'] as String?)?.isNotEmpty == true;

    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (folha) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 8),
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppTheme.bordaCard,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 8),
            ListTile(
              leading: const Icon(Icons.photo_library_rounded,
                  color: AppTheme.ctaEntrar),
              title: Text(_isDono ? 'Escolher logo da galeria' : 'Escolher da galeria'),
              onTap: () {
                Navigator.pop(folha);
                _escolherFoto(ImageSource.gallery);
              },
            ),
            ListTile(
              leading:
                  const Icon(Icons.photo_camera_rounded, color: AppTheme.ctaEntrar),
              title: const Text('Tirar uma foto'),
              onTap: () {
                Navigator.pop(folha);
                _escolherFoto(ImageSource.camera);
              },
            ),
            if (temFoto)
              ListTile(
                leading: const Icon(Icons.delete_outline_rounded,
                    color: AppTheme.error),
                title: const Text('Remover',
                    style: TextStyle(color: AppTheme.error)),
                onTap: () {
                  Navigator.pop(folha);
                  _removerFoto();
                },
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  // ─── Nome ───────────────────────────────────────────────
  Future<void> _editarNome() async {
    final controle = TextEditingController(text: _perfil?['nome'] ?? '');

    final novo = await showDialog<String>(
      context: context,
      builder: (dialogo) => _DialogCampo(
        titulo: _isDono ? 'Nome da empresa' : 'Seu nome',
        descricao: 'É o nome que aparece no topo do aplicativo.',
        controle: controle,
        icone: Icons.badge_outlined,
      ),
    );
    if (novo == null || !mounted) return;

    final resposta = await PerfilService.editar(nome: novo);
    if (!mounted) return;

    if (resposta['sucesso'] == true) {
      setState(() => _perfil = Map<String, dynamic>.from(resposta['dados']));
      _aviso('Nome atualizado');
    } else {
      _aviso(resposta['erro'] ?? 'Não foi possível salvar', erro: true);
    }
  }

  Future<void> _editarEmail() async {
    final controle = TextEditingController(text: _perfil?['email'] ?? '');

    final novo = await showDialog<String>(
      context: context,
      builder: (dialogo) => _DialogCampo(
        titulo: 'E-mail de contato',
        descricao: 'Usado só para contato. Pode ficar em branco.',
        controle: controle,
        icone: Icons.alternate_email_rounded,
        obrigatorio: false,
        teclado: TextInputType.emailAddress,
      ),
    );
    if (novo == null || !mounted) return;

    final resposta = await PerfilService.editar(email: novo);
    if (!mounted) return;

    if (resposta['sucesso'] == true) {
      setState(() => _perfil = Map<String, dynamic>.from(resposta['dados']));
      _aviso('E-mail atualizado');
    } else {
      _aviso(resposta['erro'] ?? 'Não foi possível salvar', erro: true);
    }
  }

  // ─── Senha ──────────────────────────────────────────────
  Future<void> _trocarSenha() async {
    final trocou = await showDialog<bool>(
      context: context,
      builder: (_) => const _DialogSenha(),
    );
    if (trocou == true && mounted) _aviso('Senha alterada');
  }

  // ─── Sair ───────────────────────────────────────────────
  Future<void> _confirmarSaida() async {
    final sair = await showDialog<bool>(
      context: context,
      builder: (dialogo) => AlertDialog(
        backgroundColor: AppTheme.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Sair da conta',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.tituloBemVindo,
          ),
        ),
        content: Text(
          'Você precisará informar o CPF/CNPJ e a senha para entrar de novo.',
          style: TextStyle(
            fontSize: 13.5,
            height: 1.4,
            color: Colors.black.withValues(alpha: 0.65),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogo, false),
            child: const Text('Cancelar',
                style: TextStyle(color: AppTheme.hintCampo)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.error,
              minimumSize: const Size(0, 42),
            ),
            onPressed: () => Navigator.pop(dialogo, true),
            child: const Text('Sair'),
          ),
        ],
      ),
    );

    if (sair != true || !mounted) return;

    // Sem isso o lembrete continuaria tocando no aparelho depois da saída.
    await NotificacaoService.limpar();
    await AuthService.logout();
    if (!mounted) return;

    // Limpa a pilha: depois de sair não dá para voltar com o botão do sistema.
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
  }

  // ═══════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      appBar: AppBar(
        backgroundColor: AppTheme.white,
        surfaceTintColor: AppTheme.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppTheme.azulMedio),
        title: const Text(
          'Configurações',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: AppTheme.azulMedio,
          ),
        ),
      ),
      body: _buildCorpo(),
    );
  }

  Widget _buildCorpo() {
    if (_carregando) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaria),
      );
    }

    if (_perfil == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_rounded,
                  size: 40, color: AppTheme.textoFraco),
              const SizedBox(height: 12),
              Text(
                _erro ?? 'Não foi possível carregar seus dados',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13.5, color: AppTheme.textoFraco),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _carregar,
                child: const Text('Tentar de novo'),
              ),
            ],
          ),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      children: [
        _buildFoto(),
        const SizedBox(height: 24),
        const _TituloGrupo('Conta'),
        const SizedBox(height: 8),
        _grupo([
          _linha(
            icone: Icons.badge_outlined,
            titulo: _isDono ? 'Nome da empresa' : 'Nome',
            valor: _perfil!['nome'] ?? '',
            onTap: _editarNome,
          ),
          _linha(
            icone: Icons.alternate_email_rounded,
            titulo: 'E-mail',
            valor: (_perfil!['email'] as String?)?.isNotEmpty == true
                ? _perfil!['email']
                : 'Não informado',
            onTap: _editarEmail,
          ),
          _linha(
            icone: Icons.assignment_ind_outlined,
            titulo: _perfil!['documento_tipo'] == 'cnpj' ? 'CNPJ' : 'CPF',
            valor: _perfil!['documento'] ?? '',
            // Documento é a identidade da assinatura: quem valida é a
            // AquaSys, ao criar a conta. Por isso não é editável aqui.
            travado: true,
          ),
        ]),
        const SizedBox(height: 22),
        const _TituloGrupo('Segurança'),
        const SizedBox(height: 8),
        _grupo([
          _linha(
            icone: Icons.lock_outline_rounded,
            titulo: 'Senha',
            valor: 'Alterar minha senha',
            onTap: _trocarSenha,
          ),
        ]),
        const SizedBox(height: 28),
        OutlinedButton.icon(
          onPressed: _confirmarSaida,
          icon: const Icon(Icons.logout_rounded, size: 19),
          label: const Text('Sair da conta'),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppTheme.error,
            minimumSize: const Size(0, 50),
            side: const BorderSide(color: Color(0xFFF3C0C0)),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
        ),
      ],
    );
  }

  Widget _buildFoto() {
    final avatar = _perfil?['avatar'] as String?;

    return Center(
      child: Column(
        children: [
          Stack(
            children: [
              Container(
                width: 104,
                height: 104,
                decoration: BoxDecoration(
                  color: AppTheme.primaria,
                  borderRadius: BorderRadius.circular(26),
                  border: Border.all(color: AppTheme.white, width: 3),
                  boxShadow: AppTheme.sombraCard,
                ),
                clipBehavior: Clip.antiAlias,
                child: _salvandoFoto
                    ? const Center(
                        child: SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.4,
                            color: AppTheme.white,
                          ),
                        ),
                      )
                    : AvatarDaConta(
                        base64: avatar,
                        isDono: _isDono,
                        tamanho: 104,
                      ),
              ),
              Positioned(
                right: 0,
                bottom: 0,
                child: Material(
                  color: AppTheme.ctaEntrar,
                  shape: const CircleBorder(),
                  child: InkWell(
                    customBorder: const CircleBorder(),
                    onTap: _salvandoFoto ? null : _abrirOpcoesDeFoto,
                    child: const Padding(
                      padding: EdgeInsets.all(7),
                      child: Icon(Icons.photo_camera_rounded,
                          size: 17, color: AppTheme.white),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            _perfil?['nome'] ?? '',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 16.5,
              fontWeight: FontWeight.w700,
              color: AppTheme.azulMedio,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            _isDono ? 'Acesso empresarial' : 'Acesso cliente',
            style: const TextStyle(fontSize: 12.5, color: AppTheme.textoFraco),
          ),
        ],
      ),
    );
  }

  Widget _grupo(List<Widget> linhas) {
    // Material, e não Container com decoração: o ListTile pinta o próprio
    // fundo e a ondulação do toque no Material mais próximo acima dele.
    // Com um Container colorido no meio do caminho, a decoração fica na
    // frente e esconde o efeito — o framework avisa disso em modo de
    // depuração. O `shape` desenha a mesma moldura arredondada com a
    // mesma borda, então a aparência não muda; o que muda é que a
    // superfície que recebe o toque passa a ser visível.
    return Material(
      color: AppTheme.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: AppTheme.bordaCard),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          for (var i = 0; i < linhas.length; i++) ...[
            if (i > 0)
              const Divider(height: 1, thickness: 1, color: Color(0xFFF0F3F7)),
            linhas[i],
          ],
        ],
      ),
    );
  }

  Widget _linha({
    required IconData icone,
    required String titulo,
    required String valor,
    VoidCallback? onTap,
    bool travado = false,
  }) {
    return ListTile(
      onTap: travado ? null : onTap,
      leading: Icon(icone, size: 21, color: AppTheme.ctaEntrar),
      title: Text(
        titulo,
        style: const TextStyle(fontSize: 12, color: AppTheme.textoFraco),
      ),
      subtitle: Text(
        valor,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          fontSize: 14.5,
          fontWeight: FontWeight.w600,
          color: AppTheme.tituloBemVindo,
        ),
      ),
      trailing: travado
          ? const Icon(Icons.lock_outline_rounded,
              size: 17, color: AppTheme.hintCampo)
          : const Icon(Icons.chevron_right_rounded,
              size: 20, color: AppTheme.textoFraco),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// AVATAR REAPROVEITÁVEL
// ═══════════════════════════════════════════════════════════
/// Foto da conta, com o ícone padrão como reserva.
///
/// Fica aqui, e não no cabeçalho, porque as duas telas mostram a mesma
/// imagem — e o base64 pode vir quebrado do banco, caso em que desenhar
/// o ícone é melhor do que estourar um erro na cara do usuário.
class AvatarDaConta extends StatelessWidget {
  final String? base64;
  final bool isDono;
  final double tamanho;

  const AvatarDaConta({
    super.key,
    required this.base64,
    required this.isDono,
    required this.tamanho,
  });

  @override
  Widget build(BuildContext context) {
    final padrao = Center(
      child: Icon(
        isDono ? Icons.business_rounded : Icons.person_rounded,
        color: AppTheme.white,
        size: tamanho * 0.5,
      ),
    );

    if (base64 == null || base64!.isEmpty) return padrao;

    try {
      return Image.memory(
        base64Decode(base64!),
        width: tamanho,
        height: tamanho,
        fit: BoxFit.cover,
        gaplessPlayback: true,
        errorBuilder: (_, _, _) => padrao,
      );
    } catch (_) {
      return padrao;
    }
  }
}

// ═══════════════════════════════════════════════════════════
// DIÁLOGOS
// ═══════════════════════════════════════════════════════════
class _TituloGrupo extends StatelessWidget {
  final String texto;
  const _TituloGrupo(this.texto);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(left: 4),
        child: Text(
          texto.toUpperCase(),
          style: const TextStyle(
            fontSize: 11.5,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.6,
            color: AppTheme.textoFraco,
          ),
        ),
      );
}

/// Diálogo de um campo só — usado pelo nome e pelo e-mail.
class _DialogCampo extends StatefulWidget {
  final String titulo;
  final String descricao;
  final TextEditingController controle;
  final IconData icone;
  final bool obrigatorio;
  final TextInputType teclado;

  const _DialogCampo({
    required this.titulo,
    required this.descricao,
    required this.controle,
    required this.icone,
    this.obrigatorio = true,
    this.teclado = TextInputType.text,
  });

  @override
  State<_DialogCampo> createState() => _DialogCampoState();
}

class _DialogCampoState extends State<_DialogCampo> {
  final _formKey = GlobalKey<FormState>();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Text(
        widget.titulo,
        style: const TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w700,
          color: AppTheme.tituloBemVindo,
        ),
      ),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.descricao,
              style: const TextStyle(fontSize: 12.5, color: AppTheme.textoFraco),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: widget.controle,
              autofocus: true,
              keyboardType: widget.teclado,
              decoration: InputDecoration(
                prefixIcon: Icon(widget.icone, size: 20),
              ),
              validator: (v) {
                if (!widget.obrigatorio) return null;
                return (v == null || v.trim().length < 2)
                    ? 'Informe pelo menos 2 caracteres'
                    : null;
              },
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar',
              style: TextStyle(color: AppTheme.hintCampo)),
        ),
        ElevatedButton(
          onPressed: () {
            if (!_formKey.currentState!.validate()) return;
            Navigator.pop(context, widget.controle.text.trim());
          },
          child: const Text('Salvar'),
        ),
      ],
    );
  }
}

class _DialogSenha extends StatefulWidget {
  const _DialogSenha();

  @override
  State<_DialogSenha> createState() => _DialogSenhaState();
}

class _DialogSenhaState extends State<_DialogSenha> {
  final _formKey = GlobalKey<FormState>();
  final _atualCtrl = TextEditingController();
  final _novaCtrl = TextEditingController();
  final _confirmaCtrl = TextEditingController();

  bool _salvando = false;
  String? _erro;

  @override
  void dispose() {
    _atualCtrl.dispose();
    _novaCtrl.dispose();
    _confirmaCtrl.dispose();
    super.dispose();
  }

  Future<void> _salvar() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _salvando = true;
      _erro = null;
    });

    final resposta = await PerfilService.trocarSenha(
      senhaAtual: _atualCtrl.text,
      senhaNova: _novaCtrl.text,
    );
    if (!mounted) return;

    if (resposta['sucesso'] == true) {
      Navigator.pop(context, true);
      return;
    }

    setState(() {
      _salvando = false;
      _erro = resposta['erro'] ?? 'Não foi possível alterar a senha';
    });
  }

  Widget _campo(
    TextEditingController controle,
    String rotulo, {
    String? Function(String?)? validator,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: controle,
        obscureText: true,
        decoration: InputDecoration(
          labelText: rotulo,
          prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20),
        ),
        validator: validator,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: const Text(
        'Alterar senha',
        style: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w700,
          color: AppTheme.tituloBemVindo,
        ),
      ),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _campo(
                _atualCtrl,
                'Senha atual',
                validator: (v) =>
                    (v == null || v.isEmpty) ? 'Informe a senha atual' : null,
              ),
              _campo(
                _novaCtrl,
                'Nova senha',
                validator: (v) => (v == null || v.length < 6)
                    ? 'A nova senha precisa de 6 caracteres ou mais'
                    : null,
              ),
              _campo(
                _confirmaCtrl,
                'Repita a nova senha',
                validator: (v) =>
                    v != _novaCtrl.text ? 'As senhas não coincidem' : null,
              ),
              if (_erro != null)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(
                    _erro!,
                    style: const TextStyle(fontSize: 12.5, color: AppTheme.error),
                  ),
                ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _salvando ? null : () => Navigator.pop(context),
          child: const Text('Cancelar',
              style: TextStyle(color: AppTheme.hintCampo)),
        ),
        ElevatedButton(
          onPressed: _salvando ? null : _salvar,
          child: _salvando
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                      strokeWidth: 2.2, color: AppTheme.white),
                )
              : const Text('Alterar'),
        ),
      ],
    );
  }
}
