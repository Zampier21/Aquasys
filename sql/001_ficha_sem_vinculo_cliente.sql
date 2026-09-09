-- ═══════════════════════════════════════════════════════════
-- 001 — Ficha técnica deixa de depender do cliente cadastrado
--
-- Motivo: a ficha é controle de manutenção. Quem contrata
-- manutenção nem sempre tem acesso ao app, então o nome do
-- cliente passa a ser texto livre e cliente_id vira opcional
-- (fica só para quando o atendido também tem login).
--
-- Seguro de rodar mais de uma vez.
-- ═══════════════════════════════════════════════════════════

BEGIN;

-- ─── ficha_manutencao ──────────────────────────────────────
ALTER TABLE ficha_manutencao
    ADD COLUMN IF NOT EXISTS nome_cliente     VARCHAR(150),
    ADD COLUMN IF NOT EXISTS data_atendimento DATE,
    ADD COLUMN IF NOT EXISTS tipo_instalacao  VARCHAR(20),
    ADD COLUMN IF NOT EXISTS atualizado_em    TIMESTAMP;

-- Fichas antigas (se houver) herdam o nome do cliente vinculado.
UPDATE ficha_manutencao f
   SET nome_cliente = c.nome
  FROM cliente c
 WHERE f.cliente_id = c.id
   AND f.nome_cliente IS NULL;

UPDATE ficha_manutencao
   SET nome_cliente = 'Sem nome'
 WHERE nome_cliente IS NULL;

ALTER TABLE ficha_manutencao
    ALTER COLUMN nome_cliente SET NOT NULL,
    ALTER COLUMN cliente_id   DROP NOT NULL;

-- Horário é anotado como "14:30" na ficha de papel; TIMESTAMP
-- obrigava a inventar uma data junto.
-- O IF evita quebrar se o script rodar de novo (to_char não
-- aceita uma coluna que já virou texto).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'ficha_manutencao'
           AND column_name = 'horario_chegada'
           AND data_type LIKE 'timestamp%'
    ) THEN
        ALTER TABLE ficha_manutencao
            ALTER COLUMN horario_chegada TYPE VARCHAR(10)
                USING to_char(horario_chegada, 'HH24:MI'),
            ALTER COLUMN horario_saida TYPE VARCHAR(10)
                USING to_char(horario_saida, 'HH24:MI');
    END IF;
END $$;

-- ─── teste_agua ────────────────────────────────────────────
-- VARCHAR(20) não cabe "TDS (Sólidos Totais Dissolvidos)".
ALTER TABLE teste_agua
    ALTER COLUMN parametro TYPE VARCHAR(60);

COMMIT;
