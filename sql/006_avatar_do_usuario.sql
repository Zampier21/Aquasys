BEGIN;

ALTER TABLE usuario ADD COLUMN IF NOT EXISTS avatar TEXT;

COMMENT ON COLUMN usuario.avatar IS
    'Foto de perfil ou logo, em base64 puro (sem prefixo data:). Nulo = ícone padrão.';

COMMIT;
