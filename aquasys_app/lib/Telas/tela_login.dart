import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../Tema/app_tema.dart';
import '../Services/auth_service.dart';
import '../utils/documento.dart';
import 'tela_inicial.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey         = GlobalKey<FormState>();
  final _cpfController   = TextEditingController();
  final _senhaController = TextEditingController();
  bool _senhaVisivel     = false;
  bool _carregando       = false;
  String? _erro;
  TipoDocumento _tipoDocumento = TipoDocumento.invalido;

  @override
  void initState() {
    super.initState();
    // Redesenha o campo quando o documento passa de CPF para CNPJ.
    _cpfController.addListener(() {
      final tipo = tipoDocumento(_cpfController.text);
      if (tipo != _tipoDocumento) setState(() => _tipoDocumento = tipo);
    });
  }

  @override
  void dispose() {
    _cpfController.dispose();
    _senhaController.dispose();
    super.dispose();
  }

  void _entrar() async {
    setState(() => _erro = null);
    if (!_formKey.currentState!.validate()) return;
    setState(() => _carregando = true);

    final resultado = await AuthService.login(
      cpfCnpj: _cpfController.text.trim(),
      senha: _senhaController.text,
    );
    setState(() => _carregando = false);
    if (!mounted) return;

    if (resultado['sucesso']) {
      final tipo = resultado['tipo'];
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => TelaInicial(tipoUsuario: tipo),
        ),
      );
    } else {
      setState(() => _erro = resultado['erro']);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundApp,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [

                // ─── Logo ─────────────────────────────────
                Image.asset(
                  'assets/images/logo.png',
                  width: 180,
                  height: 180,
                  fit: BoxFit.contain,
                ),
                const SizedBox(height: 32),

                // ─── Card de login ────────────────────────
                Container(
                  decoration: BoxDecoration(
                    color: AppTheme.backgroundCard,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppTheme.bordaCard, width: 1),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF023E8A).withValues(alpha: 0.08),
                        blurRadius: 32,
                        offset: const Offset(0, 8),
                      ),
                      BoxShadow(
                        color: const Color(0xFF0096C7).withValues(alpha: 0.05),
                        blurRadius: 16,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  padding: const EdgeInsets.all(28),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [

                        // Título
                        const Center(
                          child: Text(
                            'Bem-vindo',
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.tituloBemVindo,
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Center(
                          child: Text(
                            'Entre com suas credenciais de acesso',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 13,
                              color: AppTheme.subtitulo,
                            ),
                          ),
                        ),
                        const SizedBox(height: 28),

                        // Erro da API
                        if (_erro != null) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(
                                vertical: 12, horizontal: 16),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFEBEE),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                  color: AppTheme.error, width: 1),
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
                                      fontSize: 13,
                                      color: AppTheme.error,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 20),
                        ],

                        // Label CPF/CNPJ
                        const Text(
                          'CPF/CNPJ',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.labelCampo,
                          ),
                        ),
                        const SizedBox(height: 6),
                        TextFormField(
                          controller: _cpfController,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                            CpfCnpjInputFormatter(),
                          ],
                          style: const TextStyle(
                              fontSize: 14, color: AppTheme.textoFraco),
                          decoration: InputDecoration(
                            hintText: '999.999.999-99 ou 99.999.999/0001-99',
                            // Mostra ao vivo o que o app reconheceu enquanto digita.
                            suffixIcon: _tipoDocumento == TipoDocumento.invalido
                                ? null
                                : Padding(
                                    padding: const EdgeInsets.only(right: 14),
                                    child: Align(
                                      widthFactor: 1,
                                      child: Text(
                                        _tipoDocumento == TipoDocumento.cpf
                                            ? 'CPF'
                                            : 'CNPJ',
                                        style: const TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.w700,
                                          color: AppTheme.primaria,
                                        ),
                                      ),
                                    ),
                                  ),
                          ),
                          // No login não conferimos dígito verificador: quem
                          // define o documento válido é o cadastro.
                          validator: (v) => validarDocumento(
                            v,
                            exigirDigitoVerificador: false,
                          ),
                        ),
                        const SizedBox(height: 20),

                        // Label Senha
                        const Text(
                          'Senha',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.labelCampo,
                          ),
                        ),
                        const SizedBox(height: 6),
                        TextFormField(
                          controller: _senhaController,
                          obscureText: !_senhaVisivel,
                          style: const TextStyle(
                              fontSize: 14, color: AppTheme.hintCampo),
                          decoration: InputDecoration(
                            hintText: '••••••••',
                            suffixIcon: IconButton(
                              icon: Icon(
                                _senhaVisivel
                                    ? Icons.visibility_off_outlined
                                    : Icons.visibility_outlined,
                                color: AppTheme.hintCampo,
                                size: 20,
                              ),
                              onPressed: () => setState(
                                  () => _senhaVisivel = !_senhaVisivel),
                            ),
                          ),
                          validator: (v) {
                            if (v == null || v.isEmpty) return 'Informe a senha';
                            if (v.length < 6) return 'Mínimo de 6 caracteres';
                            return null;
                          },
                        ),
                        const SizedBox(height: 28),

                        // Botão Entrar
                        ElevatedButton(
                          onPressed: _carregando ? null : _entrar,
                          child: _carregando
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                    color: AppTheme.white,
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Text('Entrar'),
                        ),
                        const SizedBox(height: 24),

                        // Divider
                        const Divider(color: AppTheme.bordaCard, thickness: 1),
                        const SizedBox(height: 20),

                        // Não tem acesso
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(
                              vertical: 16, horizontal: 12),
                          decoration: BoxDecoration(
                            color: AppTheme.backgroundLabel,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                                color: AppTheme.bordaCard, width: 1),
                          ),
                          child: const Column(
                            children: [
                              Text(
                                'Não Tem Acesso?',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.tituloBemVindo,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'Entre em contato com sua loja de aquarismo parceira',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 12,
                                  color: AppTheme.subtitulo,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // Rodapé
                const SizedBox(height: 32),
                const Text(
                  '2026 AquaSys. ©Todos os direitos reservados',
                  style: TextStyle(fontSize: 11, color: Color(0xFF737373)),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}