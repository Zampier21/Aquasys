-- ═══════════════════════════════════════════════════════════
-- 003 — Cursos passam a ter aulas (vídeos do YouTube)
--
-- A tabela `curso` guardava só metadado: não havia onde pôr o
-- conteúdo. Agora um curso é uma coleção ordenada de aulas, e
-- cada aula é um vídeo do YouTube identificado pelo `youtube_id`
-- (os 11 caracteres depois de "watch?v=").
--
-- Também entra `dono_id`: nulo = curso global do AquaSys, visível
-- a todos; preenchido = curso próprio daquela loja.
--
-- Seguro de rodar mais de uma vez.
-- ═══════════════════════════════════════════════════════════

BEGIN;

-- ─── curso ─────────────────────────────────────────────────
ALTER TABLE curso
    ADD COLUMN IF NOT EXISTS dono_id UUID REFERENCES usuario(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS ativo   BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_curso_dono ON curso (dono_id);

-- ─── aula ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aula (
    id          UUID PRIMARY KEY,
    curso_id    UUID NOT NULL REFERENCES curso(id) ON DELETE CASCADE,
    titulo      VARCHAR(200) NOT NULL,
    -- Só o id do vídeo, nunca a URL inteira: assim a mesma linha
    -- serve para o player, para a miniatura e para o link externo.
    youtube_id  VARCHAR(20) NOT NULL,
    canal       VARCHAR(120),
    miniatura_url VARCHAR(255),
    ordem       INTEGER NOT NULL DEFAULT 0,
    criado_em   TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT uq_aula_curso_video UNIQUE (curso_id, youtube_id)
);

CREATE INDEX IF NOT EXISTS idx_aula_curso ON aula (curso_id, ordem);

-- ─── progresso por aula ────────────────────────────────────
-- Fonte da verdade do progresso. O `percentual` de progresso_curso
-- vira cache recalculado a partir daqui a cada marcação.
CREATE TABLE IF NOT EXISTS progresso_aula (
    id            UUID PRIMARY KEY,
    usuario_id    UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    aula_id       UUID NOT NULL REFERENCES aula(id) ON DELETE CASCADE,
    concluida     BOOLEAN NOT NULL DEFAULT FALSE,
    atualizado_em TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT uq_progresso_aula UNIQUE (usuario_id, aula_id)
);

CREATE INDEX IF NOT EXISTS idx_progresso_aula_usuario ON progresso_aula (usuario_id);

COMMIT;
