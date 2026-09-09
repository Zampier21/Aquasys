-- =====================================================================
-- AquaSys — esquema do banco de dados
--
-- Estado atual e completo das 18 tabelas, já com todas as migrações de
-- sql/ incorporadas. Gerado a partir dos modelos em app/models/ e
-- compilado para o dialeto do PostgreSQL.
--
-- COMO USAR
--   Este arquivo é documentação: serve para ler o esquema, revisá-lo e
--   anexá-lo ao trabalho. Quem cria o banco de verdade é
--
--       python criar_tabelas.py
--
--   que monta as tabelas pelos modelos e registra as migrações na
--   tabela de controle `_migracao`. Rodar este arquivo à mão num banco
--   que já existe vai falhar, porque as tabelas já estarão lá.
--
--   Ele fica fora de sql/ justamente por isso: criar_tabelas.py executa
--   todo sql/*.sql ainda não registrado, e um CREATE TABLE ali dentro
--   quebraria a preparação de um banco existente.
--
-- ORDEM
--   As tabelas aparecem em ordem de dependência: nenhuma chave
--   estrangeira aponta para tabela que ainda não exista.
-- =====================================================================

BEGIN;


-- ---------------------------------------------------------------------
-- especie
-- ---------------------------------------------------------------------
CREATE TABLE especie (
	id UUID NOT NULL, 
	nome_comum VARCHAR(100) NOT NULL, 
	nome_cientifico VARCHAR(150), 
	nomes_alternativos TEXT, 
	familia VARCHAR(80), 
	tipo_agua VARCHAR(10), 
	origem VARCHAR(120), 
	temp_min FLOAT, 
	temp_max FLOAT, 
	ph_min FLOAT, 
	ph_max FLOAT, 
	dgh_min FLOAT, 
	dgh_max FLOAT, 
	tamanho_adulto_cm FLOAT, 
	volume_minimo_l INTEGER, 
	comportamento VARCHAR(20), 
	agressivo_coespecificos BOOLEAN, 
	agrupamento VARCHAR(15), 
	cardume_minimo INTEGER, 
	nivel_natacao VARCHAR(15), 
	morde_barbatana BOOLEAN, 
	barbatana_longa BOOLEAN, 
	come_plantas BOOLEAN, 
	come_invertebrados BOOLEAN, 
	reef_safe VARCHAR(15), 
	alimentacao VARCHAR(100), 
	nivel_dificuldade VARCHAR(15), 
	expectativa_vida_anos INTEGER, 
	imagem_url VARCHAR(255), 
	observacoes TEXT, 
	ativo BOOLEAN NOT NULL, 
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

-- ---------------------------------------------------------------------
-- usuario
--   depende de: usuario
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
	id UUID NOT NULL, 
	nome VARCHAR(150) NOT NULL, 
	cpf_cnpj VARCHAR(18) NOT NULL, 
	senha_hash VARCHAR(255) NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	dono_id UUID, 
	email VARCHAR(150), 
	avatar TEXT, 
	ativo BOOLEAN NOT NULL, 
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT chk_tipo CHECK (tipo IN ('dono', 'cliente')), 
	UNIQUE (cpf_cnpj), 
	FOREIGN KEY(dono_id) REFERENCES usuario (id)
);

-- ---------------------------------------------------------------------
-- aquario
--   depende de: usuario
-- ---------------------------------------------------------------------
CREATE TABLE aquario (
	id UUID NOT NULL, 
	usuario_id UUID NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	volume_litros FLOAT NOT NULL, 
	temperatura FLOAT NOT NULL, 
	ph FLOAT NOT NULL, 
	tipo VARCHAR(20), 
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT chk_volume CHECK (volume_litros > 0), 
	CONSTRAINT chk_ph CHECK (ph BETWEEN 0 AND 14), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- cliente_manutencao
--   depende de: usuario
-- ---------------------------------------------------------------------
CREATE TABLE cliente_manutencao (
	id UUID NOT NULL, 
	dono_id UUID NOT NULL, 
	nome VARCHAR(150) NOT NULL, 
	telefone VARCHAR(30), 
	endereco VARCHAR(250), 
	tipo_instalacao VARCHAR(20), 
	volume_litros INTEGER, 
	agua_doce BOOLEAN, 
	observacoes TEXT, 
	ativo BOOLEAN NOT NULL, 
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dono_id) REFERENCES usuario (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- compatib_especie
--   depende de: especie
-- ---------------------------------------------------------------------
CREATE TABLE compatib_especie (
	id UUID NOT NULL, 
	especie_a_id UUID NOT NULL, 
	especie_b_id UUID NOT NULL, 
	nivel VARCHAR(10) NOT NULL, 
	motivo VARCHAR(30), 
	observacao TEXT, 
	fonte VARCHAR(120), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_par_especies UNIQUE (especie_a_id, especie_b_id), 
	FOREIGN KEY(especie_a_id) REFERENCES especie (id) ON DELETE CASCADE, 
	FOREIGN KEY(especie_b_id) REFERENCES especie (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- curso
--   depende de: usuario
-- ---------------------------------------------------------------------
CREATE TABLE curso (
	id UUID NOT NULL, 
	dono_id UUID, 
	titulo VARCHAR(150) NOT NULL, 
	descricao TEXT, 
	miniatura_url VARCHAR(255), 
	categoria VARCHAR(50), 
	publicado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	ativo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dono_id) REFERENCES usuario (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- dica
--   depende de: especie
-- ---------------------------------------------------------------------
CREATE TABLE dica (
	id UUID NOT NULL, 
	conteudo TEXT NOT NULL, 
	categoria VARCHAR(30), 
	especie_id UUID, 
	ativa BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(especie_id) REFERENCES especie (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- especie_imagem
--   depende de: especie
-- ---------------------------------------------------------------------
CREATE TABLE especie_imagem (
	especie_id UUID NOT NULL, 
	miniatura BYTEA NOT NULL, 
	completa BYTEA NOT NULL, 
	mime VARCHAR(30) NOT NULL, 
	hash VARCHAR(64) NOT NULL, 
	largura INTEGER, 
	altura INTEGER, 
	bytes_miniatura INTEGER, 
	bytes_completa INTEGER, 
	fonte TEXT, 
	autor VARCHAR(300), 
	licenca VARCHAR(80), 
	licenca_url TEXT, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (especie_id), 
	FOREIGN KEY(especie_id) REFERENCES especie (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- alerta
--   depende de: aquario, usuario
-- ---------------------------------------------------------------------
CREATE TABLE alerta (
	id UUID NOT NULL, 
	aquario_id UUID NOT NULL, 
	usuario_id UUID NOT NULL, 
	mensagem TEXT NOT NULL, 
	tipo VARCHAR(25), 
	lido BOOLEAN NOT NULL, 
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(aquario_id) REFERENCES aquario (id) ON DELETE CASCADE, 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- aquario_especie
--   depende de: aquario, especie
-- ---------------------------------------------------------------------
CREATE TABLE aquario_especie (
	id UUID NOT NULL, 
	aquario_id UUID NOT NULL, 
	especie_id UUID NOT NULL, 
	quantidade INTEGER NOT NULL, 
	adicionado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_aquario_especie UNIQUE (aquario_id, especie_id), 
	FOREIGN KEY(aquario_id) REFERENCES aquario (id) ON DELETE CASCADE, 
	FOREIGN KEY(especie_id) REFERENCES especie (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- aula
--   depende de: curso
-- ---------------------------------------------------------------------
CREATE TABLE aula (
	id UUID NOT NULL, 
	curso_id UUID NOT NULL, 
	titulo VARCHAR(200) NOT NULL, 
	youtube_id VARCHAR(20) NOT NULL, 
	canal VARCHAR(120), 
	miniatura_url VARCHAR(255), 
	ordem INTEGER NOT NULL, 
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_aula_curso_video UNIQUE (curso_id, youtube_id), 
	FOREIGN KEY(curso_id) REFERENCES curso (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- ficha_manutencao
--   depende de: cliente_manutencao, usuario
-- ---------------------------------------------------------------------
CREATE TABLE ficha_manutencao (
	id UUID NOT NULL, 
	dono_id UUID NOT NULL, 
	cliente_id UUID, 
	nome_cliente VARCHAR(150) NOT NULL, 
	nome_empresa VARCHAR(150), 
	data_atendimento DATE, 
	horario_chegada VARCHAR(10), 
	horario_saida VARCHAR(10), 
	tipo_instalacao VARCHAR(20), 
	volume_litros INTEGER, 
	agua_doce BOOLEAN, 
	observacoes TEXT, 
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dono_id) REFERENCES usuario (id), 
	FOREIGN KEY(cliente_id) REFERENCES cliente_manutencao (id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- parametros_agua
--   depende de: aquario
-- ---------------------------------------------------------------------
CREATE TABLE parametros_agua (
	id UUID NOT NULL, 
	aquario_id UUID NOT NULL, 
	amonia_ppm FLOAT NOT NULL, 
	nitrito_ppm FLOAT NOT NULL, 
	nitrato_ppm FLOAT NOT NULL, 
	registrado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(aquario_id) REFERENCES aquario (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- progresso_curso
--   depende de: curso, usuario
-- ---------------------------------------------------------------------
CREATE TABLE progresso_curso (
	id UUID NOT NULL, 
	usuario_id UUID NOT NULL, 
	curso_id UUID NOT NULL, 
	percentual INTEGER NOT NULL, 
	iniciado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE CASCADE, 
	FOREIGN KEY(curso_id) REFERENCES curso (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- checklist_equipamento
--   depende de: ficha_manutencao
-- ---------------------------------------------------------------------
CREATE TABLE checklist_equipamento (
	id UUID NOT NULL, 
	ficha_id UUID NOT NULL, 
	equipamento VARCHAR(100) NOT NULL, 
	presente BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ficha_id) REFERENCES ficha_manutencao (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- descricao_manutencao
--   depende de: ficha_manutencao
-- ---------------------------------------------------------------------
CREATE TABLE descricao_manutencao (
	id UUID NOT NULL, 
	ficha_id UUID NOT NULL, 
	chao_malhado BOOLEAN, 
	conferido_2x BOOLEAN, 
	stability_aplicado BOOLEAN, 
	itens_deixados TEXT, 
	descricao_livre TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ficha_id) REFERENCES ficha_manutencao (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- progresso_aula
--   depende de: aula, usuario
-- ---------------------------------------------------------------------
CREATE TABLE progresso_aula (
	id UUID NOT NULL, 
	usuario_id UUID NOT NULL, 
	aula_id UUID NOT NULL, 
	concluida BOOLEAN NOT NULL, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_progresso_aula UNIQUE (usuario_id, aula_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE CASCADE, 
	FOREIGN KEY(aula_id) REFERENCES aula (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- teste_agua
--   depende de: ficha_manutencao
-- ---------------------------------------------------------------------
CREATE TABLE teste_agua (
	id UUID NOT NULL, 
	ficha_id UUID NOT NULL, 
	parametro VARCHAR(60) NOT NULL, 
	valor FLOAT, 
	unidade VARCHAR(10), 
	PRIMARY KEY (id), 
	FOREIGN KEY(ficha_id) REFERENCES ficha_manutencao (id) ON DELETE CASCADE
);

COMMIT;
