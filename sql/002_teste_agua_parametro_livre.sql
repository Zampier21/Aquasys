-- ═══════════════════════════════════════════════════════════
-- 002 — Testes de água aceitam parâmetro personalizado
--
-- A aba "Testes de água" da ficha tem um botão "+ Adicionar":
-- o técnico pode anotar um teste que não está na lista padrão.
-- O CHECK antigo travava `parametro` nos 11 códigos fixos e
-- recusava qualquer outro.
--
-- Os 11 códigos continuam sendo o padrão — a API os entrega em
-- /fichas/catalogos com o rótulo longo para a tela. O que muda
-- é que agora cabe um item fora da lista.
--
-- Seguro de rodar mais de uma vez.
-- ═══════════════════════════════════════════════════════════

BEGIN;

ALTER TABLE teste_agua
    DROP CONSTRAINT IF EXISTS teste_agua_parametro_check;

COMMIT;
