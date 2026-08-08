# Otimização e Frequências Vibracionais de 10 Moléculas com MLIP + App Web

**Data:** 2026-08-08
**Status:** Aprovado

## Objetivo

Calcular, com um potencial de machine learning (MLIP), a geometria otimizada e as
frequências vibracionais harmônicas de 10 moléculas pequenas, e publicar os
resultados numa página única estática na Vercel: molécula 3D interativa à
esquerda, resultados à direita, com animação do modo normal selecionado.

O público é um curso — a página precisa ser demonstrativa, não só uma tabela.

## Escopo

### Dentro do escopo

- Otimização de geometria de 10 moléculas com MACE.
- Frequências vibracionais harmônicas e energia de ponto zero (ZPE).
- Autovetores dos modos normais (para animação).
- Página estática única com visualização 3D e animação de modos.
- Deploy na Vercel (plano gratuito, sem funções serverless).

### Fora do escopo (cortado deliberadamente)

- Intensidades e espectro de IR (exigiria dipolos/polarizabilidades).
- Correções anarmônicas.
- Termoquímica (entropia, capacidade calorífica, energias livres).
- Comparação com DFT.
- Qualquer backend, banco de dados ou API.

## Moléculas

Todas disponíveis no banco de dados g2 do ASE (`ase.build.molecule`), todas com
12 átomos ou menos:

| id | Fórmula | Nome | N átomos | Linear |
|----|---------|------|----------|--------|
| `h2o`    | H2O   | Água          | 3  | não |
| `co2`    | CO2   | Dióxido de carbono | 3  | sim |
| `nh3`    | NH3   | Amônia        | 4  | não |
| `h2co`   | H2CO  | Formaldeído   | 4  | não |
| `c2h2`   | C2H2  | Acetileno     | 4  | sim |
| `ch4`    | CH4   | Metano        | 5  | não |
| `ch3oh`  | CH4O  | Metanol       | 6  | não |
| `c2h4`   | C2H4  | Eteno         | 6  | não |
| `c2h6`   | C2H6  | Etano         | 8  | não |
| `c6h6`   | C6H6  | Benzeno       | 12 | não |

A coluna "Linear" é a expectativa física; o valor efetivo é determinado pelo
código (`check_linearity` da skill) e gravado no JSON.

## Potencial

MACE, no ambiente conda `mace-agent` do repositório AtomisticSkills
(`/Users/hugocemep/GitHub/AtomisticSkills`).

- **Preferência:** `MACE-MH-1` com head `omol` — o head indicado pela skill
  `ml-foundation-potentials` para sistemas moleculares e química orgânica.
- **Fallback:** `MACE-OMAT-0-small` se o checkpoint MH-1 não estiver disponível
  localmente.

O modelo efetivamente usado é gravado em `data.json` e exibido na página. Não se
apresenta um resultado sem dizer de que modelo ele veio.

## Arquitetura

Dois estágios desacoplados, ligados por um único contrato de dados:

```
[1] Pipeline Python (local, executa uma vez)
    ASE + MACE via AtomisticSkills
        |
        v
    web/data.json          <-- único contrato entre os estágios
        |
        v
[2] App estático (Vercel)
    web/index.html + 3Dmol.js (CDN)
```

O estágio 2 não sabe nada sobre ASE, MACE ou conda. O estágio 1 não sabe nada
sobre HTML. Cada um pode ser refeito sem tocar no outro.

## Componentes

### `scripts/run_molecule.py`

Responsabilidade única: produzir o dicionário de resultados de **uma** molécula.
Executável isoladamente para depuração.

Passos:

1. Monta a geometria inicial com `ase.build.molecule(nome_ase)`.
2. Carrega o wrapper MACE via `src.utils.mlips.loader.load_wrapper` do
   AtomisticSkills.
3. Relaxa com LBFGS até `fmax = 0.001 eV/Å`. A tolerância apertada não é
   opcional: a aproximação harmônica exige um mínimo bem convergido, e forças
   residuais grandes produzem frequências imaginárias espúrias.
4. Grava `relaxed.xyz` e a energia potencial final.
5. Invoca como subprocesso o script da skill:
   `chem-vibration/scripts/calculate_vibrations.py --structure relaxed.xyz --no_relax`.
   A física fica na skill; este projeto não reimplementa a análise vibracional.
6. Lê `vibration_results.json` produzido pela skill.
7. Reabre o cache do ASE (`ase.vibrations.Vibrations(atoms, name=<dir>/vib).read()`)
   e extrai os autovetores de cada modo via `get_mode(i)`. Isso lê apenas o cache
   em disco — não recalcula nada e não precisa do calculador.
8. Calcula as ligações por raios covalentes
   (`ase.neighborlist.natural_cutoffs` + `build_neighbor_list`).
9. Retorna o dicionário da molécula.

**Depende de:** ASE, do repositório AtomisticSkills (caminho configurável), e do
ambiente conda `mace-agent`.

### `scripts/run_all.py`

Responsabilidade única: orquestrar as 10 moléculas e agregar o resultado.

- Executa `run_molecule` para cada entrada da tabela de moléculas.
- **Isolamento de falhas:** exceção numa molécula é capturada, registrada e a
  execução continua. A molécula que falhou é omitida do JSON.
- Ao final, escreve `web/data.json` e imprime um relatório: quais moléculas
  entraram, quais falharam e por quê.
- Roda o bloco de validação (abaixo) e imprime o resultado.

**Depende de:** `run_molecule.py`.

### `web/index.html`

Arquivo único, sem etapa de build. Carrega `data.json` via `fetch` e 3Dmol.js
por CDN.

Layout:

- **Topo:** seletor das 10 moléculas (botões/chips) e identificação do modelo MLIP.
- **Esquerda:** visualizador 3D (3Dmol.js), rotacionável, estilo bola-e-bastão.
- **Direita:** ficha da molécula (fórmula, nº de átomos, linear, ZPE, energia) e
  tabela de modos normais clicáveis com a frequência em cm⁻¹.
- **Interação:** clicar num modo anima o deslocamento correspondente. Clicar de
  novo (ou noutro modo) troca a animação.

**Depende de:** `data.json` apenas.

## Contrato de dados: `web/data.json`

```jsonc
{
  "model":     { "type": "mace", "name": "<nome-do-checkpoint>", "head": "omol" },
  "generated": "2026-08-08T00:00:00",
  "settings":  { "fmax_eV_per_A": 0.001, "delta_A": 0.01, "nfree": 2 },
  "molecules": [
    {
      "id": "h2o",
      "name": "Água",
      "formula": "H2O",
      "n_atoms": 3,
      "is_linear": false,
      "energy_eV": -14.8,
      "zpe_eV": 0.57,
      "n_imaginary": 0,
      "atoms": {
        "symbols":   ["O", "H", "H"],
        "positions": [[0.0, 0.0, 0.12], [0.0, 0.76, -0.48], [0.0, -0.76, -0.48]]
      },
      "bonds": [[0, 1], [0, 2]],
      "modes": [
        {
          "index":    6,
          "freq_cm1": 1595.2,
          "vectors":  [[0.0, 0.0, 0.07], [0.0, 0.42, -0.56], [0.0, -0.42, -0.56]]
        }
      ]
    }
  ]
}
```

Notas sobre o contrato:

- `positions` em ångström; `vectors` são deslocamentos normalizados por átomo, na
  mesma ordem de `symbols`.
- `modes` contém **apenas os modos vibracionais reais**, não os translacionais e
  rotacionais.
- `bonds` são pares de índices em `symbols`, para o desenho — não têm significado
  físico calculado.
- `n_imaginary` é reportado mesmo quando zero: é o indicador de qualidade do
  resultado.

## Animação dos modos normais

O JS gera os quadros a partir de `positions` e `vectors`:

```
posição(atom_i, quadro_t) = positions[i] + A · sin(2π t / T) · vectors[i]
```

com amplitude `A` fixa, escolhida para ficar visualmente legível. Os quadros
alimentam o 3Dmol.js.

A API exata de animação do 3Dmol.js será confirmada via context7 antes da
implementação — é o único ponto onde o conhecimento prévio pode estar
desatualizado. Se a API nativa de vibração não servir, o fallback é gerar os
quadros como múltiplos modelos e usar `viewer.animate()`.

## Tratamento de erros

| Situação | Comportamento |
|----------|---------------|
| Checkpoint MACE indisponível | Cai para o fallback; se ambos falharem, aborta com mensagem clara |
| Relaxação não converge | Molécula omitida, erro registrado, demais continuam |
| Molécula com modo imaginário | **Incluída** no JSON, com `n_imaginary > 0` e aviso no relatório — o resultado ruim fica visível, não escondido |
| `data.json` ausente no front | Página mostra mensagem de erro em vez de tela em branco |

## Validação

Não há framework de teste; a validação é física e roda ao final de `run_all.py`.

1. **Contagem de modos:** para cada molécula, `len(modes)` deve ser `3N−6`
   (`3N−5` se linear). Divergência é reportada como falha.
2. **Ausência de imaginárias:** `n_imaginary == 0`. Qualquer modo imaginário
   indica geometria fora do mínimo e é reportado.
3. **Sanity-check contra experimento:** para H₂O, CO₂, NH₃, CH₄ e C₂H₂, comparar
   as frequências calculadas com valores experimentais conhecidos e imprimir o
   desvio **no terminal**.

   Esses valores de referência não vão para a página. Publicar números
   experimentais exige citação precisa da fonte, e o objetivo aqui é validar o
   cálculo, não distribuir dados de referência.

4. **Verificação visual:** abrir a página localmente e confirmar que as 10
   moléculas renderizam e que a animação de pelo menos um modo funciona, antes de
   fazer o deploy.

## Deploy

- Diretório `web/` publicado como estático na Vercel via MCP da Vercel.
- Sem funções serverless, sem variáveis de ambiente, sem integrações — cabe
  folgadamente no plano gratuito.
- O `data.json` é um artefato versionado no git, gerado localmente. O cálculo
  nunca roda na Vercel.

## Estrutura de arquivos

```
curso_casa_kcm/
├── docs/superpowers/specs/2026-08-08-mlip-vibrations-app-design.md
├── scripts/
│   ├── molecules.py        # tabela das 10 moléculas
│   ├── run_molecule.py     # cálculo de uma molécula
│   └── run_all.py          # orquestração + validação
├── results/                # saídas brutas por molécula (gitignored)
├── web/
│   ├── index.html
│   └── data.json
└── README.md
```
