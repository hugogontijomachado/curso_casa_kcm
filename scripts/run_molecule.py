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
