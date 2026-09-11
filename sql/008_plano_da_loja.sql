-- ═══════════════════════════════════════════════════════════
-- 008 — Plano da assinatura e teto de acessos
--
-- A loja cria os acessos dos próprios clientes. Sem teto, uma
-- assinatura só atenderia uma rede inteira, e o modelo B2B2C
-- deixaria de se sustentar: quem paga é a loja, e o que ela
-- compra é uma quantidade de acessos.
--
-- Guarda-se aqui apenas QUAL é o plano. Quantos acessos cada
-- plano concede fica em app/core/planos.py, de modo que a régua
-- comercial possa mudar sem migração de banco nem versão nova
-- do aplicativo.
--
-- A coluna aceita nulo de propósito: é o que o cliente guarda
-- (quem assina é a loja) e é o que as contas anteriores a esta
-- migração têm. O código trata nulo como o plano padrão.
-- ═══════════════════════════════════════════════════════════

ALTER TABLE usuario
    ADD COLUMN IF NOT EXISTS plano VARCHAR(20);

-- Um plano fora da lista faria o teto cair no padrão sem ninguém
-- perceber. A restrição impede que isso chegue ao banco por
-- qualquer caminho, inclusive os que não passam pela aplicação.
ALTER TABLE usuario
    DROP CONSTRAINT IF EXISTS chk_plano;

ALTER TABLE usuario
    ADD CONSTRAINT chk_plano
    CHECK (plano IS NULL OR plano IN ('basico', 'profissional', 'ilimitado'));

-- As lojas que já existem passam para o plano básico. É o teto mais
-- conservador; subir é uma decisão comercial, e cabe a quem vende.
UPDATE usuario
   SET plano = 'basico'
 WHERE tipo = 'dono'
   AND plano IS NULL;

COMMENT ON COLUMN usuario.plano IS
    'Plano da assinatura da loja. O teto de acessos de cada plano está '
    'em app/core/planos.py. Nulo no cliente, que não assina.';
