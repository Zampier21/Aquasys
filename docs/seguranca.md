# Segurança do AquaSys

Este arquivo responde, item por item, à lista de verificação usada
antes de colocar o produto no ar. Cada item diz o que foi feito, onde
está no código e o que ainda depende de decisão ou de acesso que o
código não tem.

A régua adotada é a de um sistema que guarda CPF, CNPJ, telefone e
endereço de clientes de terceiros: a loja confia os dados dos clientes
dela ao AquaSys, e o dano de um vazamento não cai sobre nós, cai sobre
ela.

---

## Quadro geral

| # | Item | Situação |
|---|------|----------|
| 1 | Esconder chaves de API | Feito (já estava) |
| 2 | Limpar segredos do git | **Pendente — depende de decisão** |
| 3 | Chave pública de banco | Não se aplica |
| 4 | Ativar RLS | Parcial — isolamento em código, com testes |
| 5 | Criptografia de dados | Parcial — TLS exigido na configuração |
| 6 | Autenticação no servidor | Feito (já estava), agora com teste que varre as rotas |
| 7 | Restringir acessos | Feito |
| 8 | Bloquear atribuição em massa | Feito |
| 9 | Proteger cookies | Não se aplica |
| 10 | Hash nas senhas | Feito (já estava), reforçado |
| 11 | Limite de requisições | Feito |
| 12 | Proteção contra robôs | Não se aplica |
| 13 | Consultas parametrizadas | Feito (já estava) |
| 14 | Validação de entrada | Feito |
| 15 | Não vazar conteúdo de usuário | Feito |
| 16 | Restringir uploads | Feito |
| 17 | Enxugar resposta da API | Feito |
| 18 | Cabeçalhos de segurança | Feito |
| 19 | Forçar HTTPS | Feito (ligar no servidor) |
| 20 | Auditoria de dependências | Feito — uma falha encontrada e removida |

Tudo o que está marcado como feito tem teste em
`tests/test_seguranca.py`.

---

## 1. Esconder chaves de API

A única chave de terceiro do sistema é a do YouTube, e ela nunca sai do
servidor: só `seed_cursos.py` a usa, num script que roda na máquina de
quem administra. O aplicativo Flutter não tem chave nenhuma embutida.

Vale lembrar que embutir chave em aplicativo não adianta de qualquer
jeito: o pacote instalado pode ser aberto e lido.

**Falta fazer, no Console do Google Cloud:** restringir a chave à
YouTube Data API v3 e ao endereço do servidor. Chave sem restrição, se
vazar, vira cobrança na conta.

## 2. Limpar segredos do git

O `.gitignore` já barra o `.env` desde sempre, mas o arquivo foi
versionado antes disso e continua no histórico, em dois commits. O
repositório é público.

Isto é o item mais urgente da lista, e está descrito no fim deste
arquivo, em **Limpeza do histórico**, porque exige decisão e não só
código.

## 3. Chave pública de banco

Vem de plataformas onde o aplicativo fala direto com o banco usando uma
chave publicável, e a segurança inteira depende das regras que aquela
chave respeita. O AquaSys não funciona assim: o aplicativo só conhece a
API, e quem fala com o PostgreSQL é o servidor. Não existe chave de
banco no lado do cliente para ser protegida.

## 4. Ativar RLS

Row Level Security é o PostgreSQL recusando linha de outro dono mesmo
quando a consulta pede. Hoje quem recusa é o código Python: toda
consulta filtra por `dono_id`, e `tests/test_isolamento.py` prova o
comportamento por fora, rota por rota.

Não é a mesma coisa. Com RLS, um `WHERE` esquecido numa rota futura
continua não vazando. Sem RLS, vaza.

Ligar RLS de verdade exige que cada transação diga ao banco quem é o
usuário (`SET LOCAL app.usuario_id`), e isso esbarra num detalhe do
desenho atual: `get_usuario_atual` depende de `get_db`, então a sessão
nasce antes de se saber de quem ela é. Dá para resolver, e não é uma
linha: é refazer o ciclo de vida da sessão e escrever política para
cada tabela. Fica como próximo passo, com o isolamento em código e os
testes segurando enquanto isso.

O que dá para fazer antes disso, e vale muito, é o papel de aplicação
com privilégio mínimo descrito em **Papel do banco**, mais abaixo.

## 5. Criptografia de dados

Separando os dois casos:

**Em trânsito.** É o que importa aqui e está resolvido na configuração:
`FORCAR_HTTPS` para o tráfego do aplicativo, e a conferência de
produção recusa subir com `DATABASE_URL` sem `sslmode=require` quando o
banco não está na mesma máquina.

**Em repouso.** Criptografia de coluna foi considerada e descartada,
com motivo: o dado sensível guardado é CPF e CNPJ, e o login procura a
conta justamente por ele, comparando sem máscara. Cifrar a coluna
impediria essa busca. O caminho correto para dado em repouso, aqui, é
disco cifrado no servidor do banco, que é configuração de
infraestrutura e não de aplicação.

A senha nunca é guardada, nem cifrada: é hash. Ver o item 10.

## 6. Autenticação no servidor

Já era assim: toda rota depende de `get_usuario_atual`, que valida a
assinatura do token e busca o usuário no banco a cada requisição. O
aplicativo também lê o vencimento do token, mas isso é conveniência de
tela, e não decisão de acesso.

O que se acrescentou foi a prova. `test_toda_rota_exige_token_menos_login_e_status`
percorre todas as rotas registradas e reprova a que não tiver a
dependência. Uma rota nova que esqueça a proteção passa a quebrar a
suíte em vez de ficar aberta em silêncio.

Também mudou a biblioteca de JWT, e o algoritmo aceito na validação
agora é passado explicitamente. Sem essa lista, um token forjado com
`alg: none` seria aceito — é a falha clássica de implementação de JWT,
e `test_token_sem_assinatura_e_recusado` a cobre.

## 7. Restringir acessos

Havia um problema real aqui:

```python
allow_origins=["*"]
allow_credentials=True
```

Essa combinação permite que qualquer site da internet chame a API em
nome de quem estiver logado. Agora:

- a lista de origens vem do `.env` e é vazia por padrão, que é o certo
  para uma API consumida por aplicativo nativo;
- em desenvolvimento, `localhost` é liberado em qualquer porta, porque
  o `flutter run -d chrome` sorteia a porta a cada execução;
- `allow_credentials` foi desligado, já que não há cookie: o token vai
  no cabeçalho `Authorization`, que o CORS libera sem esse modo;
- métodos e cabeçalhos deixaram de ser `*`;
- `'*'` na lista, em produção, impede o servidor de subir.

A `/docs` e a `/redoc` passaram a ser desligáveis, e vêm desligadas por
padrão: elas descrevem todas as rotas e todos os campos aceitos.

Por perfil, continua valendo o que já havia: `exigir_dono` nas rotas de
administração, e o cliente só enxerga o que é da loja dele.

## 8. Bloquear atribuição em massa

Todos os contratos de entrada passaram a herdar de `Entrada`
(`app/schemas/base.py`), que recusa campo não declarado.

O padrão do Pydantic é descartar o campo desconhecido em silêncio. Isso
não é explorável hoje, mas é o começo do problema: no dia em que
alguém declarar um campo com aquele nome, uma requisição antiga passa a
escrevê-lo. Duas rotas montam o objeto direto do corpo
(`Especie(**dados.model_dump())`, `setattr` em laço), e são exatamente
essas que a falha atinge.

**Uma brecha real foi encontrada e fechada no caminho.** A rota
`POST /peixes/` gravava a espécie com `dono_id` nulo, ou seja, dentro
do catálogo curado que todas as lojas enxergam. Isso estava certo antes
da migração 012, quando catálogo só havia um; depois dela, virou uma
loja escrevendo no catálogo das concorrentes. A espécie cadastrada
agora nasce com dono, como já acontecia na importação.

## 9. Proteger cookies

O AquaSys não usa cookie. O token fica no `SharedPreferences` do
aparelho e viaja no cabeçalho `Authorization`. Sem cookie não há
`HttpOnly`, `Secure` nem `SameSite` para configurar, e de quebra não há
CSRF: um site de terceiro não consegue fazer o navegador anexar um
cabeçalho que ele não controla.

Uma ressalva honesta sobre a versão web: no Flutter web, o
`SharedPreferences` é o `localStorage`, que qualquer script rodando na
página consegue ler. É por isso que a política de conteúdo da API
proíbe script, e é mais uma razão para a lista de origens do CORS ser
curta.

## 10. Hash nas senhas

Já era bcrypt via passlib, que é a escolha certa. O que mudou:

- o custo ficou explícito em 12 rodadas, para não depender do padrão da
  biblioteca;
- hash malformado responde "não bate" em vez de estourar um 500 — um
  erro diferente diria ao atacante que ele achou algo diferente;
- senha acima de 72 bytes é recusada no cadastro, em vez de ser
  truncada em silêncio pelo bcrypt.

Testes cobrem que o hash não contém a senha, que duas contas com a
mesma senha têm hashes diferentes (é o sal) e que hash estragado não
derruba a rota.

## 11. Limite de requisições

Não havia nenhum. A rota de login aceitava tentativas sem fim, e o
cadastro permite senha de seis caracteres — combinação que cai em
minutos.

`app/core/limitador.py` implementa janela deslizante em dois níveis:

- **geral**, 120 requisições por minuto por endereço;
- **login**, 8 tentativas a cada 5 minutos, contadas por endereço *e*
  por documento.

São dois ataques diferentes: um endereço tentando muitas contas, e
muitos endereços tentando a mesma. Contar só o endereço deixaria o
segundo passar. Entrar com a senha certa zera a contagem, para que a
loja que erra de manhã e acerta não fique de castigo.

Duas limitações ditas em voz alta:

- a contagem mora na memória do processo. Com vários trabalhadores do
  uvicorn, cada um conta o seu, e o teto real é o teto vezes o número de
  processos. Em mais de uma máquina, isto tem de virar contagem no
  Redis, e só este arquivo muda;
- `X-Forwarded-For` só é obedecido com `CONFIAR_NO_PROXY` ligado.
  Obedecer sem proxy na frente anularia o limitador, porque o atacante
  escolheria o próprio endereço a cada tentativa.

## 12. Proteção contra robôs

Captcha existe para impedir criação automática de conta. No AquaSys
ninguém se cadastra sozinho: a loja é cadastrada pela AquaSys, e o
cliente é cadastrado pela loja, com teto por plano. Não há formulário
público para robô nenhum preencher.

O risco real que sobraria — automatizar tentativas de senha — é o que o
item 11 resolve.

## 13. Consultas parametrizadas

Auditado: nenhuma consulta é montada por concatenação de texto. Tudo
passa pelo ORM do SQLAlchemy, que sempre parametriza. O único `text()`
do código de aplicação é uma condição fixa de índice em
`app/models/especie.py`, sem valor de usuário dentro.

Há interpolação de nome de banco em `tests/conftest.py`, que roda só na
suíte e usa nome derivado da configuração, não de entrada externa.

## 14. Validação de entrada

Pydantic em toda rota, com tamanho máximo, faixa de valor e validador
próprio de CPF e CNPJ (com dígito verificador, não só contagem de
dígitos). A importação de CSV tem teto de 512 KB e de 500 nomes, e
recusa binário renomeado.

O que se acrescentou: recusa de campo não declarado (item 8), teto de
tamanho do corpo antes da leitura (item 16) e limite nos campos do
login, que aceitavam texto de qualquer tamanho.

## 15. Não vazar conteúdo de usuário

Três frentes:

**Entre lojas.** Toda consulta filtra por dono, e `test_isolamento.py`
cobre rota por rota. O catálogo por loja tem cobertura própria em
`test_catalogo_da_loja.py`.

**Na mensagem de erro.** O login responde a mesma frase para conta
inexistente e para senha errada. Frases diferentes transformariam a
rota numa consulta: quem tentasse documentos em sequência montaria a
lista de clientes da loja. E a senha passou a ser conferida mesmo
quando a conta não existe, contra um hash descartável, para que as duas
respostas levem o mesmo tempo — sem isso, o relógio conta o que a
mensagem cala.

**No 500.** Exceção não prevista agora responde uma frase fixa, com o
traço de pilha indo para o log. Traço de pilha em resposta conta a
estrutura de pastas, as bibliotecas instaladas e às vezes trechos de
consulta com dado dentro.

A rota raiz deixou de anunciar nome, versão e caminho da documentação.

## 16. Restringir uploads

São dois, e os dois já tinham limite próprio:

- **avatar**: 400 KB, e o formato é conferido pelos bytes iniciais do
  arquivo, não pela extensão;
- **CSV de importação**: 512 KB, 500 nomes, binário recusado.

O buraco estava antes: as duas verificações acontecem com o arquivo já
inteiro na memória. Um POST de um gigabyte derrubaria o servidor antes
de qualquer uma delas rodar.

`LimiteDeCorpo`, em `app/core/seguranca_http.py`, corta o corpo acima de
2 MB sem terminar de lê-lo. É ASGI puro de propósito: só nesse nível dá
para interromper a leitura no meio.

## 17. Enxugar resposta da API

Toda rota declara `response_model`, então a resposta leva os campos
listados e nada além — nunca o objeto do banco inteiro. Auditado: nenhum
contrato de saída expõe `senha_hash`, `dono_id` ou coluna interna, e há
teste de que o corpo do login e o conteúdo do token não carregam senha.

O token leva quatro campos: `sub`, `tipo`, `iat` e `exp`. Vale lembrar
que o miolo do JWT é apenas base64, e não cifra: qualquer um lê. Por
isso não entra ali nada que já não fosse do próprio dono do token.

## 18. Cabeçalhos de segurança

`CabecalhosDeSeguranca` acrescenta a toda resposta:

| Cabeçalho | Valor | Para quê |
|---|---|---|
| `Content-Security-Policy` | `default-src 'none'` | JSON não executa nada |
| `X-Content-Type-Options` | `nosniff` | o navegador não adivinha o tipo |
| `X-Frame-Options` | `DENY` | ninguém embute a API em moldura |
| `Referrer-Policy` | `no-referrer` | o endereço não vaza ao sair |
| `Permissions-Policy` | tudo desligado | a API não usa sensor nenhum |
| `Cache-Control` | `no-store` | resposta autenticada não fica em cache |
| `Strict-Transport-Security` | 1 ano | só com `FORCAR_HTTPS` |

O HSTS só sai quando o HTTPS está exigido. Prometer HSTS sem
certificado tranca o próprio dono do lado de fora, e a promessa vale
por um ano no navegador de quem já a recebeu. Ficou sem `preload` pelo
mesmo motivo: entrar na lista embutida do navegador é decisão que não
se desfaz rápido.

A política de conteúdo é afrouxada só nos caminhos da documentação, que
carregam script e estilo de CDN.

## 19. Forçar HTTPS

`ExigirHTTPS` redireciona GET e HEAD para `https` e recusa o resto com
400. Não redireciona POST de propósito: o corpo já teria viajado em
texto claro na primeira tentativa, junto do token, e redirecionar só
faria a cópia chegar limpa depois do estrago.

Atrás de proxy que termina o TLS, quem diz o protocolo original é o
`X-Forwarded-Proto`, que é lido inclusive quando vem encadeado.

Fica desligado por padrão, porque na máquina de desenvolvimento não há
certificado. **Ligar `FORCAR_HTTPS=True` no servidor de produção** — a
conferência de produção reclama se estiver desligado.

## 20. Auditoria de dependências

`pip-audit` entrou no `requirements.txt`. Roda com:

```bash
python -m pip_audit --requirement requirements.txt
```

A primeira execução achou uma falha: a `python-jose` arrasta a `ecdsa`
como dependência obrigatória, e a `ecdsa` tem uma falha de canal
lateral (PYSEC-2026-1325) que os mantenedores declararam que não vão
corrigir. O AquaSys assina com HS256, que é HMAC e não usa curva
elíptica nenhuma: o pacote vulnerável estava instalado sem sequer ser
chamado.

Trocado por **PyJWT**, que não depende da `ecdsa`. A auditoria hoje
está limpa, no `requirements.txt` e no ambiente instalado.

Uma observação para o futuro: a `passlib` não tem versão nova desde
2020. Não há falha conhecida nela e o bcrypt que ela usa é atual, mas
vale acompanhar. Se um dia for preciso sair, os hashes já gravados são
bcrypt padrão e continuam válidos com a biblioteca `bcrypt` chamada
diretamente.

---

## Limpeza do histórico

O `.env` foi versionado em dois commits antes de o `.gitignore` ser
escrito, e o repositório é público em
`github.com/Zampier21/Aquasys`. Quem clonar tem os valores, e quem já
clonou continua tendo depois de qualquer correção.

Por isso a ordem importa, e **trocar os segredos vem primeiro**.
Reescrever o histórico sem trocar não resolve nada: o valor exposto
continua valendo.

### Passo 1 — trocar os segredos

1. **Senha do PostgreSQL.** No banco:
   ```sql
   ALTER ROLE nome_do_papel WITH PASSWORD 'nova-senha-longa';
   ```
   Depois, atualizar `DATABASE_URL` no `.env`.

2. **`SECRET_KEY`.** Gerar uma nova:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Isto derruba a sessão de todo mundo, e é o efeito desejado: token
   assinado com a chave vazada deixa de valer.

3. **Chave do YouTube.** Apagar a antiga no Console do Google Cloud e
   criar outra, já restrita à YouTube Data API v3 e ao IP do servidor.

### Passo 2 — reescrever o histórico

Com os segredos já trocados, o passo seguinte é apagar o arquivo dos
commits antigos:

```bash
pip install git-filter-repo
git filter-repo --path .env --invert-paths --force
git push origin --force --all
git push origin --force --tags
```

É uma operação que **reescreve todos os commits**: os identificadores
mudam, quem tiver clone precisa clonar de novo, e não há como desfazer
sem uma cópia de segurança do repositório. Vale fazer um clone extra do
estado atual antes.

Passo opcional, depois: pedir ao GitHub, pelo suporte, que descarte o
cache dos commits antigos — eles seguem acessíveis por identificador
direto durante algum tempo.

### Passo 3 — impedir que volte

O `.gitignore` já barra o `.env`. Para garantir mesmo com `git add -f`,
vale um gancho de pré-commit:

```bash
# .git/hooks/pre-commit
#!/bin/sh
if git diff --cached --name-only | grep -qx ".env"; then
    echo "Recusado: .env não vai para o git."
    exit 1
fi
```

---

## Papel do banco

Hoje a aplicação se conecta com um papel que é dono do esquema, ou
seja, pode apagar tabela. Não precisa: no dia a dia, ela só lê e
escreve linha. Reduzir o privilégio faz com que uma falha futura na
aplicação não vire perda do banco.

O trecho abaixo **não está em `sql/`** de propósito: aquela pasta é
aplicada automaticamente pelo `criar_tabelas.py`, e este comando leva
uma senha dentro, que não pode ser versionada. Rode à mão, uma vez:

```sql
-- Papel só de dados, sem poder mudar a estrutura.
CREATE ROLE aquasys_app LOGIN PASSWORD 'escolha-uma-senha-longa';

GRANT CONNECT ON DATABASE "AquaSys" TO aquasys_app;
GRANT USAGE ON SCHEMA public TO aquasys_app;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public TO aquasys_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aquasys_app;

-- Vale também para as tabelas que as próximas migrações criarem.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aquasys_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO aquasys_app;
```

Depois disso, `DATABASE_URL` no servidor aponta para `aquasys_app`. O
papel dono continua existindo e é o que o `criar_tabelas.py` usa quando
houver migração para aplicar — o que acontece com quem administra por
perto, e não no serviço rodando.

---

## Antes de publicar

- [ ] Trocar os três segredos e reescrever o histórico do git
- [ ] `AMBIENTE=producao` no `.env` do servidor
- [ ] `DOCS_PUBLICOS=False`
- [ ] `FORCAR_HTTPS=True`, com certificado emitido
- [ ] `CORS_ORIGENS` com o domínio exato, se houver versão web
- [ ] `CONFIAR_NO_PROXY=True` somente se houver proxy reverso
- [ ] `sslmode=require` na `DATABASE_URL`, se o banco estiver em outra máquina
- [ ] Papel de aplicação com privilégio mínimo
- [ ] Chave do YouTube restrita no Console do Google Cloud
- [ ] `python -m pip_audit --requirement requirements.txt` sem achados

Com `AMBIENTE=producao`, o servidor confere os itens de configuração
sozinho e se recusa a subir se algum estiver errado. É de propósito:
subir aberto e parecendo saudável é pior do que não subir.
