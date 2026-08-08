# Handoff — estado do projeto e próximos passos

**Última sessão:** 2026-08-08
**Estado:** publicado e funcionando. Nenhuma correção pendente é bloqueante.

Este documento existe para que a próxima sessão comece sabendo o que já foi
decidido, o que foi descoberto, e o que ficou por fazer — sem repetir
investigação.

---

## O que está no ar

- **Página:** https://cursocasakcm.vercel.app
- **Repositório:** https://github.com/hugogontijomachado/curso_casa_kcm
- **Projeto Vercel:** `curso_casa_kcm` (`prj_vkrPifrRSmIPbO8m3BL50dZQGc4m`),
  deploy estático via `vercel.json` com `outputDirectory: "web"`.

Verificado: `index.html` e `data.json` servidos com HTTP 200 e SHA-256
byte-idêntico aos arquivos locais. Apenas a *URL de deployment* tem Deployment
Protection; o alias de produção é público.

## O que o projeto faz

Otimiza a geometria e calcula as frequências vibracionais harmônicas de 10
moléculas pequenas com o potencial de machine learning `MACE-OFF23-small`,
através da skill `chem-vibration` do repositório
[AtomisticSkills](https://github.com/learningmatter-mit/AtomisticSkills), e
publica o resultado numa página estática única com visualização 3D e animação
dos modos normais.

Moléculas: H₂O, CO₂, NH₃, H₂CO, C₂H₂, CH₄, CH₃OH, C₂H₄, C₂H₆, C₆H₆.

---

## Fatos do ambiente que custaram tempo para descobrir

Não redescubra isto.

| Fato | Consequência |
|------|--------------|
| `conda` e `timeout` **não existem** no shell não-interativo | Use `/Users/hugocemep/miniforge3/envs/mace-agent/bin/python` direto. Para limitar tempo, use o parâmetro `timeout` da própria ferramenta Bash. |
| `pytest` **não está** no env `mace-agent` | Os testes são scripts Python com `assert` puro, rodados diretamente. Não instale pytest — o env é de pesquisa. |
| `PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills` é obrigatório | Sem isso, `from src.utils.mlips.loader import load_wrapper` falha. |
| O wrapper MLIP **não tem** `get_calculator()` | A API é `load_wrapper(...)` → `wrapper.create_calculator()`. `wrapper.calculator` é `None` até essa chamada. |
| `MACE-OFF23-small` já está em cache (`~/.cache/mace/`, 7 MB) | Não baixe outro modelo. É o force field MACE treinado em moléculas orgânicas neutras — a escolha certa para este conjunto. |
| A ferramenta MCP `deploy_to_vercel` exige conteúdo **inline** | Um agente ficou 10 min travado tentando transcrever 64 kB de JSON, com risco real de corromper dados científicos. **Use o CLI:** `npx vercel deploy --prod --yes`. O CLI já está autenticado como `hugogontijomachado`. |

## Descobertas científicas que moldaram o design

**A classificação de modos da skill está errada e não deve ser usada.** A skill
`chem-vibration` classifica modos por um limiar fixo de 50 cm⁻¹. No H₂O um modo
*rotacional* aparece como 52,7i cm⁻¹ — ruído numérico das diferenças finitas — e
é rotulado "imaginário", sugerindo falsamente que a geometria não é um mínimo.
Verificado: apertar `fmax` de 1e-4 para 1e-5 **não** elimina o ruído (as
frequências reais ficam idênticas). Por isso `classify_vibrational_indices` em
`scripts/run_molecule.py` descarta exatamente 5 ou 6 modos de menor magnitude
pela regra de linearidade, e **ignora o campo `real_modes` da skill**.

A margem dessa regra é folgada e foi medida: nas 10 moléculas, o maior modo
descartado é 52,7 cm⁻¹ e o menor mantido é 284,4 cm⁻¹ (CH₃OH).

**A física do resultado foi verificada independentemente.** Geometria do H₂O:
d(O–H) = 0,9587 Å e ∠HOH = 104,96°, contra 0,9578 Å / 104,48° experimentais. As
degenerescências emergem sozinhas do Hessiano, sem nada no código forçá-las:
CO₂ dá o padrão π_u/σ_g/σ_u, CH₄ dá T₂/E/A₁/T₂, e os 30 modos do benzeno pareiam
em dupletos de simetria e. Essa é a evidência mais forte de que o Hessiano está
correto.

**O CO₂ é o caso didático.** Calculado 545,4 / 1248,9 / 2170,4 cm⁻¹ contra
667 / 1333 / 2349 experimentais — todos **abaixo**, invertendo o sinal esperado
da aproximação harmônica. As outras nove ficam dentro do esperado. Ver o item
F5 abaixo: a explicação publicada no README está imprecisa e precisa ser
corrigida.

---

## Backlog de correções

Nenhuma é bloqueante — a química publicada está correta. Estão em ordem de
impacto para o público do curso. Todas foram levantadas por uma revisão de
branch inteiro que verificou os números independentemente, e o humano decidiu
publicar como está e corrigir numa sessão futura.

### F1 — A ZPE mostrada não é a ZPE dos modos mostrados ao lado dela

**Onde:** `scripts/run_molecule.py`, no campo `zpe_eV` de `compute_molecule`.

O valor vem de `resultado_skill["zero_point_energy_eV"]`, que é o
`vib.get_zero_point_energy()` do ASE — meio somatório sobre **todos os 3N**
modos, sem classificação nenhuma. Os modos residuais de translação e rotação
entram na conta.

Isto é uma incoerência conceitual: o projeto decidiu explicitamente não confiar
na classificação de modos da skill, e então importou uma ZPE derivada desse
mesmo conjunto não classificado.

Verificado no H₂O: `data.json` reporta 0,58786 eV; ½Σhν sobre os três modos
listados dá 0,58432 eV. A diferença de 0,00354 eV é exatamente
½·(0,0 + 0,0 + 0,1 + 27,6 + 29,4) cm⁻¹, os modos residuais.

Contaminação por molécula, em cm⁻¹:

| h2o | h2co | c2h4 | c2h2 | co2 | c6h6 | ch3oh | nh3 | c2h6 | ch4 |
|-----|------|------|------|-----|------|-------|-----|------|-----|
| 28,6 | 13,9 | 13,1 | 12,4 | 6,9 | 5,1 | 3,5 | 1,4 | 0,2 | 0,0 |

O erro é ≤0,6%, mas um aluno que somar a tabela exibida — exatamente o exercício
que a página convida a fazer — não reproduz o número mostrado ao lado.

**Correção:** somar ½hν sobre os modos já classificados, dentro de
`compute_molecule`. Duas linhas. **Atenção:** `tests/test_run_molecule.py` fixa o
valor contaminado 0,5875 como referência, então o teste precisa ser atualizado
no mesmo commit — hoje ele *fixa o bug*.

Regerar `web/data.json` e refazer o deploy depois.

### F2 — O rodapé da página contradiz a própria aba do CO₂

**Onde:** `web/index.html`, no texto do rodapé montado em `iniciar()`.

O rodapé afirma, incondicionalmente e em todas as 10 abas, que as frequências
"ficam sistematicamente acima das fundamentais medidas experimentalmente". No
CO₂ ficam 6% a 18% *abaixo*.

A ressalva honesta existe no `README.md`, mas o README **não está publicado** —
`/README.md` dá 404 no site, porque `outputDirectory: "web"` (corretamente) só
serve `web/`. A melhor parte do trabalho está invisível no ponto de uso.

**Correção:** hedgear o texto do rodapé e adicionar uma nota por molécula.
Melhor solução: um campo `nota` opcional em cada molécula do `data.json`, para a
página continuar orientada a dados em vez de ter texto especial para o CO₂
embutido no JavaScript.

### F3 — Erros factuais no README

**Onde:** `README.md`, seção "Limitação conhecida: CO₂".

Três problemas, em ordem de gravidade:

1. **"As demais nove moléculas, todas orgânicas"** — H₂O e NH₃ **não são
   orgânicas**. Erro factual num README de química.
2. **O argumento causal está errado por consequência.** A história publicada é
   "o CO₂ falha porque não é orgânico" — mas H₂O e NH₃ também não são orgânicas
   e saem bem (H₂O +2,3%/+5,1%/+5,1%; NH₃ entre +2,6% e +10%). A explicação
   correta é mais fina: o MACE-OFF23 foi treinado no SPICE, dominado por
   orgânicos tipo fármaco e seus ambientes aquosos, então água está
   abundantemente representada, enquanto uma molécula linear com duplas C=O
   cumuladas não está. **É sobre qual motivo de ligação está representado, não
   sobre orgânico vs. inorgânico.**
3. **Afirma como fato que o CO₂ "não estava no seu conjunto de treinamento"** —
   nada neste trabalho verificou o conteúdo do SPICE. Deve ser apresentado como
   a explicação provável, não como fato conferido.
4. **Publica valores experimentais (667, 1333, 2349 cm⁻¹) sem citação.** O
   próprio spec do projeto definiu o padrão oposto: "Publicar números
   experimentais exige citação precisa da fonte" — foi por isso que eles ficaram
   fora da página. Citar NIST WebBook ou Herzberg. O mesmo vale para o dicionário
   `REFERENCIAS_EXPERIMENTAIS` em `scripts/run_all.py`, atribuído apenas a
   "tabelas espectroscópicas padrão".

Vale também citar o próprio MACE-OFF23 — é o modelo a partir do qual se está
ensinando.

### F4 — As instruções de reprodução não funcionam em outra máquina

**Onde:** `README.md`, seção "Reproduzir os cálculos".

O README manda exportar `PYTHONPATH`. Mas `scripts/run_molecule.py` resolve a
localização da skill pela variável **`ATOMISTIC_SKILLS`**, cujo default é o
caminho absoluto `/Users/hugocemep/GitHub/AtomisticSkills`, e é ela que alimenta
`VIB_SCRIPT` e o `cwd=` do subprocesso. O README nunca menciona essa variável.

Seguindo o README em outra máquina, `PYTHONPATH` satisfaz o import de
`load_wrapper`, e depois `subprocess.run(..., check=True, cwd=<inexistente>)`
levanta exceção nas 10 moléculas.

O mecanismo é são — variável de ambiente com default. Só falta documentar. Uma
linha.

Secundário: `~/miniforge3/envs/mace-agent/bin/python` está hardcoded sem
`environment.yml` e sem instruções para criar o env `mace-agent`. No mínimo,
dizer que a especificação do ambiente vive no repositório AtomisticSkills.

### F5 — Um re-run que falhe destrói o dataset publicado

**Onde:** `scripts/run_all.py`, na escrita de `web/data.json`.

O arquivo é escrito incondicionalmente, mesmo com `registros == []`. Combinado
com o F4, a primeira coisa que a execução de um novo usuário faz é sobrescrever
o `data.json` bom de 62 kB com `"molecules": []`. É recuperável pelo git, mas se
fosse commitado e deployado a página ao vivo viraria uma casca vazia.

**Correção:** recusar a escrita quando `registros` estiver vazio ou for menor
que `MOLECULES`.

### F6 — Duas "validações" que não podem falhar

**Onde:** `scripts/run_all.py`, função `validar`.

`esperado = 3n − (5 se linear else 6)` é comparado com `len(r["modes"])`. Mas
`classify_vibrational_indices` retorna `ordem[n_trans_rot:]`, cujo comprimento é
**por construção** exatamente `3n − (5 ou 6)`, a partir do mesmo `is_linear`.
Mesma fórmula, mesma entrada, dos dois lados. A checagem é tautológica e nunca
pode reportar problema — e o README a anuncia como uma das três validações.

Agravante: `MoleculeSpec.expected_linear` (`scripts/molecules.py`) é declarado,
documentado como "a expectativa física", e **nunca é lido em lugar nenhum**.
Então `is_linear` repousa inteiramente no teste por SVD da skill, sem conferência
independente. Se `check_linearity` errasse, o pipeline emitiria silenciosamente
um modo a mais ou a menos e a validação ainda imprimiria `ok`.

**Correção:** `assert r["is_linear"] == spec.expected_linear` em `validar`. Uma
linha, e converte uma checagem vazia numa real. (As 10 estão corretas hoje — isto
é sobre a rede de segurança, não sobre a saída atual.)

### F7 — Energia total exibida sem interpretação

**Onde:** `web/index.html`, campo "Energia potencial" da ficha.

Mostra o `energy_eV` cru — para o H₂O, "−2081,121 eV". Isso é a energia total do
MACE **incluindo energias de referência atômica por elemento**. É bem definida na
escala interna do modelo e válida para comparar geometrias da mesma molécula, mas
não é interpretável isoladamente e **não é comparável entre moléculas**. A página
convida exatamente essa comparação ao pôr o mesmo campo nas 10 abas: um aluno vai
ler "CO₂ a −5135 eV é muito mais estável que H₂O a −2081 eV", o que não significa
nada.

**Correção:** relabelar explicitamente, remover o campo, ou — melhor para um
curso — calcular a energia de atomização, que ensina alguma coisa.

### F8 — Itens menores

- **Amplitude de animação não normalizada por modo.** `viewer.vibrate(12, 1.4,
  true)` é fixo, mas as normas cartesianas dos autovetores com peso de massa do
  ASE variam de 0,25 (estiramentos do CO₂) a ~1,0 (estiramentos X–H). Modos de
  átomos pesados animam ~4× mais sutis; na aba do CO₂ e em vários modos de anel
  do benzeno a animação quase não se vê. Escalar a amplitude por `1/‖v‖`
  igualaria a legibilidade — ganho real para uma página de demonstração.
- **3Dmol.js carregado sem versão fixa e sem tratamento de falha.** Se o CDN
  falhar, `$3Dmol.createViewer` lança `ReferenceError` não capturado e a página
  mostra abas e tabelas em volta de um retângulo cinza morto, sem mensagem. Para
  algo exibido ao vivo numa aula, fixar a versão e adicionar uma guarda
  `typeof $3Dmol === "undefined"` que renderize o painel `.erro` já existente.
- **A coluna "Modo" é peso morto** — imprime "vibração" em toda linha de toda
  molécula. O uso óbvio para este público seria degenerescência ou rótulo de
  simetria: os três 1329,3 idênticos do CH₄ são hoje três linhas duplicadas sem
  explicação.
- **`generated` renderizado como timestamp ISO ingênuo**, sem fuso horário.
- **Acoplamento não documentado ao nome do cache da skill.**
  `Vibrations(name=workdir/"vib")` casa com onde a skill por acaso escreve seu
  cache. Se a skill renomeasse, `vib.run()` recomputaria silenciosamente o
  Hessiano inteiro — resultado correto, tempo dobrado, nenhum sinal. Vale um
  comentário, ou uma checagem de que o cache existe antes de chamar `run()`.
- **`REFERENCIAS_EXPERIMENTAIS` cobre 5 das 10 moléculas.** As cinco maiores
  ficam sem nenhuma conferência de acurácia — embora sejam também as que estão
  mais dentro do domínio de treino do MACE-OFF23.
- **`subprocess.run` sem `timeout`** em `run_molecule.py`. Um travamento da skill
  bloquearia indefinidamente.
- **`n_imaginary` nunca é lido pela página.** A informação não se perde (modos
  imaginários apareceriam como linha laranja "imaginário"), só não é agregada na
  ficha.
- **`#legenda` fica com "carregando…"** no caminho de erro do fetch, ao lado do
  banner de erro.
- **`innerHTML` por interpolação sem escaping.** Não é superfície real: todo
  valor interpolado vem de `scripts/molecules.py` ou de um campo numérico de um
  JSON gerado pela própria máquina. Registrado só por completude.
- **Faltam `aria-controls` e `role="tabpanel"`** no padrão de abas.

---

## Decisões já tomadas — não relitigar sem motivo novo

Estas foram decididas pelo humano nesta sessão. Reabrir só com informação nova.

| Decisão | Racional registrado |
|---------|---------------------|
| `MACE-OFF23-small` em vez do `MACE-MH-1`/`omol` do spec | Já em cache local (7 MB, zero download) e treinado especificamente em moléculas orgânicas neutras. |
| `fmax = 1e-4` em vez de 1e-3 | Barato e mais seguro para a aproximação harmônica. |
| Sem array `bonds` no `data.json` | O 3Dmol.js deduz ligações sozinho das distâncias interatômicas. Seria dado morto. |
| Pareamento por vizinho mais próximo na tabela experimental mantido | Diagnóstico só de terminal, não vai para o `data.json` nem para a página. **Mas saiba ao ler aquela tabela:** no C₂H₂, 612 e 730 casam ambos com 718,5, e 774,7 nunca aparece — o efeito é fazer a molécula parecer *melhor* do que é (imprime −1,6% onde o par honesto daria +6,1%). |
| Linhas da tabela sem acesso por teclado, mantido | Decisão explícita do humano, contra recomendação da revisão. |
| `zoomTo()` a cada redraw, mantido | Decisão explícita do humano, contra recomendação da revisão (ela considera isto pior que "minor": descarta o ângulo de visão que o instrutor acabou de escolher). |
| Publicar sem aplicar nenhuma das correções acima | Decisão explícita do humano ao fim da sessão de 2026-08-08. |

---

## Como retomar

Ordem sugerida para a próxima sessão, do que mais importa ao público para o que
menos:

1. **F3** (erros factuais no README) — é o único erro publicado que está
   simplesmente incorreto, e é barato.
2. **F1** (ZPE) + **F2** (rodapé/nota do CO₂) — os dois que um aluno encontraria.
   O F1 exige regerar o `data.json` e atualizar o teste no mesmo commit.
3. **F4** + **F5** + **F6** — reprodutibilidade e rede de segurança.
4. **F7**, depois **F8** conforme o tempo.

Depois de qualquer mudança em `web/`, redeployar com:

```bash
npx vercel deploy --prod --yes
```

e conferir integridade comparando o SHA-256 do publicado contra o local:

```bash
U=https://cursocasakcm.vercel.app
curl -s $U/data.json | shasum -a 256
shasum -a 256 web/data.json
```

O processo completo desta sessão (spec → plano → execução por subagentes com
revisão por tarefa) está em `docs/superpowers/specs/` e
`docs/superpowers/plans/`.

`docs/tutorial-sessao.md` narra esse processo como tutorial: os prompts reais,
os oito pontos de decisão com as respostas, as técnicas de engenharia de contexto
usadas, e os três erros da sessão com o que cada um ensina.
