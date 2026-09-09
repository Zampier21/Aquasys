-- ═══════════════════════════════════════════════════════════
-- 005 — Cadastro leve do cliente de manutenção
--
-- A ficha atende quem a loja visita em casa, que não é a mesma
-- lista de quem tem acesso ao app. Até aqui o nome era texto
-- livre e nada se reaproveitava: na terceira visita ao mesmo
-- cliente, o técnico redigitava tudo.
--
-- Agora o contato é gravado uma vez e reutilizado. O que muda a
-- cada visita continua na ficha; o que é do cliente (contato e
-- descrição da instalação) fica aqui.
--
-- Isto NÃO é a antiga tabela `cliente`, removida na 004: aquela
-- guardava senha e dava acesso ao aplicativo. Esta é só agenda de
-- quem recebe manutenção — sem login, sem senha.
--
-- Seguro de rodar mais de uma vez.
-- ═══════════════════════════════════════════════════════════

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

-- Dois clientes de lojas diferentes podem ter o mesmo nome; dentro
-- da mesma loja, não — é o que evita duplicar o cadastro sem querer.
CREATE UNIQUE INDEX IF NOT EXISTS uq_cliente_manutencao_nome
    ON cliente_manutencao (dono_id, lower(nome));

-- ─── ficha aponta para o cadastro ──────────────────────────
ALTER TABLE ficha_manutencao
    ADD COLUMN IF NOT EXISTS cliente_id UUID
        REFERENCES cliente_manutencao(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ficha_cliente
    ON ficha_manutencao (cliente_id);

-- `nome_cliente` continua na ficha de propósito: é o retrato do nome
-- no dia do atendimento. Cliente renomeado depois não reescreve a
-- história das fichas antigas.

COMMIT;
