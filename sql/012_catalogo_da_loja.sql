-- ═══════════════════════════════════════════════════════════
-- 012 — Catálogo próprio da loja e lista de peixes que ela tem
--
-- Até aqui o catálogo era único e curado: as espécies vinham do
-- seed, sem dono. A importação da lista de estoque muda isso em
-- duas frentes.
--
-- 1. A loja passa a poder criar espécie. O que ela cria nasce
--    como rascunho dela: `especie.dono_id` aponta para a conta
--    empresarial, e só ela e os clientes dela enxergam. Nulo
--    continua significando o catálogo curado, visível a todos.
--    Assim o erro de digitação de uma loja não vira espécie para
--    as outras, e o provedor promove ao catálogo global o que
--    conferir, apagando o dono_id.
--
-- 2. `especie.revisada` diz se a ficha foi conferida por gente.
--    O preenchimento automático a partir do nome erra: numa
--    amostra de quatro nomes reais, "Tetra Neon Negro" resolveu
--    para Paracheirodon innesi, que é outro peixe, e "Camarão
--    Red Cherry" resolveu para uma rede de restaurantes. Por
--    isso o que vem da importação entra como não revisado, e o
--    motor de compatibilidade nunca responde "liberado" para
--    espécie nessa condição: pede confirmação e diz por quê.
--
-- A tabela nova, `loja_especie`, é outra coisa: registra o que
-- cada loja TEM à venda, apontando inclusive para espécies do
-- catálogo curado. Uma loja vender Neon Tetra não faz dela dona
-- da espécie, e por isso o estoque não cabe numa coluna de
-- `especie`.
-- ═══════════════════════════════════════════════════════════

ALTER TABLE especie
    ADD COLUMN IF NOT EXISTS dono_id UUID REFERENCES usuario(id) ON DELETE CASCADE;

ALTER TABLE especie
    ADD COLUMN IF NOT EXISTS revisada BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN especie.dono_id IS
    'Loja que criou a espécie pela importação. Nulo = catálogo curado do '
    'AquaSys, visível a todas as lojas.';

COMMENT ON COLUMN especie.revisada IS
    'Falso enquanto porte, comportamento e faixas não forem conferidos por '
    'uma pessoa. O motor de compatibilidade exige confirmação nesse caso.';

-- O que a loja vende. Uma linha por espécie que ela oferece, seja do
-- catálogo curado, seja criada por ela.
CREATE TABLE IF NOT EXISTS loja_especie (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dono_id     UUID NOT NULL REFERENCES usuario(id)  ON DELETE CASCADE,
    especie_id  UUID NOT NULL REFERENCES especie(id)  ON DELETE CASCADE,
    -- O nome como veio na planilha da loja. Guardado porque é por ele
    -- que o lojista reconhece o item, e não pelo nome do catálogo.
    nome_na_lista VARCHAR(150),
    criado_em   TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_loja_especie UNIQUE (dono_id, especie_id)
);

-- A listagem do estoque filtra sempre pela loja; o índice da chave
-- única já serve, e este cobre a busca inversa, de quais lojas têm
-- determinada espécie.
CREATE INDEX IF NOT EXISTS idx_loja_especie_especie
    ON loja_especie (especie_id);

-- O catálogo é lido inteiro a cada abertura da aba de peixes, sempre
-- filtrando por dono (o curado mais o da própria loja).
CREATE INDEX IF NOT EXISTS idx_especie_dono
    ON especie (dono_id)
    WHERE dono_id IS NOT NULL;

COMMENT ON TABLE loja_especie IS
    'Peixes que cada loja tem à venda, importados da planilha de estoque. '
    'Visível para a loja e para os clientes dela.';

-- ─── Unicidade do nome científico, agora por dono ──────────
-- O índice da migração 010 exigia um nome científico único na tabela
-- inteira. Com catálogo por loja isso quebra no caso mais banal: duas
-- lojas importam "Kinguio", as duas resolvem para Carassius auratus, e
-- a segunda importação falha inteira por causa da primeira.
--
-- A regra que continua fazendo sentido é uma espécie-base por nome
-- científico DENTRO de cada catálogo: um no curado, um em cada loja.
-- NULLS NOT DISTINCT faz o catálogo curado, cujo dono_id é nulo, voltar
-- a ter a garantia original em vez de virar terra de ninguém.
--
-- O recorte exclui nome científico nulo: a espécie criada sem sugestão
-- segura fica sem ele, e são muitas por importação.
DROP INDEX IF EXISTS idx_especie_cientifico;

CREATE UNIQUE INDEX IF NOT EXISTS idx_especie_cientifico
    ON especie (dono_id, lower(nome_cientifico))
    NULLS NOT DISTINCT
    WHERE variante_de_id IS NULL AND nome_cientifico IS NOT NULL;

COMMENT ON INDEX idx_especie_cientifico IS
    'Uma espécie-base por nome científico em cada catálogo: o curado '
    '(dono nulo) e o de cada loja. Variedades e fichas sem nome '
    'científico ficam de fora.';
