-- ═══════════════════════════════════════════════════════════
-- 010 — Nome científico único só entre as espécies-base
--
-- O banco já tinha, sem que nenhum arquivo do repositório o
-- declarasse, um índice único em lower(nome_cientifico): uma
-- linha por espécie. A regra era correta e evitava cadastrar o
-- mesmo peixe duas vezes com nomes populares diferentes.
--
-- Com as variedades (009), ela passou a barrar o que é certo. O
-- Acará Bandeira Marmorato É Pterophyllum scalare — compartilha o
-- nome científico com a base, porque é o mesmo animal. O primeiro
-- cadastro de variedades foi recusado inteiro por este índice.
--
-- A regra que continua valendo é a original, aplicada a quem ela
-- se destinava: não pode haver duas ESPÉCIES-BASE com o mesmo nome
-- científico. As variedades ficam fora do índice.
-- ═══════════════════════════════════════════════════════════

DROP INDEX IF EXISTS idx_especie_cientifico;

CREATE UNIQUE INDEX IF NOT EXISTS idx_especie_cientifico
    ON especie (lower(nome_cientifico))
    WHERE variante_de_id IS NULL;

COMMENT ON INDEX idx_especie_cientifico IS
    'Uma espécie-base por nome científico. Variedades ficam de fora: '
    'compartilham o nome científico da base, por serem o mesmo animal.';
