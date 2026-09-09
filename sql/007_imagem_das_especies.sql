-- ═══════════════════════════════════════════════════════════
-- 007 — Banco de imagens do catálogo de espécies
--
-- O app mostrava um ícone genérico de peixe para toda espécie.
-- Empacotar as fotos dentro do Flutter engordaria o APK sem
-- limite: são muitas espécies, e cada nova exigiria publicar
-- uma versão nova do aplicativo. Aqui a foto entra pelo banco,
-- e o app enxerga na hora.
--
-- Fica em tabela separada de propósito. `especie` é lida em
-- toda listagem do catálogo; se os bytes morassem lá, cada
-- SELECT arrastaria megabytes sem ninguém pedir.
--
-- Duas versões da mesma foto, para não trafegar 100 KB onde
-- cabem 10:
--   miniatura — quadrada, o círculo da lista;
--   completa  — proporção original, o card aberto.
--
-- As colunas de crédito não são enfeite: as fotos vêm do
-- Wikimedia Commons sob licença Creative Commons, que exige
-- citar autor e licença onde a imagem aparece.
--
-- Seguro de rodar mais de uma vez.
-- ═══════════════════════════════════════════════════════════

BEGIN;

CREATE TABLE IF NOT EXISTS especie_imagem (
    especie_id      UUID PRIMARY KEY REFERENCES especie(id) ON DELETE CASCADE,

    miniatura       BYTEA NOT NULL,
    completa        BYTEA NOT NULL,
    mime            VARCHAR(30) NOT NULL DEFAULT 'image/jpeg',

    -- sha256 da imagem completa: vira o ETag, e é como o script
    -- percebe que a origem não mudou e evita regravar à toa.
    hash            CHAR(64) NOT NULL,

    largura         INTEGER,
    altura          INTEGER,
    bytes_miniatura INTEGER,
    bytes_completa  INTEGER,

    -- Crédito exigido pela licença
    fonte           TEXT,           -- página de origem da foto
    autor           VARCHAR(300),
    licenca         VARCHAR(80),
    licenca_url     TEXT,

    atualizado_em   TIMESTAMP NOT NULL DEFAULT now()
);

COMMENT ON TABLE especie_imagem IS
    'Foto de cada espécie, em duas resoluções. Separada de `especie` para não pesar as listagens.';

COMMIT;
