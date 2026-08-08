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
