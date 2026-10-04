-- ═══════════════════════════════════════════════════════════
-- 011 — Exclusão lógica do aquário e da ficha de manutenção
--
-- Até aqui, excluir um aquário apagava a linha de verdade, e as
-- chaves estrangeiras em CASCADE levavam junto tudo o que pendia
-- dele: parâmetros registrados, testes de água, alertas e o
-- povoamento. Um toque errado destruía o histórico inteiro, sem
-- volta. O mesmo valia para a ficha de manutenção, que é o
-- registro de uma visita que aconteceu e não deveria sumir.
--
-- A coluna `ativo` já era o padrão da casa em usuario, curso,
-- especie e cliente_manutencao. Estende-se às duas tabelas que
-- faltavam, em vez de inventar uma convenção nova.
--
-- O dado continua no banco; o que muda é que as consultas passam
-- a filtrar por `ativo`. Quem excluiu por engano reativa pela
-- própria tela, como já acontece com o acesso do cliente.
-- ═══════════════════════════════════════════════════════════

ALTER TABLE aquario
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE ficha_manutencao
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

-- As listagens sempre filtram por ativo e por dono. Sem índice, a
-- varredura cresce com o total de linhas da instalação inteira, e
-- não com o que pertence àquela loja.
CREATE INDEX IF NOT EXISTS idx_aquario_usuario_ativo
    ON aquario (usuario_id, ativo);

CREATE INDEX IF NOT EXISTS idx_ficha_dono_ativo
    ON ficha_manutencao (dono_id, ativo);

COMMENT ON COLUMN aquario.ativo IS
    'Falso quando o aquário foi excluído pelo usuário. A linha e todo o '
    'histórico dependente permanecem, e a exclusão pode ser desfeita.';

COMMENT ON COLUMN ficha_manutencao.ativo IS
    'Falso quando a ficha foi arquivada. Atende ao RF010: a visita '
    'registrada sai da lista sem que o histórico seja perdido.';
