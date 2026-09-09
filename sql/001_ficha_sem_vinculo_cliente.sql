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
