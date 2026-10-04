-- ═══════════════════════════════════════════════════════════
-- 013 — Preenchimento da ficha a partir da FishBase
--
-- A importação da lista da loja criava a espécie só com o nome
-- comum e, quando dava para provar, o nome científico. Porte e
-- faixas de água ficavam vazios, e não havia de onde vir.
--
-- Com o nome científico em mão, a FishBase preenche o que é
-- medida objetiva: tamanho adulto, tipo de água, faixa de pH e
-- faixa de dureza. São dados de base científica, citáveis, e
-- entram direto nas colunas que já existem.
--
-- Esta migração acrescenta as duas colunas que faltavam para
-- isso ser feito de forma honesta.
--
-- ─── Por que `clima` e não temperatura ─────────────────────
-- A FishBase tem `stocks.TempMin` e `stocks.TempMax`, e seria
-- o caminho óbvio para `temp_min` e `temp_max`. Não é, e o
-- motivo é um peixe da própria lista da Aqualife.
--
-- Para Carassius auratus, o kinguio, a FishBase registra
-- 0 a 41 graus. O número está certo: é a faixa em que a espécie
-- sobrevive na natureza, somando as populações introduzidas no
-- mundo inteiro, do degelo ao clima equatorial. Só que não é
-- recomendação de aquário. Gravado em `temp_min` e `temp_max`,
-- o motor de compatibilidade concluiria que o kinguio serve em
-- qualquer aquário, inclusive num de disco a 29 graus. Kinguio
-- é peixe de água fria. O conselho sairia errado, e sobre
-- animal vivo.
--
-- O que a FishBase tem e é defensável é a classificação de
-- clima (`stocks.EnvTemp`): o kinguio é subtropical, o neon é
-- tropical. É categoria, não faixa, e serve para avisar quem
-- preenche a ficha e para alertar quando o clima da espécie não
-- combina com o aquário. A faixa em graus continua sendo
-- preenchida por gente.
-- ═══════════════════════════════════════════════════════════

ALTER TABLE especie
    ADD COLUMN IF NOT EXISTS clima VARCHAR(15);

ALTER TABLE especie
    ADD COLUMN IF NOT EXISTS fonte_dados VARCHAR(120);

-- Mesmas categorias da FishBase, traduzidas, no padrão dos
-- outros enumerados da tabela.
ALTER TABLE especie
    DROP CONSTRAINT IF EXISTS chk_clima;

ALTER TABLE especie
    ADD CONSTRAINT chk_clima CHECK (
        clima IS NULL OR clima IN (
            'tropical', 'subtropical', 'temperado',
            'boreal', 'polar', 'altitude', 'agua_profunda'
        )
    );

COMMENT ON COLUMN especie.clima IS
    'Classificação climática da espécie, vinda de stocks.EnvTemp da '
    'FishBase. Não substitui temp_min e temp_max: é categoria, e serve '
    'para alertar quando o clima da espécie não combina com o aquário.';

-- A licença da FishBase é CC BY-NC 4.0, que exige atribuição onde o
-- dado aparecer. Guardar a fonte na própria linha é o que permite ao
-- aplicativo mostrar o crédito na ficha, e também distinguir o que
-- veio de fora do que uma pessoa digitou.
COMMENT ON COLUMN especie.fonte_dados IS
    'De onde vieram as medidas da ficha, para crédito e rastreio. '
    'Exemplo: "FishBase v24.07 (CC BY-NC 4.0)". Nulo quando foi '
    'preenchida à mão.';

-- A tela de revisão lista o que a importação deixou incompleto,
-- sempre dentro de uma loja.
CREATE INDEX IF NOT EXISTS idx_especie_nao_revisada
    ON especie (dono_id)
    WHERE revisada = FALSE;
