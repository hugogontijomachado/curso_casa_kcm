# Tutorial: como esta sessão foi conduzida

Registro completo de uma sessão real do Claude Code que saiu de um pedido em
linguagem natural até uma página publicada, em uma sessão. O objetivo aqui não é
o resultado científico — é **o método**: como usar o harness e como fazer
engenharia de contexto.

Tudo abaixo aconteceu de fato. Os prompts são verbatim, as decisões e os erros
também.

---

## 1. O que foi construído

Um pipeline que otimiza a geometria e calcula frequências vibracionais
harmônicas de 10 moléculas pequenas com um potencial de machine learning, mais
uma página estática única que mostra a molécula em 3D à esquerda e a lista de
resultados à direita, com animação dos modos normais.

A física veio das skills do [AtomisticSkills](https://github.com/learningmatter-mit/AtomisticSkills)
— um repositório separado, invocado como subprocesso. Este projeto **orquestra**,
não reimplementa.

Resultado: https://cursocasakcm.vercel.app

Custo aproximado: uma sessão, ~13 subagentes, 10 commits.

---

## 2. Ingredientes

### Skills usadas

| Skill | Papel |
|-------|-------|
| `superpowers:using-superpowers` | Carregada automaticamente no início. É a regra que obriga a procurar skills antes de agir. |
| `superpowers:brainstorming` | Transformou o pedido em um **spec** aprovado. Proíbe escrever código antes disso. |
| `superpowers:writing-plans` | Transformou o spec em um **plano** com tarefas e código concreto. |
| `superpowers:subagent-driven-development` | Executou o plano: um subagente por tarefa, um revisor por tarefa, uma revisão final. |
| `claude-in-chrome` | Tentada para verificação visual. **Não estava disponível** — a extensão não estava conectada. |

As três primeiras formam uma cadeia obrigatória: brainstorming → writing-plans →
execução. Nenhuma delas deixa pular para a seguinte sem aprovação humana.

### MCPs usados

| MCP | Para quê | Resultado |
|-----|----------|-----------|
| **Vercel** | `deploy_to_vercel` para publicar | **Falhou.** Ver seção 6. |
| **Vercel** | `get_project_deployment_protection` para diagnosticar o 302 | 404 — autenticado em escopo diferente. |
| **context7** | Documentação atual do 3Dmol.js | Funcionou, via CLI `npx ctx7@latest`. |

Lição já aqui: **dois de três usos de MCP falharam**, e o trabalho seguiu porque
havia alternativa por CLI. Não desenhe um fluxo que só funciona se o MCP
funcionar.

### Ferramentas de linha de comando

- `npx ctx7@latest library` / `docs` — documentação atualizada de bibliotecas
- `npx vercel deploy --prod --yes` — deploy que de fato funcionou
- Scripts da skill SDD: `sdd-workspace`, `task-brief`, `review-package`

---

## 3. O fluxo, fase a fase

### Fase 0 — O pedido

Prompt verbatim:

> escolha 10 moleculas simples com até 20 atomos, de prefrencia menos de 12. Use
> o atomistic skills que está localmente em "/Users/hugocemep/GitHub/AtomisticSkills",
> escolha o potencial de IA simples, calcule uma otimizacao molecular e calcule
> frequencias para cada molecula. Após, iremos desenvolver um app simples, pode
> ser HTML react etc de uma pagina apenas (o objetivo é rodar no vercel, utilize
> apenas tecnologias que funcione na vercel versao gratis) que apresentará o
> resultado de todas as moleculas calculardas, com a molecula desenhada na
> esquerda e a lista de resultados na direita. Use o mcp context7 para escrita de
> codigo, utilize o MCP da vercel ao final para implementar isso tudo. De inicio,
> vamos usr todo o fluxo do using-superpowers para planejar e executar. Todo o
> planejamento sera feito usando o superpower. Vamos buscar uma maneira simples,
> todo o planejamento e execucao tem que caber + ou - em uma sessao, o objetivo é
> ter um resultado rapido.

**O que esse prompt faz de certo**, e vale copiar:

1. **Dá o caminho absoluto** do recurso local. Sem isso o agente gasta turnos
   procurando.
2. **Define a restrição de plataforma** ("apenas tecnologias que funcionem na
   Vercel versão grátis"). Restrição explícita elimina um espaço inteiro de
   escolhas ruins.
3. **Descreve o layout** ("molécula na esquerda, lista na direita"). Uma frase
   que evita três rodadas de ajuste.
4. **Nomeia o processo** ("todo o fluxo do using-superpowers"). Isso muda o
   comportamento do agente do começo ao fim.
5. **Declara o orçamento** ("tem que caber em uma sessão", "resultado rápido").
   Isso é o que faz o agente escolher HTML estático em vez de Next.js.

### Fase 1 — Brainstorming (spec)

O agente primeiro **explorou o contexto**: listou o repositório de destino
(vazio), o AtomisticSkills, as skills disponíveis, os ambientes conda, e leu o
`SKILL.md` da skill de vibração.

Aí veio a parte decisiva, e é onde a maior parte do tempo de planejamento se
paga: **o agente rodou testes de fumaça antes de propor qualquer coisa.**

```bash
# Descobriu que MACE-OFF23-small já estava em cache local
ls ~/.cache/mace/

# Rodou H2O de ponta a ponta para ver se a API funcionava
PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
~/miniforge3/envs/mace-agent/bin/python -c "..."
```

Isso revelou quatro coisas que o plano dependia e que ninguém sabia:

- `conda` e `timeout` **não existem** no shell não-interativo
- `pytest` **não está instalado** no ambiente
- a API é `wrapper.create_calculator()`, não `get_calculator()`
- a skill classifica um modo rotacional do H₂O como "imaginário" — erro dela

**Princípio:** verifique antes de planejar. Um plano escrito sobre suposições
gera cinco rodadas de correção; um plano escrito sobre fatos medidos executa
direto. As quatro descobertas acima viraram a seção "Global Constraints" do
plano, e nenhum dos 13 subagentes tropeçou nelas.

#### Decisões da Fase 1

O agente perguntou com `AskUserQuestion` — opções concretas, com trade-off, e a
recomendação em primeiro lugar.

| Pergunta | Opções | Resposta |
|----------|--------|----------|
| Conjunto de 10 moléculas | Orgânico clássico (recomendado) / trocar benzeno por menor / incluir halogenados | **Orgânico clássico** |
| Stack do app | HTML estático + 3Dmol.js (recomendado) / Next.js + React / SVG 2D | **HTML estático** |
| Animar os modos normais? | Sim, com animação (recomendado) / só estático | **Sim** |

Depois o agente apresentou o design em seções e pediu aprovação:

> **aprovado**

E então escreveu o spec em `docs/superpowers/specs/`, commitou, e pediu revisão:

> **aprovado**

### Fase 2 — Writing-plans

O plano virou um documento com **o código completo de cada arquivo** — não
descrições. A regra da skill é explícita: nada de "adicione tratamento de erro
apropriado", nada de "escreva testes para o acima". Se é código, o código está
lá.

O plano também carrega um bloco **Global Constraints** com os fatos medidos na
Fase 1, copiados literalmente. Todo subagente recebe esse bloco.

Antes de escrever, o agente consultou o context7 sobre o 3Dmol.js:

```bash
npx ctx7@latest library "3Dmol.js" "animate normal mode vibration"
npx ctx7@latest docs /websites/3dmol_doc "viewer.vibrate, addModel with frames"
```

Isso mudou o design: descobriu-se que `viewer.vibrate()` lê colunas extras
`dx dy dz` de um XYZ, o que eliminou a necessidade de gerar quadros de animação à
mão **e** de exportar uma lista de ligações no JSON.

**Princípio:** consultar documentação atual antes de escrever é mais barato que
depurar uma API que você lembrou errado.

### Fase 3 — Execução por subagentes

Escolha oferecida ao humano:

> **1. Subagent-Driven (recomendado)** — subagente novo por tarefa, revisão entre
> tarefas
> **2. Execução inline** — executa nesta sessão com checkpoints

Resposta: **`1`**

Depois, um empurrão para começar:

> **continue subagent driven development**

O ciclo por tarefa, repetido 5 vezes:

```
1. gerar o brief da tarefa em arquivo    (scripts/task-brief PLANO N)
2. registrar o commit BASE               (git rev-parse HEAD)
3. despachar o implementador             (Agent, com modelo escolhido)
4. gerar o pacote de revisão em arquivo  (scripts/review-package PLANO BASE HEAD)
5. despachar o revisor                   (Agent, spec + qualidade)
6. se houver achado: rodada de correção + re-review escopada
7. anotar no ledger e ir para a próxima
```

#### Seleção de modelo por tarefa

Isto importa para custo e velocidade:

| Tarefa | Modelo | Por quê |
|--------|--------|---------|
| 1 — tabela de moléculas | **haiku** | O plano já traz o código pronto. É transcrição. |
| 2 — cálculo de uma molécula | **sonnet** | Subprocesso, cache do ASE, verificação numérica. |
| 3 — orquestração | **sonnet** | Integração + julgamento sobre falhas. |
| 4 — página web | **sonnet** | Transcrição + verificação sem navegador. |
| 5 — README | **haiku** | Texto ditado no prompt. |
| Revisores de tarefa | **sonnet** | Piso para revisão; haiku dá muitas voltas. |
| Re-review de 1 linha | **haiku** | Diff trivial. |
| **Revisão final** | **opus** | A única que olha o conjunto. Vale o custo. |

**Regra prática:** quando o prompt contém o código a escrever, use o modelo mais
barato. Quando exige julgamento sobre o todo, use o mais capaz. Nunca omita o
modelo — omitir herda o mais caro da sessão.

#### Verificação visual — o limite dos subagentes

A Task 4 pedia confirmar quatro coisas na página renderizada. Nenhum subagente
consegue: não têm navegador. O agente principal também não conseguiu (a extensão
do Chrome não estava conectada).

Solução: pedir ao humano.

> Abra **http://localhost:8765/** e me diga se estes quatro pontos funcionam:
> 1. As 10 abas aparecem no topo
> 2. A molécula renderiza em 3D e gira ao arrastar
> 3. Clicar numa frequência anima o modo; clicar de novo para
> 4. Trocar de aba troca a molécula e a lista

Resposta: **aprovadissimo**

**Princípio:** saiba o que o agente *não* pode verificar e peça explicitamente.
O erro seria o subagente afirmar "verifiquei visualmente" sem ter olhado.

### Fase 4 — Revisão final

Um único subagente em **opus**, com o diff do branch inteiro, instruído a
verificar os números por conta própria em vez de conferir o relatório.

Ele achou coisas que nenhuma revisão por tarefa poderia achar, porque cada uma só
via uma tarefa:

- A energia de ponto zero publicada somava sobre **todos** os 3N modos, incluindo
  translação e rotação residuais — enquanto a tabela ao lado mostrava só os
  vibracionais. Incoerência **entre** tarefas.
- O rodapé da página afirmava algo que a aba do CO₂ contradizia.
- Erros factuais no README que o próprio agente principal tinha escrito.

E também confirmou o que estava certo, medindo: geometria do H₂O dentro de
0,001 Å do experimental; as degenerescências emergindo sozinhas do Hessiano.

### Fase 5 — Encerramento

Prompt:

> vamos publicar como está, mas vamos documentar todos os achados, problemas para
> uma correçao futura. Apos a publicacao e encerramento, faremos uma rodada de
> conferencia de documentacao (…) vamos garantir que todo contexto util sobreviva
> a proxima sessao (…) faca um handoff.md em docs/

Produziu: `docs/handoff.md`, `CLAUDE.md`, o ledger preservado, e memórias
persistentes.

---

## 4. Todos os pontos de decisão

Oito perguntas ao longo da sessão. Note o padrão: **o agente nunca perguntou algo
que pudesse decidir sozinho**, e sempre apresentou uma recomendação.

| # | Fase | Pergunta | Resposta |
|---|------|----------|----------|
| 1 | Brainstorm | Qual conjunto de 10 moléculas? | Orgânico clássico |
| 2 | Brainstorm | Qual stack para a Vercel free? | HTML estático + 3Dmol.js |
| 3 | Brainstorm | Animar os modos normais? | Sim |
| 4 | Task 3 | O pareamento com experimento é defeituoso, mas veio do plano. Qual prevalece? | Manter o plano |
| 5 | Task 3 | Como tratar a limitação do MACE no CO₂? | Documentar no README |
| 6 | Task 4 | Dois achados, ambos código que o plano mandou. Corrigir? | Só o `stopAnimate()` |
| 7 | Final | 7 achados da revisão final. Corrigir? | Publicar como está + documentar |
| 8 | Final | Reavaliar duas decisões que a revisora contestou? | Não corrigir nada |

As perguntas 4, 6 e 7 são de um tipo específico e importante: **o revisor achou
defeito no código que o próprio plano mandou escrever.** A skill é explícita
nesse caso — o agente não pode nem descartar o achado (porque o plano manda) nem
contrariar o plano (porque o humano aprovou). Tem que apresentar os dois lados e
perguntar qual prevalece.

---

## 5. Engenharia de contexto: as técnicas concretas

Este é o núcleo do tutorial. A sessão terminou usando **10% de 1M de tokens**
apesar de 13 subagentes e ~96 kB de diffs revisados. Como:

### 5.1 Passe arquivos, não conteúdo

Errado:

```
prompt: "Aqui está a tarefa: [cola 200 linhas do plano]
         Aqui está o diff: [cola 8 kB]"
```

Certo:

```bash
scripts/task-brief PLANO 2      # → .../task-2-brief.md
scripts/review-package PLANO BASE HEAD   # → .../review-a..b.diff
```

```
prompt: "Leia primeiro: .../task-2-brief.md
         Diff sob revisão: .../review-a..b.diff"
```

O conteúdo **nunca entra no contexto do agente coordenador**. Ele só manda
caminhos. O que você cola num prompt fica residente pelo resto da sessão e é
relido a cada turno.

### 5.2 Não leia o transcript dos subagentes

Cada subagente escreve um `.output` em JSONL. O da revisão final tinha **424 kB**.
Ler isso estouraria o contexto.

Mas dá para medir sem ler — foi assim que se diagnosticou o agente travado:

```bash
wc -lc "$F"; sleep 30; wc -lc "$F"     # cresceu? está vivo
```

### 5.3 O relatório vai para arquivo, o resumo vem no retorno

Todo subagente recebeu esta instrução:

> Escreva seu relatório completo em `.../task-N-report.md`.
> Depois responda **apenas** (menos de 15 linhas): status, commits, resumo dos
> testes em uma linha, preocupações, e o caminho do relatório.

O detalhe fica no disco; o coordenador recebe 10 linhas.

### 5.4 O ledger sobrevive à compactação

Um arquivo `progress.md` com uma linha por evento:

```
Task 1: complete (commits b8fd941..175215f, review clean)
Task 2: minor (deferred): subprocess.run sem timeout
Task 3: parked — pareamento greedy mispareia modos degenerados — ruling: humano manteve
```

Se o contexto for compactado no meio, o ledger e o `git log` são a verdade — não
a memória do agente. Sem isso, um coordenador que perdeu o fio **redespacha
tarefas já concluídas**, que é a falha mais cara possível.

### 5.5 Não empilhe histórico nos despachos

Cada prompt de subagente descreve **uma** tarefa. Nada de "estado após as tarefas
1 a 3". Um subagente novo precisa da sua tarefa, das interfaces que toca e das
restrições globais. Mais nada.

### 5.6 Dê ao revisor os fatos de domínio

Sem isso, o revisor reporta decisões deliberadas como defeitos. Exemplo real,
incluído em todos os prompts de revisão:

> A skill classifica modos por um limiar fixo de 50 cm⁻¹ e erra: no H₂O um modo
> rotacional aparece como 52,7i cm⁻¹. **Por isso** o código descarta exatamente 5
> ou 6 modos pela regra de linearidade. Usar o `real_modes` da skill é que seria
> o bug.

Mas o inverso é proibido: **nunca instrua um revisor a não reportar algo.** Se
você acha que seria falso positivo, deixe ele levantar e julgue depois.

### 5.7 Verifique o que atravessa uma fronteira

Antes do deploy, o agente registrou os checksums:

```bash
shasum -a 256 web/data.json web/index.html
```

E depois comparou com o publicado. Isso pegou de imediato que o site retornava
302 (proteção) em vez do conteúdo — os dois "checksums" iguais eram a mesma
página de redirect.

---

## 6. Os três erros da sessão, e o que eles ensinam

### Erro 1 — O MCP da Vercel travou um agente por 10 minutos

A ferramenta `deploy_to_vercel` exige o conteúdo dos arquivos **inline, no
próprio parâmetro**. O `data.json` tem 64 kB de dados científicos gerados.

Um subagente ficou 10 minutos tentando transcrever isso. E o risco não era só
lentidão: **um único dígito alterado corromperia dados científicos silenciosamente.**

O que salvou: o agente tinha antecipado o risco e embutido verificação por
checksum no prompt do subagente. E o humano notou o travamento:

> verifique a task em background ela pode estar travada, eu ja autorizei a vercel,
> mas nao fizemos commit e push no github ainda

Com o CLI autenticado, a solução era trivial — `npx vercel deploy --prod --yes`
faz upload byte-exato, sem modelo nenhum no meio. O próprio subagente tinha
chegado à mesma conclusão antes de ser encerrado.

**Lição:** ferramentas que exigem conteúdo inline não servem para dados grandes.
Prefira ferramentas que operam sobre arquivos no disco. E **sempre verifique
integridade** quando o dado atravessa um modelo.

### Erro 2 — A revisão final demorou e quase foi abortada

8,5 minutos. O humano cobrou:

> a revisao esta demorando mais que o esperado confira

O diagnóstico foi feito medindo o crescimento do arquivo de saída sem lê-lo. Ela
progrediu e terminou — e foi a revisão que achou os problemas mais sérios.

**Lição:** o pacote de revisão tinha 96 kB, dos quais 64 kB eram JSON gerado. Dá
para excluir dados gerados do pacote de revisão e ficar com o código real.
Vale fazer isso na próxima.

### Erro 3 — O agente publicou um erro factual

No README, o agente escreveu "as demais nove moléculas, **todas orgânicas**".
H₂O e NH₃ não são orgânicas. Pior: isso derruba o argumento causal que a seção
tentava construir.

Nenhuma revisão por tarefa pegou — o texto foi ditado no prompt do subagente, que
o transcreveu fielmente como mandado. Só a revisão final, lendo o conjunto com
olhar crítico, pegou.

**Lição:** conteúdo que o coordenador dita no prompt não passa por revisão de
verdade — o subagente vai transcrever, não questionar. Se você ditar afirmações
factuais, elas precisam de uma revisão explícita depois.

---

## 7. Como replicar

### Passo a passo

1. **Escreva o pedido com caminhos absolutos, restrições de plataforma, o layout
   desejado e o orçamento de tempo.** Peça o fluxo do superpowers explicitamente.

2. **Deixe o brainstorming rodar.** Responda as perguntas. Não pule para o
   código — a skill não deixa, e é bom que não deixe.

3. **Exija testes de fumaça antes do plano.** Se o agente não propuser, peça:
   "verifique que a API funciona antes de escrever o plano". Isso é o que
   diferencia um plano que executa direto de um que precisa de cinco correções.

4. **Leia o plano.** É o único artefato que você precisa ler com atenção. Se o
   plano estiver certo, a execução tende a sair certa.

5. **Escolha subagent-driven.** Responda as perguntas de adjudicação quando o
   revisor discordar do plano.

6. **Faça você a verificação visual.** O agente não consegue ver a tela.

7. **Peça a revisão final em opus**, instruída a verificar os números em vez de
   conferir o relatório.

8. **Termine com handoff.** Peça explicitamente `docs/handoff.md`, `CLAUDE.md` e
   memórias. Contexto perdido entre sessões custa mais que defeito documentado.

### Prompts que valem copiar

Para forçar verificação antes do plano:

> Antes de escrever o plano, rode um teste de fumaça de ponta a ponta do caminho
> crítico e me diga o que descobriu. Não escreva placeholders no plano.

Para o revisor final:

> Verifique os números por conta própria em vez de conferir o relatório. Estes
> fatos de domínio justificam decisões de design e não são defeitos: [lista].
> Estes achados já foram julgados pelo humano — não relitigue, mas me diga se
> algum é mais grave do que o julgamento supôs: [lista].

Para o handoff:

> Documente todos os achados, decisões e problemas em aberto num docs/handoff.md,
> com localização exata, número verificado e correção proposta de cada item, de
> modo que a próxima sessão não precise reinvestigar nada.

---

## 8. Onde ficou cada coisa

| Arquivo | Conteúdo |
|---------|----------|
| `docs/superpowers/specs/` | O spec aprovado na Fase 1 |
| `docs/superpowers/plans/` | O plano com o código de cada tarefa |
| `docs/superpowers/ledger-2026-08-08-execucao.md` | Ledger: cada tarefa, cada achado, cada ruling |
| `docs/handoff.md` | Estado, decisões e backlog de 8 correções pendentes |
| `CLAUDE.md` | O que um agente precisa saber antes de tocar no repo |
| `docs/tutorial-sessao.md` | Este arquivo |
