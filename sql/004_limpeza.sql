BEGIN;

-- ─── grupo_aquario ─────────────────────────────────────────
ALTER TABLE aquario DROP COLUMN IF EXISTS grupo_id;
DROP TABLE IF EXISTS grupo_aquario;

-- ─── historico_aquario ─────────────────────────────────────
DROP TABLE IF EXISTS historico_aquario;

-- ─── permissao ─────────────────────────────────────────────
DROP TABLE IF EXISTS permissao;

-- ─── cliente ───────────────────────────────────────────────
ALTER TABLE ficha_manutencao DROP COLUMN IF EXISTS cliente_id;
DROP TABLE IF EXISTS cliente;

-- ─── colunas de curso sem leitor ───────────────────────────
ALTER TABLE curso
    DROP COLUMN IF EXISTS autor,
    DROP COLUMN IF EXISTS duracao_min;

COMMIT;
