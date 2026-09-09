-- ═══════════════════════════════════════════════════════════
-- 006 — Foto de perfil / logo da conta
--
-- O cabeçalho de todas as telas mostrava um ícone genérico. A
-- loja quer a própria logo ali, e o cliente, a foto dele.
--
-- A imagem fica gravada em base64 na própria linha do usuário,
-- e não num serviço de arquivos. É a escolha certa para o
-- tamanho deste projeto: são poucos KB por conta (o app reduz a
-- imagem antes de enviar e a API recusa acima de 400 KB), não
-- há bucket para manter, e a foto acompanha o backup do banco
-- sem nenhum passo extra.
--
-- Se um dia a base crescer a ponto de isso pesar, a saída é
-- mover para armazenamento de objetos e deixar aqui só a URL —
-- a coluna já é TEXT, então cabe URL sem nova migração.
--
-- Seguro de rodar mais de uma vez.
-- ═══════════════════════════════════════════════════════════

BEGIN;

ALTER TABLE usuario ADD COLUMN IF NOT EXISTS avatar TEXT;

COMMENT ON COLUMN usuario.avatar IS
    'Foto de perfil ou logo, em base64 puro (sem prefixo data:). Nulo = ícone padrão.';

COMMIT;
