BEGIN;

CREATE TABLE IF NOT EXISTS cliente_manutencao (
    id       UUID PRIMARY KEY,
    dono_id  UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,

    -- Contato
    nome      VARCHAR(150) NOT NULL,
    telefone  VARCHAR(30),
    endereco  VARCHAR(250),

    -- Instalação: repete de visita em visita, então vem daqui
    -- pré-preenchida na ficha (e a ficha pode divergir se precisar).
    tipo_instalacao VARCHAR(20),
    volume_litros   INTEGER,
    agua_doce       BOOLEAN,

    observacoes   TEXT,
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMP,

    CONSTRAINT chk_volume_manutencao CHECK (volume_litros IS NULL OR volume_litros > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cliente_manutencao_nome
    ON cliente_manutencao (dono_id, lower(nome));

-- ─── ficha aponta para o cadastro ──────────────────────────
ALTER TABLE ficha_manutencao
    ADD COLUMN IF NOT EXISTS cliente_id UUID
        REFERENCES cliente_manutencao(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ficha_cliente
    ON ficha_manutencao (cliente_id);


COMMIT;
