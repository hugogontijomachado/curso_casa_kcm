# Otimização e Frequências Vibracionais com MLIP — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calcular geometria otimizada e frequências vibracionais harmônicas de 10 moléculas pequenas com MACE, e publicar os resultados numa página estática única na Vercel com visualização 3D e animação dos modos normais.

**Architecture:** Dois estágios desacoplados por um único contrato de dados (`web/data.json`). O estágio 1 é um pipeline Python local que usa ASE + MACE através do repositório AtomisticSkills e grava o JSON. O estágio 2 é um `index.html` estático que só lê esse JSON — não sabe nada de Python, conda ou MLIP.

**Tech Stack:** Python 3.10 (ambiente conda `mace-agent`), ASE, MACE (`MACE-OFF23-small`), AtomisticSkills (skill `chem-vibration`), HTML/CSS/JS puro, 3Dmol.js via CDN, Vercel (estático).

## Global Constraints

Estes valores são fatos verificados na máquina alvo. Use-os literalmente.

- **Interpretador Python:** `/Users/hugocemep/miniforge3/envs/mace-agent/bin/python`. Os comandos `conda` e `timeout` **não existem** no shell não-interativo — nunca use `conda run` nem `timeout` nos comandos.
- **PYTHONPATH obrigatório** para importar o AtomisticSkills: `PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills`.
- **Raiz do AtomisticSkills:** `/Users/hugocemep/GitHub/AtomisticSkills`.
- **`pytest` NÃO está instalado** no `mace-agent`. Os testes são scripts Python com `assert` puro, executados diretamente. Não instale pytest.
- **Modelo MLIP:** `MACE-OFF23-small`, já em cache em `~/.cache/mace/MACE-OFF23_small.model`. Não baixe outro modelo.
- **API do wrapper MLIP:** `load_wrapper("mace", "MACE-OFF23-small", device="cpu")` → `wrapper.create_calculator()`. **Não existe** `wrapper.get_calculator()`; `wrapper.calculator` é `None` até `create_calculator()` ser chamado.
- **Parâmetros do cálculo:** `fmax = 1e-4` eV/Å, `delta = 0.01` Å, `nfree = 2`, `device = "cpu"`.
- **Nomes de arquivos e diretórios são fixos** conforme a seção "Estrutura de arquivos" abaixo.
- **Idioma:** comentários, docstrings e texto de interface em português. Nomes de identificadores em inglês onde já é convenção (`positions`, `symbols`).
- **Commits:** ao final de cada tarefa, com a mensagem indicada.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---------|------------------|
| `scripts/__init__.py` | Torna `scripts/` importável como pacote |
| `scripts/molecules.py` | A tabela das 10 moléculas. Sem lógica de cálculo. |
| `scripts/run_molecule.py` | Cálculo completo de **uma** molécula: relaxa, chama a skill, extrai autovetores, devolve o registro |
| `scripts/run_all.py` | Orquestra as 10, isola falhas, valida a física, escreve `web/data.json` |
| `tests/test_molecules.py` | Verifica a tabela contra o banco g2 do ASE |
| `tests/test_run_molecule.py` | Verifica o cálculo de H₂O contra valores de referência |
| `web/index.html` | Página única: visualizador 3D + lista de resultados + animação |
| `web/data.json` | Contrato de dados (gerado, versionado no git) |
| `results/` | Saídas brutas por molécula (ignorado pelo git) |

## Contexto de domínio para quem implementa

Três coisas que não são óbvias e que já foram verificadas experimentalmente nesta máquina:

**1. A skill `chem-vibration` não devolve os autovetores.** Ela grava `vibration_results.json` com frequências e ZPE, mas os deslocamentos de cada modo (necessários para animar) ficam apenas no cache em disco do ASE, em `<output_dir>/vib`. A forma de obtê-los sem recalcular nada é reabrir `ase.vibrations.Vibrations` apontando para esse mesmo cache e chamar `get_mode(i)`.

**2. A classificação de modos da skill usa um limiar fixo de 50 cm⁻¹ e erra.** Em H₂O, um modo *rotacional* aparece como `52.7i` cm⁻¹ — ruído numérico das diferenças finitas — e a skill o classifica como "imaginário", o que sugeriria falsamente que a geometria não é um mínimo. Verificado: apertar `fmax` de 1e-4 para 1e-5 **não** elimina esse ruído (as frequências reais ficam idênticas: 1631,7 / 3844,9 / 3949,1 cm⁻¹). Portanto **não** use o campo `real_modes` da skill. Classifique você mesmo pela regra exata: uma molécula tem exatamente 5 graus de liberdade de translação/rotação se linear, 6 caso contrário. Ordene os 3N modos por magnitude, descarte os 5 ou 6 menores, e os restantes são os vibracionais. Só um modo imaginário *entre esses* é problema de verdade.

**3. O 3Dmol.js anima vibrações a partir de colunas extras no XYZ.** `viewer.vibrate(numFrames, amplitude, bothWays)` procura as propriedades `dx, dy, dz` dos átomos, que o parser XYZ lê das colunas 5, 6 e 7. Ou seja: basta montar uma string XYZ com `símbolo x y z dx dy dz` por linha e chamar `vibrate()` seguido de `animate()`. Não é preciso gerar quadros na mão. O 3Dmol também deduz as ligações sozinho a partir das distâncias, então **não** precisamos exportar uma lista de ligações no JSON (isso simplifica o contrato descrito no spec).

---

### Task 1: Tabela de moléculas

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/molecules.py`
- Test: `tests/test_molecules.py`

**Interfaces:**
- Consumes: nada.
- Produces: `MoleculeSpec` (dataclass congelada com os campos `id: str`, `ase_name: str`, `name: str`, `expected_linear: bool`) e `MOLECULES: list[MoleculeSpec]` com 10 entradas. As tarefas 2 e 3 importam ambos de `scripts.molecules`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_molecules.py`:

```python
"""Verifica que a tabela de moléculas é consistente com o banco g2 do ASE."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ase.build import molecule as ase_molecule

from scripts.molecules import MOLECULES

LIMITE_ATOMOS = 12


def main() -> None:
    assert len(MOLECULES) == 10, f"esperava 10 moléculas, achei {len(MOLECULES)}"

    ids = [m.id for m in MOLECULES]
    assert len(set(ids)) == 10, f"ids duplicados em {ids}"

    for spec in MOLECULES:
        atoms = ase_molecule(spec.ase_name)
        n = len(atoms)
        assert n <= LIMITE_ATOMOS, f"{spec.id}: {n} átomos, acima do limite de {LIMITE_ATOMOS}"
        assert spec.name, f"{spec.id}: nome em português vazio"
        print(f"OK  {spec.id:6s} {atoms.get_chemical_formula():6s} {n:2d} átomos  {spec.name}")

    print("\ntodos os testes de tabela passaram")


main()
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run:
```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm && \
PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
~/miniforge3/envs/mace-agent/bin/python tests/test_molecules.py
```
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts'`.

- [ ] **Step 3: Escrever a implementação**

Criar `scripts/__init__.py` vazio.

Criar `scripts/molecules.py`:

```python
"""Tabela das moléculas estudadas.

Todas existem no banco de dados g2 do ASE e têm no máximo 12 átomos.
O campo `expected_linear` é apenas a expectativa física — a linearidade
efetiva é determinada pelo cálculo e gravada no JSON de saída.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MoleculeSpec:
    """Identificação de uma molécula do conjunto."""

    id: str
    ase_name: str
    name: str
    expected_linear: bool


MOLECULES: list[MoleculeSpec] = [
    MoleculeSpec("h2o", "H2O", "Água", False),
    MoleculeSpec("co2", "CO2", "Dióxido de carbono", True),
    MoleculeSpec("nh3", "NH3", "Amônia", False),
    MoleculeSpec("h2co", "H2CO", "Formaldeído", False),
    MoleculeSpec("c2h2", "C2H2", "Acetileno", True),
    MoleculeSpec("ch4", "CH4", "Metano", False),
    MoleculeSpec("ch3oh", "CH3OH", "Metanol", False),
    MoleculeSpec("c2h4", "C2H4", "Eteno", False),
    MoleculeSpec("c2h6", "C2H6", "Etano", False),
    MoleculeSpec("c6h6", "C6H6", "Benzeno", False),
]
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run:
```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm && \
PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
~/miniforge3/envs/mace-agent/bin/python tests/test_molecules.py
```
Expected: PASS — 10 linhas `OK ...` seguidas de `todos os testes de tabela passaram`.

Se algum `ase_name` não existir no g2, o ASE levanta `KeyError`. Nesse caso corrija o nome em `scripts/molecules.py` (o g2 usa fórmulas como `CH3OH`, não `CH4O`) e rode de novo.

- [ ] **Step 5: Commit**

```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm
git add scripts/__init__.py scripts/molecules.py tests/test_molecules.py
git commit -m "Add molecule table with g2 validation"
```

---

### Task 2: Cálculo de uma molécula

**Files:**
- Create: `scripts/run_molecule.py`
- Test: `tests/test_run_molecule.py`

**Interfaces:**
- Consumes: `MoleculeSpec` e `MOLECULES` de `scripts.molecules`.
- Produces, todos importáveis de `scripts.run_molecule`:
  - `MODEL_TYPE: str`, `MODEL_NAME: str`, `FMAX: float`, `DELTA: float`, `NFREE: int` — constantes de configuração.
  - `load_calculator() -> tuple[object, object]` — devolve `(wrapper, calculator)`.
  - `classify_vibrational_indices(frequencies, is_linear) -> list[int]` — índices dos modos vibracionais.
  - `compute_molecule(spec: MoleculeSpec, calculator, results_root: Path) -> dict` — o registro completo da molécula.

  A tarefa 3 usa `load_calculator`, `compute_molecule`, `MODEL_TYPE` e `MODEL_NAME`.

- [ ] **Step 1: Escrever o teste que falha**

Os valores de referência abaixo foram medidos nesta máquina com `MACE-OFF23-small` e são reprodutíveis.

Criar `tests/test_run_molecule.py`:

```python
"""Verifica o cálculo de uma molécula contra valores medidos nesta máquina.

Referência para H2O com MACE-OFF23-small, fmax=1e-4:
frequências 1631.7 / 3844.9 / 3949.1 cm^-1, ZPE 0.5875 eV, d(O-H) 0.9588 A.
"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scripts.molecules import MOLECULES
from scripts.run_molecule import compute_molecule, load_calculator

FREQUENCIAS_ESPERADAS = [1631.7, 3844.9, 3949.1]
TOLERANCIA_CM1 = 15.0
ZPE_ESPERADA_EV = 0.5875
TOLERANCIA_ZPE_EV = 0.01


def main() -> None:
    spec = next(m for m in MOLECULES if m.id == "h2o")
    _, calculator = load_calculator()

    with tempfile.TemporaryDirectory() as tmp:
        registro = compute_molecule(spec, calculator, pathlib.Path(tmp))

    assert registro["id"] == "h2o"
    assert registro["formula"] == "H2O"
    assert registro["n_atoms"] == 3
    assert registro["is_linear"] is False

    modos = registro["modes"]
    assert len(modos) == 3, f"esperava 3 modos vibracionais, achei {len(modos)}"
    assert registro["n_imaginary"] == 0, f"modos imaginários: {registro['n_imaginary']}"

    for modo, esperada in zip(modos, FREQUENCIAS_ESPERADAS):
        desvio = abs(modo["freq_cm1"] - esperada)
        assert desvio < TOLERANCIA_CM1, f"modo {modo['freq_cm1']} vs esperado {esperada}"
        assert len(modo["vectors"]) == 3, "um vetor de deslocamento por átomo"
        assert len(modo["vectors"][0]) == 3, "cada vetor tem 3 componentes"

    desvio_zpe = abs(registro["zpe_eV"] - ZPE_ESPERADA_EV)
    assert desvio_zpe < TOLERANCIA_ZPE_EV, f"ZPE {registro['zpe_eV']} vs {ZPE_ESPERADA_EV}"

    assert len(registro["atoms"]["symbols"]) == 3
    assert len(registro["atoms"]["positions"]) == 3
    assert registro["energy_eV"] < 0, "energia potencial deve ser negativa"

    print("frequências:", [m["freq_cm1"] for m in modos])
    print("ZPE (eV):", registro["zpe_eV"])
    print("energia (eV):", registro["energy_eV"])
    print("\nteste de cálculo de molécula passou")


main()
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run:
```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm && \
PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
~/miniforge3/envs/mace-agent/bin/python tests/test_run_molecule.py
```
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.run_molecule'`.

- [ ] **Step 3: Escrever a implementação**

Criar `scripts/run_molecule.py`:

```python
"""Otimiza uma molécula com MACE e calcula suas frequências vibracionais.

A análise vibracional em si é feita pela skill `chem-vibration` do
AtomisticSkills, invocada como subprocesso. Este módulo cuida da
relaxação, da extração dos autovetores (que a skill não devolve) e da
montagem do registro final.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ATOMISTIC_SKILLS = Path(
    os.environ.get("ATOMISTIC_SKILLS", "/Users/hugocemep/GitHub/AtomisticSkills")
)
if str(ATOMISTIC_SKILLS) not in sys.path:
    sys.path.insert(0, str(ATOMISTIC_SKILLS))

from ase.build import molecule as ase_molecule
from ase.io import write as ase_write
from ase.optimize import LBFGS
from ase.vibrations import Vibrations

from src.utils.mlips.loader import load_wrapper

from scripts.molecules import MoleculeSpec

MODEL_TYPE = "mace"
MODEL_NAME = "MACE-OFF23-small"
DEVICE = "cpu"
FMAX = 1e-4
DELTA = 0.01
NFREE = 2

VIB_SCRIPT = (
    ATOMISTIC_SKILLS / ".agents/skills/chem-vibration/scripts/calculate_vibrations.py"
)


def load_calculator():
    """Carrega o MLIP uma única vez e devolve (wrapper, calculador ASE)."""
    wrapper = load_wrapper(MODEL_TYPE, MODEL_NAME, device=DEVICE)
    return wrapper, wrapper.create_calculator()


def _optimize(spec: MoleculeSpec, calculator, workdir: Path):
    """Relaxa a molécula e grava relaxed.xyz. Devolve (atoms, energia_eV)."""
    atoms = ase_molecule(spec.ase_name)
    atoms.calc = calculator
    LBFGS(atoms, logfile=str(workdir / "relax.log")).run(fmax=FMAX, steps=1000)
    energia = float(atoms.get_potential_energy())
    ase_write(str(workdir / "relaxed.xyz"), atoms)
    return atoms, energia


def _run_vibration_skill(workdir: Path) -> dict:
    """Invoca a skill chem-vibration e devolve o JSON que ela produz."""
    comando = [
        sys.executable,
        str(VIB_SCRIPT),
        "--structure", str(workdir / "relaxed.xyz"),
        "--model_type", MODEL_TYPE,
        "--model_name", MODEL_NAME,
        "--no_relax",
        "--delta", str(DELTA),
        "--nfree", str(NFREE),
        "--device", DEVICE,
        "--output_dir", str(workdir),
    ]
    ambiente = dict(os.environ, PYTHONPATH=str(ATOMISTIC_SKILLS))
    subprocess.run(comando, check=True, cwd=str(ATOMISTIC_SKILLS), env=ambiente)
    return json.loads((workdir / "vibration_results.json").read_text())


def classify_vibrational_indices(frequencies, is_linear: bool) -> list[int]:
    """Devolve os índices dos modos vibracionais entre os 3N modos.

    Uma molécula tem exatamente 5 graus de liberdade de translação e
    rotação se for linear, 6 caso contrário. Descartamos os modos de
    menor magnitude nessa quantidade exata, em vez de usar um limiar fixo
    em cm^-1: o ruído numérico das diferenças finitas põe modos
    rotacionais em torno de 50i cm^-1, e um limiar os classificaria
    erroneamente como frequências imaginárias.
    """
    n_trans_rot = 5 if is_linear else 6
    magnitudes = np.array([abs(complex(f)) for f in frequencies])
    ordem = np.argsort(magnitudes)
    return sorted(int(i) for i in ordem[n_trans_rot:])


def _open_vibrations(atoms, workdir: Path, calculator) -> Vibrations:
    """Reabre o cache do ASE gravado pela skill, sem recalcular nada."""
    copia = atoms.copy()
    copia.calc = calculator
    vib = Vibrations(copia, name=str(workdir / "vib"), delta=DELTA, nfree=NFREE)
    vib.run()
    return vib


def compute_molecule(spec: MoleculeSpec, calculator, results_root: Path) -> dict:
    """Executa o cálculo completo de uma molécula e devolve o registro."""
    workdir = Path(results_root) / spec.id
    workdir.mkdir(parents=True, exist_ok=True)

    atoms, energia = _optimize(spec, calculator, workdir)
    resultado_skill = _run_vibration_skill(workdir)

    vib = _open_vibrations(atoms, workdir, calculator)
    frequencias = vib.get_frequencies()
    is_linear = bool(resultado_skill["is_linear"])
    indices = classify_vibrational_indices(frequencias, is_linear)

    modos = []
    n_imaginarios = 0
    for i in indices:
        valor = complex(frequencias[i])
        imaginario = abs(valor.imag) > 1e-6
        if imaginario:
            n_imaginarios += 1
        modos.append(
            {
                "index": i,
                "freq_cm1": round(-abs(valor.imag) if imaginario else valor.real, 1),
                "imaginary": imaginario,
                "vectors": np.round(vib.get_mode(i), 4).tolist(),
            }
        )
    modos.sort(key=lambda m: m["freq_cm1"])

    return {
        "id": spec.id,
        "name": spec.name,
        "formula": atoms.get_chemical_formula(),
        "n_atoms": len(atoms),
        "is_linear": is_linear,
        "energy_eV": round(energia, 6),
        "zpe_eV": round(float(resultado_skill["zero_point_energy_eV"]), 6),
        "n_imaginary": n_imaginarios,
        "atoms": {
            "symbols": atoms.get_chemical_symbols(),
            "positions": np.round(atoms.get_positions(), 4).tolist(),
        },
        "modes": modos,
    }
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run:
```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm && \
PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
~/miniforge3/envs/mace-agent/bin/python tests/test_run_molecule.py
```
Expected: PASS, terminando com `teste de cálculo de molécula passou`. O carregamento do modelo demora cerca de 10 s; o cálculo de H₂O é rápido. Avisos do PyTorch sobre `weights_only` e `cuequivariance` são normais e podem ser ignorados.

- [ ] **Step 5: Commit**

```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm
git add scripts/run_molecule.py tests/test_run_molecule.py
git commit -m "Add single-molecule optimization and vibration calculation"
```

---

### Task 3: Orquestração, validação e geração do data.json

**Files:**
- Create: `scripts/run_all.py`
- Create: `web/data.json` (gerado ao executar)

**Interfaces:**
- Consumes: `MOLECULES` de `scripts.molecules`; `load_calculator`, `compute_molecule`, `MODEL_TYPE`, `MODEL_NAME`, `FMAX`, `DELTA`, `NFREE` de `scripts.run_molecule`.
- Produces: o arquivo `web/data.json` no formato descrito no spec. A tarefa 4 consome só esse arquivo.

- [ ] **Step 1: Escrever o script**

Criar `scripts/run_all.py`:

```python
"""Roda o cálculo das 10 moléculas, valida a física e gera web/data.json.

Uma molécula que falha é registrada e omitida do JSON; as demais seguem.
"""

from __future__ import annotations

import datetime
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.molecules import MOLECULES
from scripts.run_molecule import (
    DELTA,
    FMAX,
    MODEL_NAME,
    MODEL_TYPE,
    NFREE,
    compute_molecule,
    load_calculator,
)

RAIZ = Path(__file__).resolve().parents[1]
RESULTS = RAIZ / "results"
SAIDA = RAIZ / "web" / "data.json"

# Fundamentais experimentais em cm^-1, de tabelas espectroscópicas padrão.
# Usados apenas para conferência no terminal; não vão para a página.
# As frequências harmônicas calculadas ficam sistematicamente ~5% acima
# das fundamentais medidas, porque estas incluem anarmonicidade.
REFERENCIAS_EXPERIMENTAIS = {
    "h2o": [1595, 3657, 3756],
    "co2": [667, 1333, 2349],
    "nh3": [950, 1627, 3337, 3444],
    "ch4": [1306, 1534, 2917, 3019],
    "c2h2": [612, 730, 1974, 3289, 3374],
}


def calcular_todas() -> tuple[list[dict], list[tuple[str, str]]]:
    """Calcula todas as moléculas. Devolve (registros, falhas)."""
    _, calculator = load_calculator()
    registros: list[dict] = []
    falhas: list[tuple[str, str]] = []

    for i, spec in enumerate(MOLECULES, start=1):
        print(f"\n[{i}/{len(MOLECULES)}] {spec.id} ({spec.ase_name})", flush=True)
        try:
            registros.append(compute_molecule(spec, calculator, RESULTS))
        except Exception as erro:  # noqa: BLE001 — uma falha não pode parar o lote
            falhas.append((spec.id, f"{type(erro).__name__}: {erro}"))
            traceback.print_exc()

    return registros, falhas


def validar(registros: list[dict]) -> list[str]:
    """Confere a física de cada registro. Devolve a lista de problemas."""
    problemas: list[str] = []

    print("\n" + "=" * 64)
    print("VALIDAÇÃO — contagem de modos e frequências imaginárias")
    print("=" * 64)

    for r in registros:
        n = r["n_atoms"]
        esperado = 3 * n - (5 if r["is_linear"] else 6)
        obtido = len(r["modes"])
        marca = "ok " if obtido == esperado else "ERRO"
        if obtido != esperado:
            problemas.append(f"{r['id']}: {obtido} modos, esperado {esperado}")
        if r["n_imaginary"]:
            problemas.append(f"{r['id']}: {r['n_imaginary']} frequência(s) imaginária(s)")
            marca = "ERRO"
        print(
            f"{marca} {r['id']:6s} {r['formula']:6s} "
            f"modos {obtido:2d}/{esperado:2d}  imaginárias {r['n_imaginary']}"
        )

    print("\n" + "=" * 64)
    print("CONFERÊNCIA COM FUNDAMENTAIS EXPERIMENTAIS (cm^-1)")
    print("valores harmônicos ficam ~5% acima por não incluir anarmonicidade")
    print("=" * 64)

    por_id = {r["id"]: r for r in registros}
    for mol_id, experimentais in REFERENCIAS_EXPERIMENTAIS.items():
        registro = por_id.get(mol_id)
        if registro is None:
            continue
        calculadas = [m["freq_cm1"] for m in registro["modes"]]
        print(f"\n{mol_id} ({registro['formula']})")
        for exp in experimentais:
            mais_proxima = min(calculadas, key=lambda c: abs(c - exp))
            desvio = 100.0 * (mais_proxima - exp) / exp
            print(f"   exp {exp:6.0f}   calc {mais_proxima:7.1f}   desvio {desvio:+6.1f}%")

    return problemas


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    SAIDA.parent.mkdir(exist_ok=True)

    registros, falhas = calcular_todas()
    problemas = validar(registros)

    dados = {
        "model": {"type": MODEL_TYPE, "name": MODEL_NAME},
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "settings": {"fmax_eV_per_A": FMAX, "delta_A": DELTA, "nfree": NFREE},
        "molecules": registros,
    }
    SAIDA.write_text(json.dumps(dados, indent=1, ensure_ascii=False))

    print("\n" + "=" * 64)
    print("RESUMO")
    print("=" * 64)
    print(f"moléculas calculadas: {len(registros)}/{len(MOLECULES)}")
    print(f"arquivo gerado: {SAIDA} ({SAIDA.stat().st_size / 1024:.0f} kB)")

    for mol_id, erro in falhas:
        print(f"FALHOU  {mol_id}: {erro}")
    for problema in problemas:
        print(f"PROBLEMA  {problema}")

    if not falhas and not problemas:
        print("nenhuma falha, nenhum problema de validação")

    return 1 if falhas or problemas else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Rodar o pipeline completo**

Run:
```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm && \
PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
~/miniforge3/envs/mace-agent/bin/python scripts/run_all.py 2>&1 | tail -60
```

Expected: as 10 moléculas calculadas, tabela de validação com `ok` em todas as linhas, tabela de comparação experimental com desvios majoritariamente entre 0% e +8%, e `nenhuma falha, nenhum problema de validação`.

O benzeno (12 átomos, 36 deslocamentos) é o mais demorado. Use `timeout` de pelo menos 15 minutos na chamada da ferramenta Bash — mas **não** o comando `timeout`, que não existe nesta máquina.

- [ ] **Step 3: Conferir o JSON gerado**

Run:
```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm && \
~/miniforge3/envs/mace-agent/bin/python -c "
import json
d = json.load(open('web/data.json'))
print('modelo:', d['model'])
for m in d['molecules']:
    print(f\"{m['id']:6s} {m['formula']:6s} {m['n_atoms']:2d} átomos  {len(m['modes']):2d} modos  ZPE {m['zpe_eV']:.4f} eV\")
"
```
Expected: 10 linhas, contagens de modos iguais a 3N−6 (3N−5 para `co2` e `c2h2`).

- [ ] **Step 4: Corrigir se a validação apontar problema**

Se alguma molécula acusar frequência imaginária ou contagem de modos errada, **não** relaxe a validação. Investigue: rode aquela molécula sozinha com

```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm && \
PYTHONPATH=/Users/hugocemep/GitHub/AtomisticSkills \
~/miniforge3/envs/mace-agent/bin/python -c "
import pathlib
from scripts.molecules import MOLECULES
from scripts.run_molecule import compute_molecule, load_calculator
spec = next(m for m in MOLECULES if m.id == 'AQUI_O_ID')
_, calc = load_calculator()
r = compute_molecule(spec, calc, pathlib.Path('results'))
print([m['freq_cm1'] for m in r['modes']])
"
```

e apague `results/<id>/vib` antes de repetir, para não reaproveitar um cache inconsistente.

- [ ] **Step 5: Commit**

```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm
git add scripts/run_all.py web/data.json
git commit -m "Add pipeline orchestration and generate results for ten molecules"
```

---

### Task 4: Página web

**Files:**
- Create: `web/index.html`

**Interfaces:**
- Consumes: `web/data.json` — os campos `model.name`, e por molécula `id`, `name`, `formula`, `n_atoms`, `is_linear`, `energy_eV`, `zpe_eV`, `n_imaginary`, `atoms.symbols`, `atoms.positions`, `modes[].freq_cm1`, `modes[].imaginary`, `modes[].vectors`.
- Produces: nada consumido por outra tarefa.

- [ ] **Step 1: Escrever a página**

Criar `web/index.html`:

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frequências vibracionais com MLIP</title>
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>
<style>
  :root {
    --fundo: #0f1115;
    --painel: #171a21;
    --borda: #262b35;
    --texto: #e6e9ef;
    --suave: #949cad;
    --destaque: #5eb0ff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--fundo);
    color: var(--texto);
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  }
  header {
    padding: 20px 24px 12px;
    border-bottom: 1px solid var(--borda);
  }
  h1 { margin: 0 0 4px; font-size: 19px; font-weight: 600; }
  .sub { color: var(--suave); font-size: 13px; }
  .abas {
    display: flex; flex-wrap: wrap; gap: 6px;
    padding: 14px 24px; border-bottom: 1px solid var(--borda);
  }
  .aba {
    padding: 6px 13px; border: 1px solid var(--borda); border-radius: 999px;
    background: var(--painel); color: var(--suave);
    cursor: pointer; font-size: 13px; font-family: inherit;
  }
  .aba:hover { color: var(--texto); }
  .aba[aria-selected="true"] {
    background: var(--destaque); border-color: var(--destaque); color: #04121f; font-weight: 600;
  }
  main {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 20px; padding: 20px 24px; align-items: start;
  }
  @media (max-width: 860px) { main { grid-template-columns: 1fr; } }
  #viewer {
    position: relative; width: 100%; height: 460px;
    background: var(--painel); border: 1px solid var(--borda); border-radius: 10px;
  }
  .dica { margin-top: 8px; color: var(--suave); font-size: 12px; }
  .painel {
    background: var(--painel); border: 1px solid var(--borda);
    border-radius: 10px; padding: 16px;
  }
  .ficha { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; margin-bottom: 18px; }
  .ficha div { font-size: 13px; }
  .ficha span { display: block; color: var(--suave); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th {
    text-align: left; color: var(--suave); font-weight: 500; font-size: 11px;
    text-transform: uppercase; letter-spacing: .04em;
    padding: 6px 8px; border-bottom: 1px solid var(--borda);
  }
  th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td { padding: 7px 8px; border-bottom: 1px solid var(--borda); }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: #1e222b; }
  tbody tr[aria-selected="true"] { background: #16324d; color: var(--destaque); }
  .imag { color: #ff8f6b; }
  footer { padding: 8px 24px 28px; color: var(--suave); font-size: 12px; }
  .erro { padding: 24px; color: #ff8f6b; }
</style>
</head>
<body>
<header>
  <h1>Otimização e frequências vibracionais de moléculas pequenas</h1>
  <div class="sub" id="legenda">carregando…</div>
</header>

<div class="abas" id="abas" role="tablist"></div>

<main>
  <div>
    <div id="viewer"></div>
    <div class="dica">Arraste para girar, role para aproximar. Clique numa frequência para animar o modo normal.</div>
  </div>
  <div class="painel">
    <div class="ficha" id="ficha"></div>
    <table>
      <thead>
        <tr>
          <th class="num">#</th>
          <th class="num">Frequência (cm⁻¹)</th>
          <th>Modo</th>
        </tr>
      </thead>
      <tbody id="modos"></tbody>
    </table>
  </div>
</main>

<footer id="rodape"></footer>

<script>
let dados = null;
let molecula = null;
let visualizador = null;
let modoSelecionado = null;

/** Monta um XYZ. Com `modo`, acrescenta as colunas dx dy dz que o 3Dmol usa para vibrar. */
function montarXyz(mol, modo) {
  const linhas = [String(mol.n_atoms), mol.formula];
  mol.atoms.symbols.forEach((simbolo, i) => {
    const [x, y, z] = mol.atoms.positions[i];
    const base = `${simbolo} ${x.toFixed(5)} ${y.toFixed(5)} ${z.toFixed(5)}`;
    if (!modo) {
      linhas.push(base);
      return;
    }
    const [dx, dy, dz] = modo.vectors[i];
    linhas.push(`${base} ${dx.toFixed(5)} ${dy.toFixed(5)} ${dz.toFixed(5)}`);
  });
  return linhas.join("\n") + "\n";
}

function desenhar(mol, modo) {
  visualizador.clear();
  visualizador.addModel(montarXyz(mol, modo), "xyz");
  visualizador.setStyle({}, {
    stick: { radius: 0.13, colorscheme: "Jmol" },
    sphere: { scale: 0.24, colorscheme: "Jmol" },
  });
  if (modo) {
    visualizador.vibrate(12, 1.4, true);
    visualizador.animate({ loop: "backAndForth", reps: 0, interval: 55 });
  }
  visualizador.zoomTo();
  visualizador.render();
}

function renderFicha(mol) {
  const campos = [
    ["Fórmula", mol.formula],
    ["Átomos", mol.n_atoms],
    ["Geometria", mol.is_linear ? "linear" : "não linear"],
    ["Modos vibracionais", mol.modes.length],
    ["Energia de ponto zero", `${mol.zpe_eV.toFixed(4)} eV`],
    ["Energia potencial", `${mol.energy_eV.toFixed(3)} eV`],
  ];
  document.getElementById("ficha").innerHTML = campos
    .map(([rotulo, valor]) => `<div><span>${rotulo}</span>${valor}</div>`)
    .join("");
}

function renderModos(mol) {
  const corpo = document.getElementById("modos");
  corpo.innerHTML = mol.modes
    .map((modo, i) => {
      const classe = modo.imaginary ? ' class="num imag"' : ' class="num"';
      const rotulo = modo.imaginary ? "imaginário" : "vibração";
      return `<tr data-i="${i}"><td class="num">${i + 1}</td>` +
             `<td${classe}>${modo.freq_cm1.toFixed(1)}</td><td>${rotulo}</td></tr>`;
    })
    .join("");

  corpo.querySelectorAll("tr").forEach((linha) => {
    linha.addEventListener("click", () => {
      const i = Number(linha.dataset.i);
      modoSelecionado = modoSelecionado === i ? null : i;
      corpo.querySelectorAll("tr").forEach((outra) => {
        outra.setAttribute("aria-selected", String(Number(outra.dataset.i) === modoSelecionado));
      });
      desenhar(molecula, modoSelecionado === null ? null : molecula.modes[modoSelecionado]);
    });
  });
}

function selecionar(id) {
  molecula = dados.molecules.find((m) => m.id === id);
  modoSelecionado = null;
  document.querySelectorAll(".aba").forEach((aba) => {
    aba.setAttribute("aria-selected", String(aba.dataset.id === id));
  });
  renderFicha(molecula);
  renderModos(molecula);
  desenhar(molecula, null);
}

async function iniciar() {
  try {
    const resposta = await fetch("data.json");
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    dados = await resposta.json();
  } catch (erro) {
    document.querySelector("main").innerHTML =
      `<div class="erro">Não foi possível carregar data.json: ${erro.message}</div>`;
    return;
  }

  document.getElementById("legenda").textContent =
    `${dados.molecules.length} moléculas · potencial ${dados.model.name} · ` +
    `aproximação harmônica · relaxação até fmax = ${dados.settings.fmax_eV_per_A} eV/Å`;
  document.getElementById("rodape").textContent =
    `Cálculos gerados em ${dados.generated} com ASE e MACE via AtomisticSkills. ` +
    `As frequências são harmônicas e ficam sistematicamente acima das fundamentais ` +
    `medidas experimentalmente, que incluem anarmonicidade.`;

  document.getElementById("abas").innerHTML = dados.molecules
    .map((m) => `<button class="aba" role="tab" data-id="${m.id}">${m.name} · ${m.formula}</button>`)
    .join("");
  document.querySelectorAll(".aba").forEach((aba) => {
    aba.addEventListener("click", () => selecionar(aba.dataset.id));
  });

  visualizador = $3Dmol.createViewer(document.getElementById("viewer"), {
    backgroundColor: "#171a21",
  });

  selecionar(dados.molecules[0].id);
}

iniciar();
</script>
</body>
</html>
```

- [ ] **Step 2: Servir a página localmente**

Run (em segundo plano):
```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm/web && \
~/miniforge3/envs/mace-agent/bin/python -m http.server 8765
```

- [ ] **Step 3: Verificar que a página funciona**

Run:
```bash
curl -s -o /dev/null -w "index %{http_code}\n" http://localhost:8765/index.html && \
curl -s -o /dev/null -w "data  %{http_code}\n" http://localhost:8765/data.json
```
Expected: `index 200` e `data 200`.

Depois abra `http://localhost:8765/` no navegador e confirme, com os próprios olhos:
1. As 10 abas aparecem no topo.
2. A molécula renderiza em 3D e gira ao arrastar.
3. Clicar numa frequência anima a molécula, e clicar de novo para a animação.
4. Trocar de aba troca a molécula e a lista de modos.

Se qualquer um dos quatro pontos falhar, corrija antes de seguir. Use o console do navegador para ver erros de JavaScript.

- [ ] **Step 4: Parar o servidor local e commitar**

```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm
git add web/index.html
git commit -m "Add single-page viewer with 3D structure and mode animation"
```

---

### Task 5: Deploy na Vercel

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: `web/index.html` e `web/data.json`.
- Produces: a URL pública do deploy.

- [ ] **Step 1: Escrever o README**

Criar `README.md`:

```markdown
# Frequências vibracionais de moléculas pequenas com MLIP

Otimização de geometria e análise vibracional harmônica de 10 moléculas
pequenas usando o potencial de machine learning MACE-OFF23-small, através
das skills do [AtomisticSkills](https://github.com/learningmatter-mit/AtomisticSkills).
Os resultados são publicados numa página estática com visualização 3D e
animação dos modos normais.

## Reproduzir os cálculos

Requer o repositório AtomisticSkills e o ambiente conda `mace-agent`.

    PYTHONPATH=/caminho/para/AtomisticSkills \
    ~/miniforge3/envs/mace-agent/bin/python scripts/run_all.py

Isso regenera `web/data.json` e imprime a validação: contagem de modos
(3N−6, ou 3N−5 para moléculas lineares), ausência de frequências
imaginárias, e a comparação com fundamentais experimentais.

## Testes

    PYTHONPATH=/caminho/para/AtomisticSkills \
    ~/miniforge3/envs/mace-agent/bin/python tests/test_molecules.py

    PYTHONPATH=/caminho/para/AtomisticSkills \
    ~/miniforge3/envs/mace-agent/bin/python tests/test_run_molecule.py

## Página

`web/` é servida como conteúdo estático. Para ver localmente:

    cd web && python -m http.server 8765

## Sobre os números

As frequências são **harmônicas**: a energia potencial é aproximada por uma
parábola em torno do mínimo. Elas ficam sistematicamente acima das
fundamentais medidas experimentalmente, que incluem efeitos anarmônicos.
Um desvio positivo da ordem de 5% é o esperado, não um erro do cálculo.
```

- [ ] **Step 2: Commitar o README**

```bash
cd /Users/hugocemep/GitHub/curso_casa_kcm
git add README.md
git commit -m "Add README describing pipeline and how to reproduce"
```

- [ ] **Step 3: Fazer o deploy**

Use a ferramenta MCP da Vercel `mcp__plugin_vercel_vercel__deploy_to_vercel` a
partir do diretório `/Users/hugocemep/GitHub/curso_casa_kcm`. O conteúdo a
publicar é o diretório `web/`.

Se o deploy exigir a definição de um diretório de saída, configure `web` como
diretório raiz do projeto. Não há build step: é conteúdo estático puro, sem
`package.json`, sem funções serverless e sem variáveis de ambiente.

- [ ] **Step 4: Verificar o deploy**

Run (substituindo pela URL devolvida):
```bash
curl -s -o /dev/null -w "index %{http_code}\n" https://SUA-URL.vercel.app/ && \
curl -s -o /dev/null -w "data  %{http_code}\n" https://SUA-URL.vercel.app/data.json
```
Expected: `index 200` e `data 200`.

Se o deploy tiver proteção ativada e devolver 401, use
`mcp__plugin_vercel_vercel__get_access_to_vercel_url` para obter uma URL
acessível, ou desative a proteção com
`mcp__plugin_vercel_vercel__update_project_deployment_protection`.

Abra a URL no navegador e repita a verificação visual dos quatro pontos da
tarefa 4.

- [ ] **Step 5: Reportar**

Informe ao usuário: a URL do deploy, quantas moléculas foram calculadas com
sucesso, o resultado da validação de modos, e a faixa de desvio observada
contra os valores experimentais.
