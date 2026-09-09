# AquaSys

Sistema de gerenciamento de aquários para lojas de aquarismo e seus clientes.

A loja acompanha os próprios aquários, registra as manutenções que faz na casa
dos clientes e publica conteúdo em vídeo. O cliente acompanha os aquários dele,
consulta compatibilidade entre espécies antes de comprar um peixe e assiste aos
cursos que a loja disponibilizou.

**API** em FastAPI + PostgreSQL · **Aplicativo** em Flutter

---

## O que o sistema faz

O app tem quatro abas, e a quarta muda conforme quem entrou:

| | Conta empresarial (CNPJ) | Cliente (CPF) |
|---|---|---|
| **Início** | Painel com aquários, peixes, saúde geral, alertas e dicas | idem |
| **Aquários** | Cadastro e parâmetros de água, com alerta por tipo de aquário | idem |
| **Peixes** | Catálogo de espécies e análise de compatibilidade | idem |
| **4ª aba** | **Clientes** — acessos, manutenções e cursos | **Cursos** — só assiste |

A engrenagem do topo abre as **Configurações**, iguais para os dois acessos:
trocar a foto (ou a logo, no caso da loja), o nome exibido, o e-mail de
contato, a senha — e sair da conta. CPF/CNPJ não se edita ali: é a identidade
da assinatura, validada por você na criação da conta.

### Modelo de negócio

O AquaSys é vendido às lojas como serviço (SaaS). **Não existe
auto-cadastro**: a conta de cada assinante é criada no servidor, por quem
administra o produto, depois de conferir que se trata mesmo de uma empresa.

Das 42 rotas da API, apenas duas são públicas — o login e o health check.
Nenhuma delas cria conta.

A pessoa física nunca assina: ela entra como cliente de uma loja, e é a
loja que cria esse acesso pelo app.

### Os dois tipos de acesso

Ambos vivem na tabela `usuario`, separados por duas colunas:

- `tipo` — `'dono'` (empresa) ou `'cliente'` (pessoa física)
- `dono_id` — no cliente, aponta para a loja que o cadastrou; no dono, é nulo

O banco garante essa regra por conta própria:

```sql
CHECK ((tipo='dono' AND dono_id IS NULL) OR (tipo='cliente' AND dono_id IS NOT NULL))
```

O cliente não se cadastra sozinho: a loja cria o acesso dele em
**Clientes → Acessos para clientes**, definindo uma senha inicial. A partir daí
o cliente entra no mesmo login, com o próprio CPF.

O login **reconhece CPF ou CNPJ automaticamente** pela quantidade de dígitos
(11 ou 14) — não há botão de "sou empresa" ou "sou cliente".

---

## Rodando o projeto

### O que você precisa

- Python 3.12 ou mais novo (desenvolvido em 3.14)
- PostgreSQL 14 ou mais novo
- Flutter 3.35 ou mais novo (desenvolvido em 3.47)

### 1. Banco de dados

Crie um banco vazio no PostgreSQL:

```sql
CREATE DATABASE "AquaSys";
```

### 2. API

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha:

```bash
DATABASE_URL=postgresql://usuario:senha@localhost:5432/AquaSys
SECRET_KEY=<uma chave longa e aleatória>
```

Gere a chave com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Monte o esquema:

```bash
python criar_tabelas.py
```

Crie a conta da loja assinante — **sem ela não há como entrar no app**:

```bash
python criar_dono.py "Minha Loja de Aquarismo" 12.345.678/0001-90 minhasenha
```

Só aceita **CNPJ**, com dígitos verificadores conferidos. CPF é recusado:
pessoa física entra como cliente de uma loja, não como assinante.

Suba a API:

```bash
uvicorn app.main:app --reload
```

A documentação interativa fica em <http://127.0.0.1:8000/docs>.

### 3. Aplicativo

```bash
cd aquasys_app
flutter pub get
flutter run -d chrome
```

Entre com o CNPJ e a senha que você acabou de criar.

---

## Rodando no celular

O padrão da API é `127.0.0.1`, que **num aparelho aponta para o próprio
aparelho** — não para o seu computador. São dois ajustes:

**A API precisa aceitar conexão de fora:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**O app precisa saber o IP da sua máquina** (descubra com `ipconfig`):

```bash
flutter run --dart-define=AQUASYS_API=http://192.168.0.10:8000
```

Computador e celular precisam estar na mesma rede. O endereço é lido em
`lib/config.dart` e não está fixo em nenhum outro lugar do código.

---

## Conteúdo inicial (opcional)

O sistema funciona vazio, mas fica mais interessante com dados:

```bash
python seed_especies.py    # catálogo de espécies e regras de compatibilidade
python seed_dicas.py       # dicas da tela inicial, geradas do catálogo
python seed_cursos.py      # cursos globais, com vídeos do YouTube
```

Todos podem ser rodados mais de uma vez sem duplicar nada.

Para testar as duas telas sem cadastrar nada à mão:

```bash
python seed_demo.py
```

Cria uma loja e um cliente dela, cada um com aquários, peixes e alertas:

| | Documento | Senha |
|---|---|---|
| Loja (CNPJ) | `11.222.333/0001-81` | `aquasys123` |
| Cliente (CPF) | `123.456.789-09` | `cliente123` |

### Sobre os cursos

`seed_cursos.py` monta os cursos a partir de **playlists do YouTube**. Sem
configuração extra ele usa o feed RSS público, que entrega no máximo 15 vídeos
por playlist. Para trazer playlists inteiras, coloque uma chave da YouTube Data
API v3 no `.env`:

```bash
YOUTUBE_API_KEY=<sua chave>
```

A API do YouTube é gratuita (10.000 unidades por dia; cada playlist custa 1) e
não exige cartão. A chave é usada **apenas pelo seed, no servidor** — o
aplicativo nunca a recebe.

Playlists maiores que 15 vídeos, sem a chave, podem ser completadas à mão pelo
arquivo `cursos.txt`.

Os vídeos são reproduzidos pelo **player oficial do YouTube** (IFrame Player
API). O banco guarda apenas o identificador do vídeo — nada é baixado nem
redistribuído, que é o exigido pelos Termos de Serviço do YouTube.

---

## Estrutura

```
app/                    API FastAPI
├── core/               configuração, segurança, CPF/CNPJ, dependências
├── models/             tabelas (SQLAlchemy)
├── schemas/            contratos de entrada e saída (Pydantic)
├── routers/            endpoints por assunto
└── services/           regras de negócio sem HTTP
    ├── parametros.py       faixas ideais, conforme os peixes do aquário
    ├── dicas.py            dicas tiradas do estado real de cada aquário
    ├── imagens.py          preparo das fotos e busca no Wikimedia Commons
    ├── compatibilidade.py  motor de convivência entre espécies
    └── youtube.py          integração com o YouTube

aquasys_app/lib/        Aplicativo Flutter
├── config.dart         endereço da API
├── Services/           acesso à API (api.dart centraliza tudo)
├── Telas/              uma tela por assunto
├── Tema/               tokens de cor e widgets reaproveitados
├── widgets/            componentes compartilhados
└── utils/              CPF/CNPJ

sql/                    migrações, aplicadas em ordem
```

### Onde ficam as regras

Três decisões que explicam o resto do código:

**A faixa ideal de cada parâmetro vive só no servidor**
(`app/services/parametros.py`). Ela sai de duas camadas: o tipo do aquário é o
palpite inicial, mas quando há peixes cadastrados são eles que mandam — a faixa
vira a interseção do que as espécies aguentam. Um "comunitário" povoado com
peixes de água alcalina não leva alarme por pH 8, e um neon em água a pH 7,3
leva, com o motivo escrito por extenso. O app não recalcula nada: recebe da API
quais parâmetros estão fora, a faixa e a explicação. Foi assim que se evitou o
card do aquário e a tela inicial discordarem.

**Toda rota filtra pelo usuário logado** antes de responder
(`_buscar_aquario_do_usuario`, `_buscar_ficha_do_dono`, e semelhantes). Trocar
o id na URL não dá acesso a dado de terceiro.

**As fotos das espécies não vão dentro do aplicativo.** Empacotá-las engordaria
o APK sem limite — são muitas espécies — e cada peixe novo exigiria publicar
uma versão na loja. Elas ficam em `especie_imagem`, tabela separada de
`especie` para o catálogo não arrastar megabytes em cada listagem, e são
servidas por `GET /peixes/{id}/imagem` com `ETag` e cache de um mês. Duas
resoluções: 192 px quadrada para a lista (~8 KB) e 900 px para o card aberto
(~60 KB).

As imagens vêm do **Wikimedia Commons**, sob licença Creative Commons ou
domínio público — o que permite uso comercial. Autor e licença são gravados
junto e exibidos sob a foto, porque essas licenças exigem crédito visível.

---

## Scripts

| Comando | O que faz |
|---|---|
| `python criar_tabelas.py` | Cria as tabelas que faltam e aplica as migrações pendentes |
| `python criar_dono.py "<nome>" <cnpj> <senha>` | Cria a conta de uma loja assinante (só CNPJ) |
| `python seed_demo.py` | Cria as duas contas de demonstração, com conteúdo |
| `python seed_especies.py` | Popula o catálogo de espécies |
| `python seed_dicas.py` | Popula as dicas da tela inicial |
| `python seed_cursos.py` | Popula os cursos globais |
| `python seed_cursos.py --listar` | Mostra os cursos e aulas já importados |
| `python regerar_alertas.py` | Recalcula os alertas de todos os aquários |
| `python baixar_imagens.py` | Baixa do Wikimedia Commons a foto das espécies que ainda não têm |
| `python baixar_imagens.py --listar` | Mostra quais espécies têm foto, com autor e licença |
| `python baixar_imagens.py --especie "X" --arquivo foto.jpg` | Usa uma imagem local, quando o Commons não tem |

`criar_tabelas.py` controla o que já rodou na tabela `_migracao`, então cada
migração é aplicada uma única vez. Rodar de novo é sempre seguro.

`regerar_alertas.py` só é necessário depois de mexer nas faixas ideais em
`app/services/parametros.py` — no uso normal, cada medição já regrava os alertas
do próprio aquário.

---

## Testes

**API** — 216 testes:

```bash
python -m pytest
```

Rodam contra um banco PostgreSQL próprio (`<seu_banco>_test`), criado do zero e
derrubado no fim. O banco de desenvolvimento nunca é tocado, e cada teste roda
numa transação desfeita ao final, então um não enxerga o que o outro gravou.

| Arquivo | O que cobre |
|---|---|
| `test_documento.py` | CPF x CNPJ: reconhecimento, dígitos verificadores, máscara |
| `test_parametros.py` | Faixas ideais por tipo e pelos peixes do aquário |
| `test_youtube.py` | Extração de id de vídeo e de playlist |
| `test_auth.py` | Login com e sem máscara, senha errada, conta desativada |
| `test_isolamento.py` | Uma loja não alcança dado de outra |
| `test_cursos.py` | Visibilidade global/loja e progresso por pessoa |
| `test_fichas.py` | Cadastro reaproveitado e preenchimento automático |
| `test_alertas.py` | Ciclo do alerta, dicas da Home e cálculo da saúde geral |
| `test_perfil.py` | Nome, e-mail, troca de senha e foto de perfil |
| `test_imagens.py` | Preparo das fotos das espécies, licença aceita e cache da rota |

`test_isolamento.py` é o mais importante: o sistema é multiempresa, e se uma
loja conseguisse ler dado de outra trocando um id na URL, o produto não poderia
ser vendido.

**Aplicativo** — 23 testes:

```bash
cd aquasys_app
flutter test
flutter analyze
```

Cobrem CPF/CNPJ, o agendamento das notificações e a expiração do token que
decide o login automático.

---

## Duas coisas para saber

**A senha nunca é guardada em texto.** `senha_hash` recebe um hash bcrypt; a
senha original existe só no corpo da requisição.

**Excluir um cliente desativa, não apaga** (`ativo = false`). Apagar a linha
levaria junto, por cascata, os aquários, os peixes e o progresso de curso dele.

**Suspender uma loja é a mesma coisa.** O login filtra por `ativo`, então
`UPDATE usuario SET ativo = false WHERE cpf_cnpj = '...'` corta o acesso de um
assinante sem apagar nada — e reverter é só voltar para `true`.

---

## Configuração

Tudo vem do `.env` (veja `.env.example`):

| Variável | Para quê |
|---|---|
| `DATABASE_URL` | Conexão com o PostgreSQL |
| `SECRET_KEY` | Assinatura dos tokens JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade da sessão (padrão 60) |
| `YOUTUBE_API_KEY` | Opcional, só para o seed de cursos |
| `SQL_ECHO` | `True` imprime todo SQL no console (padrão `False`) |

O `.env` está fora do controle de versão e **não deve ser commitado**.
