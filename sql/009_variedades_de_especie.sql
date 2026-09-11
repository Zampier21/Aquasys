-- ═══════════════════════════════════════════════════════════
-- 009 — Variedades de uma mesma espécie
--
-- O catálogo precisa mostrar Tetra Neon Negro e Tetra Neon
-- Negro Albino, Acará Bandeira Marmorato e Acará Bandeira
-- Leopardo Azul. São variedades de aquariofilia: mesma espécie,
-- mesma água, mesmo porte, mesmo temperamento. O que muda é a
-- aparência — e é justamente ela que a loja quer mostrar ao
-- cliente na hora da venda.
--
-- Cadastrar cada variedade como espécie independente traria dois
-- problemas. O primeiro é repetir trinta campos de biologia
-- idênticos, que passariam a poder divergir entre si. O segundo,
-- pior, é a lista do catálogo encher de oito acarás-bandeira que,
-- para o motor de compatibilidade, são o mesmo animal.
--
-- A variedade passa a apontar para a espécie-base e a preencher
-- apenas o que difere. O resto fica nulo e é herdado na leitura.
-- ═══════════════════════════════════════════════════════════

ALTER TABLE especie
    ADD COLUMN IF NOT EXISTS variante_de_id UUID;

-- Apagar a base leva junto as variedades: uma variedade órfã não
-- teria de onde herdar pH, temperatura nem porte, e viraria uma
-- ficha pela metade.
ALTER TABLE especie
    DROP CONSTRAINT IF EXISTS especie_variante_de_id_fkey;

ALTER TABLE especie
    ADD CONSTRAINT especie_variante_de_id_fkey
    FOREIGN KEY (variante_de_id) REFERENCES especie (id) ON DELETE CASCADE;

-- Um nível só de herança. Variedade de variedade tornaria a
-- resolução recursiva e o dado, difícil de conferir: quem herda
-- precisa apontar para uma espécie que não herde de ninguém.
-- A restrição não consegue enxergar outra linha, então o que se
-- garante aqui é o caso trivial; o resto é verificado na aplicação.
ALTER TABLE especie
    DROP CONSTRAINT IF EXISTS chk_variante_nao_e_ela_mesma;

ALTER TABLE especie
    ADD CONSTRAINT chk_variante_nao_e_ela_mesma
    CHECK (variante_de_id IS NULL OR variante_de_id <> id);

-- A listagem do catálogo passa a filtrar por esta coluna a cada
-- abertura da aba Peixes; o índice evita varrer a tabela inteira.
CREATE INDEX IF NOT EXISTS idx_especie_variante_de
    ON especie (variante_de_id);

COMMENT ON COLUMN especie.variante_de_id IS
    'Espécie-base desta variedade. Nulo quando a própria linha é a '
    'base. A variedade preenche só o que difere; o restante é '
    'herdado na leitura por app/services/variedades.py.';
