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
