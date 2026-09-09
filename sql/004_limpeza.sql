-- ═══════════════════════════════════════════════════════════
-- 004 — Remove o que a auditoria apontou como morto
--
-- Nada aqui é usado por rota, serviço ou tela. Cada bloco diz
-- por que sai, para o histórico não virar adivinhação.
--
-- Seguro de rodar mais de uma vez.
-- ═══════════════════════════════════════════════════════════

BEGIN;

-- ─── grupo_aquario ─────────────────────────────────────────
-- Zero referências em rotas e serviços. `aquario.grupo_id` era
-- aceito e gravado, mas nunca existiu endpoint que criasse um
-- grupo, e o app nunca enviou o campo.
ALTER TABLE aquario DROP COLUMN IF EXISTS grupo_id;
DROP TABLE IF EXISTS grupo_aquario;

-- ─── historico_aquario ─────────────────────────────────────
-- Era lido para preencher "última manutenção", mas nenhuma linha
-- do projeto jamais escreveu nele: o campo era sempre nulo e o
-- card mostrava "Sem registro" para sempre.
-- Para ressuscitar isso direito é preciso um evento de manutenção
-- de verdade, ligado a um aquário — hoje a ficha técnica usa nome
-- de cliente livre e não aponta para aquário nenhum.
DROP TABLE IF EXISTS historico_aquario;

-- ─── permissao ─────────────────────────────────────────────
-- Única tabela sem modelo. O controle de acesso real é o par
-- usuario.tipo + usuario.dono_id, que cobre o que o produto pede.
DROP TABLE IF EXISTS permissao;

-- ─── cliente ───────────────────────────────────────────────
-- O acesso do cliente vive em `usuario` (tipo='cliente' + dono_id):
-- é de lá que o login lê e para lá que aquario.usuario_id aponta.
-- A tabela `cliente` ficou vazia, e `ficha_manutencao.cliente_id`
-- deixou de ser preenchido quando a ficha passou a usar nome livre.
ALTER TABLE ficha_manutencao DROP COLUMN IF EXISTS cliente_id;
DROP TABLE IF EXISTS cliente;

-- ─── colunas de curso sem leitor ───────────────────────────
-- `autor` nunca foi preenchido (o canal fica em aula.canal) e
-- `duracao_min` não tem de onde vir: o oEmbed não devolve duração
-- e digitar à mão seria atrito. A tela mostra o número de aulas.
ALTER TABLE curso
    DROP COLUMN IF EXISTS autor,
    DROP COLUMN IF EXISTS duracao_min;

COMMIT;
