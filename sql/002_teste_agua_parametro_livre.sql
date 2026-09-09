BEGIN;

ALTER TABLE teste_agua
    DROP CONSTRAINT IF EXISTS teste_agua_parametro_check;

COMMIT;
