import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../Tema/app_tema.dart';
import '../config.dart';

/// Foto de uma espécie, servida pela API.
class FotoEspecie extends StatelessWidget {
  final String? caminho;
  final Color cor;
  final double tamanho;

  /// Círculo na lista de espécies; quadrado arredondado nos habitantes.
  final bool circular;

  /// Quanto do ícone de reserva ocupa o espaço, quando não há foto.
  final double proporcaoIcone;

  const FotoEspecie({
    super.key,
    required this.caminho,
    required this.cor,
    required this.tamanho,
    this.circular = true,
    this.proporcaoIcone = 0.43,
  });

  BorderRadius get _raio => BorderRadius.circular(circular ? tamanho / 2 : 10);

  Widget _reserva() {
    return Container(
      width: tamanho,
      height: tamanho,
      decoration: BoxDecoration(color: cor, borderRadius: _raio),
      child: Center(
        child: FaIcon(
          FontAwesomeIcons.fish,
          size: tamanho * proporcaoIcone,
          color: AppTheme.white,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (caminho == null || caminho!.isEmpty) return _reserva();

    return ClipRRect(
      borderRadius: _raio,
      child: CachedNetworkImage(
        imageUrl: '${Config.apiUrl}$caminho',
        width: tamanho,
        height: tamanho,
        fit: BoxFit.cover,
        // Guarda em disco: a lista de espécies é longa e reaberta o tempo
        // todo. Sem isso, cada volta à aba Peixes baixaria tudo de novo.
        fadeInDuration: const Duration(milliseconds: 180),
        placeholder: (_, _) => Container(
          width: tamanho,
          height: tamanho,
          decoration: BoxDecoration(
            color: cor.withValues(alpha: 0.18),
            borderRadius: _raio,
          ),
        ),
        errorWidget: (_, _, _) => _reserva(),
      ),
    );
  }
}

/// Foto grande da espécie, para o card aberto.
///
/// Vem com a linha de crédito porque as fotos são do Wikimedia Commons,
/// sob licença Creative Commons: citar autor e licença onde a imagem
/// aparece é condição de uso, não gentileza.
class FotoEspecieGrande extends StatelessWidget {
  final String? caminho;
  final String? credito;

  const FotoEspecieGrande({super.key, required this.caminho, this.credito});

  @override
  Widget build(BuildContext context) {
    if (caminho == null || caminho!.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: CachedNetworkImage(
                imageUrl: '${Config.apiUrl}$caminho',
                fit: BoxFit.cover,
                placeholder: (_, _) => Container(
                  color: AppTheme.superficieAzul,
                ),
                // Sem foto grande o card simplesmente não a mostra: um
                // retângulo de erro no meio da ficha do peixe seria pior
                // do que a ausência dela.
                errorWidget: (_, _, _) => const SizedBox.shrink(),
              ),
            ),
          ),
          if (credito != null && credito!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4, left: 2),
              child: Text(
                'Foto: $credito',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 10.5, color: AppTheme.hintCampo),
              ),
            ),
        ],
      ),
    );
  }
}
