# Colocar o AquaSys no ar de graça

Roteiro para publicar a API e deixar o aplicativo apontando para ela,
sem custo, para um teste de algumas semanas com poucas pessoas.

A montagem é **Render** para a API e **Neon** para o banco. Os dois
juntos, e não um só, por um motivo específico: o Postgres gratuito do
Render **expira 30 dias depois de criado** e depois é apagado com os
dados dentro. Para um teste que pode passar de um mês, isso é um prazo
de validade em cima do banco da loja. O plano gratuito do Neon não
expira.

Nenhum dos dois pede cartão.

---

## O que esperar do que é grátis

Antes de começar, o que se está aceitando:

| | Render (API) | Neon (banco) |
|---|---|---|
| Memória | 512 MB | — |
| Armazenamento | — | 0,5 GB |
| Adormece | 15 min sem visita | 5 min sem consulta |
| Tempo para acordar | até ~1 minuto | menos de 1 segundo |
| Cota mensal | 750 horas de serviço | 100 horas de banco ativo |
| Validade | não expira | não expira |

**O ponto que mais incomoda é o primeiro despertar.** O serviço
hiberna depois de 15 minutos parado, e a próxima pessoa a abrir o
aplicativo espera cerca de um minuto pela tela de login. Quem estiver
demonstrando o produto precisa saber disso, porque a primeira
impressão é justamente essa. Como contornar está em
**Manter acordado**, mais abaixo.

O banco acorda rápido o bastante para ninguém perceber, e a API já está
configurada para reconectar sozinha quando ele dorme
(`OPCOES_DO_POOL` em `app/database.py`).

Meio giga de banco parece pouco, mas as fotos das espécies são o que
pesa e são poucas dezenas. Sobra folga.

**Sobre a memória, que foi medida.** A consulta à FishBase monta um
índice de 35.731 espécies na memória do processo, e isso entrou no
projeto depois deste roteiro. Medido com `tracemalloc`: o índice ocupa
**25,6 MB**, com pico de **58 MB** durante a carga. Somado ao FastAPI,
ao SQLAlchemy e ao pyarrow, cabe nos 512 MB com folga.

O que vale saber é o efeito do hibernar: o índice morre com o processo,
então a **primeira importação depois de cada despertar** baixa nove
megabytes de novo e leva alguns segundos. Não atrapalha o uso normal,
porque só a importação depende dele.

---

## 1. Banco no Neon

1. Criar conta em [neon.com](https://neon.com) e criar um projeto.
2. **Escolher Postgres 18**, que é a mesma versão da sua máquina. Isso
   importa no passo 2: cópia de banco entre versões diferentes dá
   trabalho, entre iguais não dá nenhum.
3. Escolher a região mais próxima. O Render gratuito fica nos Estados
   Unidos, então vale usar uma região americana no Neon também: banco
   na Europa e API nos Estados Unidos somaria uma viagem de ida e volta
   do Atlântico a cada consulta.
4. Copiar a *connection string*. Ela se parece com:

   ```
   postgresql://usuario:senha@ep-algo-1234.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

   O `?sslmode=require` no fim não é enfeite: sem ele a senha e os
   dados dos clientes atravessariam a internet em texto claro, e a
   conferência de produção da API se recusa a subir sem ele.

Não há extensão a instalar. A busca do catálogo comparava sem acento
pela extensão `unaccent`, que exigia `CREATE EXTENSION` com privilégio
de superusuário em cada ambiente novo; agora usa `translate`, que é
função embutida do PostgreSQL. Um banco vazio do Neon já serve.

---

## 2. Levar os dados para lá

Duas maneiras. A primeira é mais rápida e leva tudo, inclusive as fotos
já baixadas.

### Copiando o banco que você já tem

Na sua máquina, com o PostgreSQL instalado:

```bash
pg_dump --no-owner --no-acl --format=custom --file=aquasys.dump "postgresql://usuario:senha@localhost:5432/AquaSys"
```

```bash
pg_restore --no-owner --no-acl --dbname="COLE_AQUI_A_URL_DO_NEON" aquasys.dump
```

O `--no-owner` e o `--no-acl` existem porque os papéis do seu Postgres
local não existem no Neon; sem eles o restore reclama de dono
inexistente linha por linha.

Vale olhar o que vai junto antes de mandar: se o banco local tiver
cliente de teste, ficha de brincadeira ou aquário de experimento, isso
tudo aparece no ambiente que as pessoas vão abrir.

### Ou montando do zero

Se preferir começar limpo, aponte os próprios scripts do projeto para o
Neon. No PowerShell, na pasta do projeto:

```powershell
$env:DATABASE_URL="COLE_AQUI_A_URL_DO_NEON"; python criar_tabelas.py
```

Depois os seeds, na ordem, e por fim a conta da loja com o CNPJ de
verdade da Aqualife (o script confere os dígitos verificadores e
recusa número inventado):

```powershell
$env:DATABASE_URL="COLE_AQUI_A_URL_DO_NEON"; python seed_especies.py; python seed_variedades.py; python seed_dicas.py; python baixar_imagens.py
```

```powershell
$env:DATABASE_URL="COLE_AQUI_A_URL_DO_NEON"; python criar_dono.py "Aqualife Ecossistemas" 11.222.333/0001-81 umaSenhaBoa
```

O `baixar_imagens.py` busca as fotos no Wikimedia e demora alguns
minutos.

> **Feche esse terminal quando terminar.** O `$env:DATABASE_URL` vale
> até a janela ser fechada, e a suíte de testes cria e **apaga** um
> banco derivado do que estiver nessa variável. Rodar `pytest` no
> mesmo terminal apontaria a suíte para o Neon.

---

## 3. API no Render

O arquivo `render.yaml`, na raiz do projeto, já descreve o serviço
inteiro: plano gratuito, comando de construção, comando de partida e
todas as variáveis que não são segredo.

1. Criar conta em [render.com](https://render.com) e ligar ao GitHub.
2. **New > Blueprint**, escolher o repositório `Zampier21/Aquasys`.
3. O Render lê o `render.yaml` e pede os três valores marcados como
   `sync: false`:

   - **`DATABASE_URL`** — a string do Neon, com o `?sslmode=require`.
   - **`SECRET_KEY`** — uma chave nova, gerada com:

     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(48))"
     ```

     Precisa ser diferente da que está no `.env` da sua máquina, que
     ficou no histórico do repositório. Com uma chave nova aqui e uma
     senha nova vinda do Neon, o ambiente publicado não usa nenhum dos
     segredos que vazaram.

   - **`YOUTUBE_API_KEY`** — pode deixar em branco. Só o seed de cursos
     usa, e ele roda na sua máquina.

4. Publicar. A construção instala as dependências e aplica as
   migrações pendentes.

O endereço sai como `https://aquasys-api.onrender.com`. Confira com:

```bash
curl https://aquasys-api.onrender.com/health
```

Deve responder `{"status":"ok"}`.

**Se a implantação falhar ao subir**, leia o log: com
`AMBIENTE=producao` a API confere a própria configuração e se recusa a
ligar dizendo exatamente o que está aberto. É de propósito. Subir
parecendo saudável enquanto está exposto é pior do que não subir.

---

## 4. Apontar o aplicativo

O endereço da API não está escrito no código: `lib/config.dart` o lê de
`AQUASYS_API` no momento da compilação. Então é só compilar passando o
novo endereço.

> **Os dois caminhos funcionam nesta máquina.** Medido: `flutter build
> web` em 66 segundos, `flutter build apk` em 28 segundos depois do
> primeiro. O primeiro APK demora muito mais, porque baixa 4,3 GB de
> Gradle; isso é uma vez só. O aviso do `flutter doctor` sobre
> `cmdline-tools` não impede a compilação: aquilo serve ao `sdkmanager`
> e à conferência de licença, e a licença que importa já está aceita.
>
> Escolha pelo que vai avaliar. O APK é o produto que o TCC descreve e
> é onde a notificação local existe. O navegador dispensa instalação e
> serve em iPhone, que não há como compilar aqui.

### Android, que é o que o TCC descreve

```bash
flutter build apk --release --dart-define=AQUASYS_API=https://aquasys-api.onrender.com
```

O arquivo sai em `build/app/outputs/flutter-apk/app-release.apk`. Dá
para mandar por WhatsApp ou Drive; quem for instalar precisa liberar
"instalar de fonte desconhecida" uma vez.

Nada mais precisa ser feito: aplicativo nativo não passa por CORS.

### Pelo navegador, que é o recomendado

Um link, nada para instalar, e serve em Android e iPhone:

```bash
flutter build web --release --dart-define=AQUASYS_API=https://aquasys-api.onrender.com
```

A pasta `build/web` é um site estático. Cloudflare Pages, Netlify e
GitHub Pages hospedam isso de graça e sem hibernar.

**Aqui o CORS passa a importar.** Depois de saber o endereço do site,
volte ao painel do Render e preencha `CORS_ORIGENS` com ele, exato e
com `https`:

```
CORS_ORIGENS=https://aquasys.pages.dev
```

Sem isso o navegador recusa todas as chamadas, e o erro que aparece no
console não diz "CORS" com todas as letras. Se o aplicativo abrir mas
nada carregar, é isto.

A pasta pesa 42 MB, quase tudo do CanvasKit, que é o motor de desenho
do Flutter. O navegador guarda em cache depois da primeira visita.

**O que não funciona no navegador:** a notificação local. O
`flutter_local_notifications` só existe em Android e iOS, e no
navegador o `NotificacaoService` se desliga sozinho em vez de estourar.
Então o RF011 não é observável num teste por link: o alerta aparece no
painel, mas o lembrete agendado no aparelho, não. Vale dizer isso a
quem avalia, para não registrarem como defeito.

Outra ressalva: no Flutter web o token fica no `localStorage`, que
qualquer script na página consegue ler. Para um teste interno está bem;
é mais uma razão para essa lista de origens ficar curta.

---

## 5. Preparar o ambiente para os testadores

Servidor no ar não basta: o aplicativo precisa ter o que mostrar e as
pessoas precisam de como entrar.

**A conta da loja** é criada por linha de comando, e é ela que cria as
demais:

```powershell
$env:DATABASE_URL="COLE_AQUI_A_URL_DO_NEON"; python criar_dono.py "Aqualife Ecossistemas" 11.222.333/0001-81 umaSenhaBoa
```

**As contas dos testadores** saem de dentro do aplicativo, entrando
como a loja: aba Clientes, Acessos, e um acesso por pessoa. Vale um por
testador, e não um compartilhado: aquário de um aparecendo na tela do
outro atrapalha justamente o que se quer observar. O plano básico
permite quinze acessos ativos.

**O catálogo precisa estar cheio.** Com oito peixes, o motor de
compatibilidade não tem o que mostrar, e é ele o centro do sistema.
Importe o `estoque_aqualife.csv`, que tem 58 espécies conferidas, e
revise as fichas pela tela de revisão. Vinte peixes revisados já
sustentam uma sessão de teste.

**Os cursos e as dicas** vêm dos seeds, e valem porque a aba Aprender
vazia parece defeito:

```powershell
$env:DATABASE_URL="COLE_AQUI_A_URL_DO_NEON"; python seed_cursos.py; python seed_dicas.py
```

**O que avisar a quem testa:** que a primeira abertura do dia demora
até um minuto, e que não é lentidão do sistema, é o servidor gratuito
acordando. Sem esse aviso, a primeira anotação de todo mundo vai ser
sobre desempenho, e o desempenho não é o que você quer avaliar.

---

## 6. Manter acordado

O despertar de um minuto é o que mais atrapalha uma demonstração. Dá
para evitar visitando a API de tempos em tempos, e a conta fecha:

**750 horas por mês** é a cota, e um mês tem no máximo **744 horas**.
Ou seja, dá para manter um serviço, e só um, acordado o mês inteiro,
com 6 horas de folga. Se criar um segundo serviço gratuito na mesma
conta, os dois passam a dividir a mesma cota e nenhum atravessa o mês.

Em [cron-job.org](https://cron-job.org), que é gratuito, crie um
trabalho que chame:

```
https://aquasys-api.onrender.com/health
```

a cada 10 minutos.

**Use `/health`, e não a raiz nem outra rota.** Essa rota não consulta
o banco. Uma que consultasse manteria o Neon acordado junto, e ali a
cota é de 100 horas por mês, que 24 horas por dia queimariam em quatro
dias. Com `/health`, o Render fica de pé e o banco só acorda quando
alguém realmente usa o aplicativo.

Se o teste for só em horário comercial, melhor ainda: programe o
trabalho para as horas úteis e sobra cota de sobra.

---

## 7. Durante o teste, fique de olho

- **Horas de serviço no Render.** O painel mostra o consumo do mês. Ao
  esgotar as 750, o serviço é suspenso até o mês virar.
- **Horas de banco no Neon.** Mesma ideia, com 100 horas. Estourar
  suspende o banco até a virada.
- **Espaço no Neon.** 0,5 GB. As fotos das espécies são o que cresce.
- **Log do Render.** Erro não previsto agora sai no log com o traço de
  pilha inteiro, e na resposta só uma frase genérica. Quando alguém
  disser "deu erro", o que explica o que houve está no log.

---

## Quando deixar de ser teste

Isto aqui é montagem de teste, e é honesto dizer o que ela não é. Não
há cópia de segurança automática no plano gratuito do Neon (a janela de
recuperação é de 6 horas), não há segundo servidor se o primeiro cair,
e o despertar de um minuto continua existindo sempre que o ping falhar.

Para a loja usar de verdade, no dia a dia, o passo é sair do plano
gratuito do Render (o menor plano pago não hiberna) e ligar backup no
banco. Nada no código muda: é a mesma implantação, com outro plano.

O que muda no código, e vale antes disso, é o que está em
[`seguranca.md`](seguranca.md): o RLS e o papel de banco com privilégio
mínimo, que são as duas coisas que ficaram por fazer.
