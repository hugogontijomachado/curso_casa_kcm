# curso_casa_kcm

Otimização de geometria e frequências vibracionais harmônicas de 10 moléculas
pequenas com o potencial de machine learning MACE, publicadas como página
estática única. Material para curso.

**Leia `docs/handoff.md` antes de começar qualquer trabalho.** Ele traz o estado
atual, as decisões já tomadas, o que foi descoberto e o backlog de correções
pendentes com localização e correção de cada uma.

## Ambiente — armadilhas conhecidas

Estas custaram tempo para descobrir. Não redescubra.

- **`conda` e `timeout` não existem** no shell não-interativo. Use o
  interpretador direto: `/Users/hugocemep/miniforge3/envs/mace-agent/bin/python`.
  Para limitar tempo de execução, use o parâmetro `timeout` da ferramenta Bash.
- **`PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills` é obrigatório** para
  qualquer script deste repositório.
- **`ATOMISTIC_SKILLS`** é a variável que `scripts/run_molecule.py` usa para
  localizar a skill; seu default é o mesmo caminho absoluto. É ela que alimenta o
  `cwd` do subprocesso. Em outra máquina, defina as duas.
- **`pytest` não está instalado e não deve ser instalado** — `mace-agent` é um
  ambiente de pesquisa. Os testes são scripts Python com `assert` puro:

      PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
      ~/miniforge3/envs/mace-agent/bin/python tests/test_molecules.py

- **A API do wrapper MLIP é `wrapper.create_calculator()`**, não
  `get_calculator()`. `wrapper.calculator` é `None` até essa chamada.
- **Modelo: `MACE-OFF23-small`**, já em cache em `~/.cache/mace/`. Não troque sem
  motivo — é o force field MACE treinado em moléculas orgânicas neutras.

## Estrutura

| Caminho | Papel |
|---------|-------|
| `scripts/molecules.py` | Tabela das 10 moléculas. Sem lógica de cálculo. |
| `scripts/run_molecule.py` | Cálculo de uma molécula: relaxa, chama a skill, extrai autovetores. |
| `scripts/run_all.py` | Orquestra as 10, isola falhas, valida, escreve `web/data.json`. |
| `web/index.html` | Página única. Único consumidor de `data.json`. Sem build step. |
| `web/data.json` | Contrato entre o pipeline e a página. Gerado, versionado. |
| `results/` | Saídas brutas por molécula. Ignorado pelo git. |
| `docs/handoff.md` | **Estado, decisões e backlog. Comece por aqui.** |

O pipeline Python e a página são desacoplados: o único contrato entre eles é
`web/data.json`. A página não sabe nada de ASE, MACE ou conda.

## Regenerar os resultados

    PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
    ~/miniforge3/envs/mace-agent/bin/python scripts/run_all.py

Leva alguns minutos; o benzeno (12 átomos, 36 deslocamentos) domina o tempo.
Imprime a validação e a comparação com valores experimentais no terminal.

**Cuidado:** hoje esse script sobrescreve `web/data.json` incondicionalmente,
mesmo se todas as moléculas falharem (item F5 do handoff).

## Deploy

Use o CLI, **não** a ferramenta MCP `deploy_to_vercel` — ela exige o conteúdo dos
arquivos inline, e transcrever 64 kB de JSON científico por um modelo arrisca
corromper os dados silenciosamente. Isso já travou um agente por 10 minutos.

    npx vercel deploy --prod --yes

Depois confira a integridade comparando checksums do publicado contra o local:

    U=https://cursocasakcm.vercel.app
    curl -s $U/data.json | shasum -a 256
    shasum -a 256 web/data.json

## Sobre os números

As frequências são **harmônicas** e ficam tipicamente ~5% acima das fundamentais
experimentais, que incluem anarmonicidade. O CO₂ é a exceção instrutiva: fica
6–18% *abaixo*, porque o potencial não descreve bem essa molécula. Ao mexer em
qualquer coisa que afete os números, preserve essa honestidade — o público é uma
turma, e o valor didático está justamente em mostrar onde o modelo falha.
