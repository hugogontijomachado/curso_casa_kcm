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
