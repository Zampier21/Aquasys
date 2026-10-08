-- ═══════════════════════════════════════════════════════════
-- 014 — Sessão que sobrevive à expiração do token de acesso
--
-- O token de acesso vale uma hora. É um prazo curto de propósito:
-- se ele vazar, vaza por pouco tempo, e o servidor não guarda
-- estado de sessão, o que é a propriedade do estilo REST que
-- permite replicar o servidor sem coordenação.
--
-- O problema é que, na prática, isso jogava o usuário de volta na
-- tela de login a cada hora. Para um aquarista que abre o
-- aplicativo três vezes por semana, significa digitar a senha
-- toda vez.
--
-- A saída conhecida é o par de tokens: o de acesso continua curto
-- e sem estado, e um segundo token, de longa duração, serve só
-- para pedir um novo. Este é guardado, e é o que esta tabela
-- registra.
--
-- ─── Por que não basta alongar o token de acesso ───────────
-- Porque um JWT não se revoga. Uma vez emitido com validade de
-- trinta dias, vale trinta dias para quem o tiver, e o servidor
-- não tem onde anotar que aquele token não serve mais. Perder o
-- celular significaria perder a conta até o prazo acabar.
-- Com a sessão em tabela, revogar é um UPDATE.
--
-- ─── Por que o hash, e não o token ─────────────────────────
-- Guarda-se o SHA-256 do token de renovação, nunca ele mesmo. A
-- razão é a mesma da senha: se este banco vazar, o que o atacante
-- encontra não serve para entrar em lugar nenhum. É a coluna
-- `senha_hash` aplicada a outro segredo.
--
-- ─── Por que `usado_em` ────────────────────────────────────
-- O token de renovação é rotacionado: cada uso emite um novo e
-- marca o antigo. Se um token já usado reaparecer, há duas cópias
-- em circulação — o aparelho legítimo e outro. Nesse caso não dá
-- para saber qual é qual, e a resposta é derrubar todas as
-- sessões daquele usuário e exigir login. É a detecção de reúso
-- recomendada para rotação de token.
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sessao (
    id          UUID PRIMARY KEY,
    usuario_id  UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    hash        VARCHAR(64) NOT NULL UNIQUE,
    criado_em   TIMESTAMP NOT NULL DEFAULT now(),
    expira_em   TIMESTAMP NOT NULL,
    usado_em    TIMESTAMP,
    revogado_em TIMESTAMP
);

-- A renovação busca pelo hash, que já é único. O índice por usuário
-- serve à revogação em massa, que varre todas as sessões de uma conta.
CREATE INDEX IF NOT EXISTS idx_sessao_usuario
    ON sessao (usuario_id, revogado_em);

COMMENT ON TABLE sessao IS
    'Token de renovação de cada aparelho conectado. Uma linha por '
    'sessão ativa; o token em si não é guardado, apenas seu hash.';

COMMENT ON COLUMN sessao.hash IS
    'SHA-256 do token de renovação. O token só existe no aparelho.';

COMMENT ON COLUMN sessao.usado_em IS
    'Quando este token foi trocado por outro. Preenchido significa '
    'que ele não vale mais; se reaparecer, há cópia em circulação e '
    'todas as sessões do usuário são revogadas.';

COMMENT ON COLUMN sessao.revogado_em IS
    'Quando a sessão foi encerrada, por logout ou por suspeita de '
    'reúso. Sessão revogada não renova nada.';
